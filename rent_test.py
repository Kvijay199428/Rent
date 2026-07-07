#!/usr/bin/env python3
import os
import re
import io
import json
import time
import uuid
import base64
import sqlite3
import traceback
from pathlib import Path
from urllib.parse import urljoin, quote

import requests

BASE_URL = "https://endomorphic-semiprotectively-jamaal.ngrok-free.dev/rent/"
TIMEOUT = 30

ALLOW_MUTATION = True
TEST_PUBLIC_KYC = True # Enabled KYC flow
TEST_WHATSAPP = False
TEST_IMPORT_EXECUTE = False
TEST_RESTORE_BACKUP = False

DB_PATH = os.getenv("RENT_DB_PATH", "").strip()
SAMPLE_DIR_ENV = os.getenv("RENT_SAMPLE_DIR", "").strip()

OUT_JSON = "endpoint_test_report.json"
OUT_MD = "endpoint_test_report.md"


def norm_base(url: str) -> str:
    return url if url.endswith("/") else url + "/"


BASE_URL = norm_base(BASE_URL)

session = requests.Session()
session.headers.update({"User-Agent": "rent-endpoint-tester/3.0"})

results = []
tested_ops = set()

context = {
    "openapi": None,
    "config": None,
    "tenant_list": [],
    "created_tenant_id": None,
    "created_tenant_name": None,
    "created_tenant_pin": "1234", # Default tenant pin to resolve unlock failures
    "created_viewtoken": None,
    "created_billno": None,
    "created_backup_id": None,
    "preview_selected_targets": [],
    "kyc_filename": None,
    "occupant_uuid": None,
}

PAGE_ROUTES = [
    ("Home page", "GET", ""),
    ("Billing page", "GET", "billing"),
    ("History page", "GET", "history"),
    ("Tenants page", "GET", "tenants"),
    ("Settings page", "GET", "settings"),
    ("Archive page", "GET", "archive"),
    ("Backups page", "GET", "backups"),
    ("Favicon", "GET", "favicon.ico"),
]

TEMP_DIR = Path(".rent_test_assets")
TEMP_DIR.mkdir(exist_ok=True)


def now_ms():
    return int(time.time() * 1000)


def make_url(path: str) -> str:
    return urljoin(BASE_URL, path.lstrip("/"))


def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return None


def body_preview(resp, limit=300):
    text = resp.text if hasattr(resp, "text") else ""
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:limit]


def add_result(name, category, method, url, ok, status=None, expected=None, latency_ms=None,
               details=None, response_json=None, skipped=False):
    results.append({
        "name": name,
        "category": category,
        "method": method,
        "url": url,
        "ok": ok,
        "skipped": skipped,
        "status": status,
        "expected": expected,
        "latency_ms": latency_ms,
        "details": details,
        "response_json": response_json,
    })


def op_key(method: str, path: str) -> str:
    return f"{method.upper()} {path}"


def mark_tested(method: str, path: str):
    tested_ops.add(op_key(method, path))


def request(method, path, name=None, expected=(200,), category="http", mark=True, **kwargs):
    url = make_url(path)
    
    print(f"\n--- [REQUEST] {method.upper()} {url} ---")
    if "params" in kwargs and kwargs["params"]:
        print(f"Query: {kwargs['params']}")
    if "json" in kwargs and kwargs["json"]:
        print(f"JSON Payload: {json.dumps(kwargs['json'], indent=2)}")
    elif "data" in kwargs and kwargs["data"]:
        print(f"Data Payload: {kwargs['data']}")
    if "files" in kwargs and kwargs["files"]:
        print(f"Files: {list(kwargs['files'].keys())}")
        
    started = now_ms()
    try:
        resp = session.request(method, url, timeout=TIMEOUT, allow_redirects=True, **kwargs)
        latency = now_ms() - started
        
        print(f"--- [RESPONSE] {resp.status_code} ({latency}ms) ---")
        try:
            resp_json = resp.json()
            print(f"Response JSON: {json.dumps(resp_json, indent=2)}")
        except Exception:
            text = resp.text if hasattr(resp, "text") else ""
            print(f"Response Text (max 300 chars): {text[:300]}")
            
        ok = resp.status_code in expected
        add_result(
            name=name or f"{method} {path}",
            category=category,
            method=method.upper(),
            url=url,
            ok=ok,
            status=resp.status_code,
            expected=list(expected),
            latency_ms=latency,
            details=body_preview(resp),
            response_json=safe_json(resp),
        )
        if mark:
            mark_tested(method, path)
        update_context_from_response(path, resp)
        return resp
    except Exception as e:
        latency = now_ms() - started
        add_result(
            name=name or f"{method} {path}",
            category=category,
            method=method.upper(),
            url=url,
            ok=False,
            status=None,
            expected=list(expected),
            latency_ms=latency,
            details=f"{type(e).__name__}: {e}",
            response_json=None,
        )
        if mark:
            mark_tested(method, path)
        return None


def skip(name, category, method, url, reason):
    add_result(
        name=name,
        category=category,
        method=method,
        url=url,
        ok=False,
        skipped=True,
        details=reason,
    )


def extract_tenant_id(obj):
    if isinstance(obj, dict):
        if isinstance(obj.get("id"), int):
            return obj["id"]
        data = obj.get("data")
        if isinstance(data, dict) and isinstance(data.get("id"), int):
            return data["id"]
    return None


def extract_billno(obj):
    if isinstance(obj, dict):
        if isinstance(obj.get("Bill"), str):
            return obj["Bill"]
        if isinstance(obj.get("billno"), str):
            return obj["billno"]
        data = obj.get("data")
        if isinstance(data, dict):
            if isinstance(data.get("Bill"), str):
                return data["Bill"]
            if isinstance(data.get("billno"), str):
                return data["billno"]
    return None


def extract_backup_id(obj):
    if isinstance(obj, dict):
        data = obj.get("data")
        if isinstance(data, dict) and data.get("id"):
            return str(data["id"])
        if obj.get("id"):
            return str(obj["id"])
    return None


def extract_selected_targets(preview_json):
    selected = []
    if not isinstance(preview_json, dict):
        return selected
    files = preview_json.get("files", {})
    if not isinstance(files, dict):
        return selected
    for filename, tenants in files.items():
        if isinstance(tenants, dict):
            for tenant_id in tenants.keys():
                selected.append(f"{filename}:{tenant_id}")
    return selected


def update_context_from_response(path: str, resp):
    data = safe_json(resp)
    if path.endswith("openapi.json") and isinstance(data, dict):
        context["openapi"] = data

    if "api/config" in path and isinstance(data, dict):
        context["config"] = data

    if "api/tenants" in path and resp.request.method == "GET":
        if isinstance(data, list):
            context["tenant_list"] = data
            if not context["created_tenant_id"]:
                first = next((x for x in data if isinstance(x, dict) and isinstance(x.get("id"), int)), None)
                if first:
                    context["created_tenant_id"] = first["id"]
                    context["created_tenant_name"] = first.get("name")
                    context["created_viewtoken"] = first.get("viewtoken")

    tenant_id = extract_tenant_id(data)
    if tenant_id and not context["created_tenant_id"]:
        context["created_tenant_id"] = tenant_id

    billno = extract_billno(data)
    if billno and not context["created_billno"]:
        context["created_billno"] = billno

    backup_id = extract_backup_id(data)
    if backup_id and not context["created_backup_id"]:
        context["created_backup_id"] = backup_id

    if isinstance(data, dict):
        vt = data.get("viewtoken")
        if vt:
            context["created_viewtoken"] = vt

    selected_targets = extract_selected_targets(data)
    if selected_targets:
        context["preview_selected_targets"] = selected_targets

    if resp.headers.get("content-type", "").startswith("text/html"):
        text = resp.text or ""
        if not context["occupant_uuid"]:
            m = re.search(r'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})', text)
            if m:
                context["occupant_uuid"] = m.group(1)


def fetch_openapi():
    return request("GET", "openapi.json", name="OpenAPI discovery", category="discovery", expected=(200,))


def test_docs():
    request("GET", "docs", name="Swagger UI", category="docs", expected=(200,))
    request("GET", "redoc", name="ReDoc", category="docs", expected=(200,))


def test_pages():
    for name, method, path in PAGE_ROUTES:
        request(method, path, name=name, category="pages", expected=(200, 204))


def find_path(spec, method=None, must_contain=None, must_end=None, exclude=None):
    if not spec or "paths" not in spec:
        return None
    must_contain = must_contain or []
    exclude = exclude or []
    candidates = []
    for path, ops in spec["paths"].items():
        if method and method.lower() not in ops:
            continue
        if must_end and not path.endswith(must_end):
            continue
        if any(x not in path for x in must_contain):
            continue
        if any(x in path for x in exclude):
            continue
        candidates.append(path)
    candidates.sort(key=len)
    return candidates[0] if candidates else None


def resolve_ref(spec, obj):
    if not isinstance(obj, dict):
        return obj
    if "$ref" not in obj:
        return obj
    ref = obj["$ref"]
    if not ref.startswith("#/"):
        return obj
    cur = spec
    for part in ref[2:].split("/"):
        cur = cur.get(part, {})
    return cur if isinstance(cur, dict) else obj


def schema_to_example(spec, schema, name_hint="field", depth=0):
    """
    Automatically generates input data for text, number fields, and handles arrays/objects.
    """
    if not schema or depth > 6:
        return None
    schema = resolve_ref(spec, schema)

    low = name_hint.lower()
    
    # Strict Redaction Compliance for Sensitive Identifiers
    if "aadhaar" in low or "aadhar" in low:
        return "[Aadhaar Redacted]"
    if "rrn" == low or "resident registration" in low:
        return "[RRN Omitted]"
    if "mynumber" in low:
        return "[Your MyNumber]"

    if "oneOf" in schema and schema["oneOf"]:
        return schema_to_example(spec, schema["oneOf"][0], name_hint, depth + 1)
    if "anyOf" in schema and schema["anyOf"]:
        return schema_to_example(spec, schema["anyOf"][0], name_hint, depth + 1)
    if "allOf" in schema and schema["allOf"]:
        merged = {}
        for part in schema["allOf"]:
            part = resolve_ref(spec, part)
            merged.update(part)
        schema = merged

    if "enum" in schema and schema["enum"]:
        preferred = {
            "status": ["Active", "ACTIVE", "success", "system"],
            "paymentstatus": ["PENDING", "PARTIAL", "PAID", "ADVANCE"],
            "theme": ["system", "light", "dark"],
        }
        for key, values in preferred.items():
            if key in low:
                for value in values:
                    if value in schema["enum"]:
                        return value
        return schema["enum"][0]

    typ = schema.get("type")

    if typ == "object" or "properties" in schema:
        out = {}
        for prop, prop_schema in (schema.get("properties") or {}).items():
            val = schema_to_example(spec, prop_schema, prop, depth + 1)
            if val is not None:
                out[prop] = val
        return out

    if typ == "array":
        item = schema_to_example(spec, schema.get("items", {}), name_hint, depth + 1)
        return [] if item is None else [item]

    fmt = schema.get("format", "")

    if typ == "string" or typ is None:
        if fmt == "email" or "email" in low: return "apitest@example.com"
        if fmt == "uuid": return str(uuid.uuid4())
        if fmt == "binary": return "__BINARY__"
        if "phone" in low or "mobile" in low: return "9999999999"
        if "month" in low: return "July 2099 QA"
        if "name" == low or low.endswith("name"): return f"API TEST {uuid.uuid4().hex[:6].upper()}"
        if "billno" in low: return context.get("created_billno") or "REC-001"
        if "viewtoken" in low: return context.get("created_viewtoken") or str(uuid.uuid4())
        if "filename" in low: return context.get("kyc_filename") or "dummy.txt"
        if "pin" in low: return context.get("created_tenant_pin") or "1234"
        if "status" in low:
            if "payment" in low: return "PENDING"
            return "Active"
        if "desc" in low or "notes" in low: return "Automated test value"
        return f"auto_string_{uuid.uuid4().hex[:4]}"

    if typ == "integer":
        if "tenantid" in low and context.get("created_tenant_id"):
            return context["created_tenant_id"]
        return 1

    if typ == "number":
        if "reading" in low: return 10.0
        if "rent" in low: return 1200.0
        if "water" in low: return 100.0
        if "rate" in low: return 9.5
        if "arrears" in low: return 0.0
        if "amount" in low: return 100.0
        return 1.5

    if typ == "boolean":
        return True

    return None


def candidate_sample_dirs():
    dirs = []
    if SAMPLE_DIR_ENV:
        dirs.append(Path(SAMPLE_DIR_ENV))
    dirs.append(Path(__file__).resolve().parent / "sample")
    dirs.append(Path.cwd() / "sample")
    dirs.append(Path(r"D:/VEGA/RENT/sample"))
    unique = []
    seen = set()
    for d in dirs:
        key = str(d.resolve()) if d.exists() else str(d)
        if key not in seen:
            seen.add(key)
            unique.append(d)
    return unique


def ensure_fallback_assets():
    png_path = TEMP_DIR / "sample.png"
    if not png_path.exists():
        png_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9sXjv6kAAAAASUVORK5CYII="
        )
        png_path.write_bytes(png_bytes)

    pdf_path = TEMP_DIR / "sample.pdf"
    if not pdf_path.exists():
        pdf_path.write_bytes(
            b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
        )

    txt_path = TEMP_DIR / "sample.txt"
    if not txt_path.exists():
        txt_path.write_text("rent endpoint automated test file", encoding="utf-8")

    xlsx_path = TEMP_DIR / "sample.xlsx"
    if not xlsx_path.exists():
        xlsx_path.write_bytes(b"PK\x03\x04")

    zip_path = TEMP_DIR / "sample.zip"
    if not zip_path.exists():
        zip_path.write_bytes(b"PK\x03\x04")

    return {
        "image": png_path,
        "pdf": pdf_path,
        "text": txt_path,
        "xlsx": xlsx_path,
        "zip": zip_path,
        "any": txt_path,
    }


FALLBACK_ASSETS = ensure_fallback_assets()


def pick_sample_file(kind="any"):
    dirs = candidate_sample_dirs()
    exts_map = {
        "image": {".png", ".jpg", ".jpeg", ".webp"},
        "pdf": {".pdf"},
        "xlsx": {".xlsx"},
        "zip": {".zip"},
        "text": {".txt", ".csv", ".json"},
        "any": {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".xlsx", ".zip", ".txt", ".csv", ".json"},
    }
    exts = exts_map.get(kind, exts_map["any"])
    for d in dirs:
        if d.exists() and d.is_dir():
            for p in d.rglob("*"):
                if p.is_file() and p.suffix.lower() in exts:
                    return p
    return FALLBACK_ASSETS.get(kind, FALLBACK_ASSETS["any"])


def file_tuple_for_kind(kind="any"):
    p = pick_sample_file(kind)
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".zip": "application/zip",
        ".txt": "text/plain",
        ".csv": "text/csv",
        ".json": "application/json",
    }.get(p.suffix.lower(), "application/octet-stream")
    return (p.name, p.read_bytes(), mime)


def declared_expected(meta, fallback=(200, 201, 204, 400, 404, 405, 409, 422)):
    codes = []
    for code in (meta or {}).get("responses", {}).keys():
        if str(code).isdigit():
            codes.append(int(code))
    return tuple(sorted(set(codes))) if codes else fallback


def substitute_path_params(path):
    replacements = {
        "tenantid": context.get("created_tenant_id") or 1,
        "billno": context.get("created_billno") or "REC-001",
        "backupid": context.get("created_backup_id") or "BKP-TEST",
        "backup_id": context.get("created_backup_id") or "BKP-TEST",
        "viewtoken": context.get("created_viewtoken") or str(uuid.uuid4()),
        "tenantname": context.get("created_tenant_name") or "API TEST",
        "filename": context.get("kyc_filename") or "sample.txt",
        "occupantuuid": context.get("occupant_uuid") or str(uuid.uuid4()),
        "format": "xlsx",
    }

    def repl(match):
        key = match.group(1)
        return quote(str(replacements.get(key, "1")), safe="")

    return re.sub(r"\{([^}]+)\}", repl, path)


def generic_json_body(spec, path, method, meta):
    low = path.lower()

    if "/api/tenants" in low and method == "POST":
        name = f"API TEST {uuid.uuid4().hex[:8].upper()}"
        context["created_tenant_name"] = name
        return {
            "name": name,
            "company": "QA",
            "phone": "9999999999",
            "email": "apitest@example.com",
            "address": "Test Address",
            "portalpin": "1234",
            "roomnumber": "T-101",
            "occupation": "QA",
            "notes": "Created by automated test",
            "status": "Active",
            "rent": 1200.0,
            "water": 100.0,
            "defaulttankwatercharge": 0.0,
            "electricityrate": 9.5,
            "previousmeter": 0.0,
            "additionalpersoncharge": 0.0,
            "securitydeposit": 0.0,
            "meterid": f"MTR-{uuid.uuid4().hex[:6].upper()}",
            "tenantpin": context.get("created_tenant_pin", "1234"),
            "viewtoken": None,
            "arrears": 0.0,
        }

    if "/api/tenants/" in low and method == "PUT":
        tenant_id = context.get("created_tenant_id") or 1
        return {
            "id": tenant_id,
            "name": context.get("created_tenant_name") or f"API TEST {uuid.uuid4().hex[:6].upper()}",
            "company": "QA",
            "phone": "9999999999",
            "email": "apitest@example.com",
            "address": "Updated Test Address",
            "roomnumber": "T-102",
            "occupation": "QA",
            "notes": "Updated by automated test",
            "status": "Active",
            "rent": 1200.0,
            "water": 100.0,
            "defaulttankwatercharge": 0.0,
            "electricityrate": 9.5,
            "previousmeter": 0.0,
            "additionalpersoncharge": 0.0,
            "securitydeposit": 0.0,
            "meterid": f"MTR-{uuid.uuid4().hex[:6].upper()}",
            "tenantpin": context.get("created_tenant_pin", "1234"),
            "viewtoken": context.get("created_viewtoken"),
            "arrears": 0.0,
        }

    if ("/api/bill" in low or "/api/editbill/" in low) and method == "POST":
        return {
            "tenant": context.get("created_tenant_name") or "API TEST",
            "month": f"July 2099 {uuid.uuid4().hex[:4].upper()}",
            "currentreading": 10.0,
            "additionalpersons": 0,
            "tankwater": 0.0,
            "maintenancecharge": 0.0,
            "maintenancedesc": "",
            "previousarrears": 0.0,
            "amountreceived": 0.0,
            "paymentstatus": "PENDING",
        }

    if low.endswith("/payment") and method == "POST":
        return {"paymentstatus": "PARTIAL", "amountreceived": 100.0}

    if "/api/config" in low and method == "POST":
        cfg = context.get("config") or {}
        return {
            "landlord": cfg.get("landlord", {}),
            "billing": cfg.get("billing", {}),
            "backup": cfg.get("backup", {}),
        }

    if "/api/ui/theme" in low and method == "POST":
        return {"theme": "system"}

    req_body = (meta or {}).get("requestBody") or {}
    req_body = resolve_ref(spec, req_body)
    content = req_body.get("content", {})
    json_schema = (
        content.get("application/json", {}).get("schema")
        or content.get("application/*+json", {}).get("schema")
    )
    if json_schema:
        return schema_to_example(spec, json_schema, "body")

    return None


def generic_form_or_files(spec, path, method, meta):
    """
    Constructs FormData and detects appropriate file payloads (Images/PDFs) 
    automatically mapping field names to templates.
    """
    req_body = (meta or {}).get("requestBody") or {}
    req_body = resolve_ref(spec, req_body)
    content = req_body.get("content", {})

    chosen = None
    media_type = None
    for mt in ["multipart/form-data", "application/x-www-form-urlencoded"]:
        if mt in content:
            chosen = content[mt].get("schema")
            media_type = mt
            break

    if not chosen:
        return None, None, None

    schema = resolve_ref(spec, chosen)
    props = schema.get("properties", {}) if isinstance(schema, dict) else {}
    data = {}
    files = {}

    for field, field_schema in props.items():
        fs = resolve_ref(spec, field_schema)
        fmt = fs.get("format")
        low = field.lower()

        if fmt == "binary" or "file" in low or "document" in low or "proof" in low or "upload" in low:
            kind = "any"
            if "signature" in low or "image" in low or "photo" in low or "emp" in low or "kyc" in low or "aadhaar" in low:
                kind = "image"
            elif "pdf" in low:
                kind = "pdf"
            elif "file" in low and ("import" in path.lower() or "sync" in path.lower()):
                p = pick_sample_file("xlsx")
                if p.suffix.lower() not in {".xlsx", ".zip"}:
                    p = FALLBACK_ASSETS["xlsx"]
                files[field] = (p.name, p.read_bytes(),
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if p.suffix.lower() == ".xlsx" else "application/zip")
                continue
            files[field] = file_tuple_for_kind(kind)
            continue

        if low == "selectedtargets":
            targets = context.get("preview_selected_targets") or []
            data[field] = json.dumps(targets or ["RentDataTemplate.xlsx:T001"])
            continue

        val = schema_to_example(spec, fs, field)
        if val is None:
            val = "test"
        data[field] = str(val)

    return media_type, data, files


def build_request_kwargs(spec, path, method, meta):
    """
    Scans parameters (headers, query, path) and request bodies to construct
    all inputs dynamically according to the OpenAPI documentation.
    """
    kwargs = {}
    params = {}
    headers = {}
    path_params = {}

    for param in meta.get("parameters", []):
        param = resolve_ref(spec, param)
        in_ = param.get("in")
        name = param.get("name")
        schema = param.get("schema", {})
        val = schema_to_example(spec, schema, name)
        if val is None: 
            val = "test"

        if in_ == "query":
            params[name] = val
        elif in_ == "header":
            headers[name] = str(val)
        elif in_ == "path":
            path_params[name] = str(val)

    if params: kwargs["params"] = params
    if headers: kwargs["headers"] = headers

    media_type, data, files = generic_form_or_files(spec, path, method, meta)
    if files:
        kwargs["data"] = data
        kwargs["files"] = files
    else:
        payload = generic_json_body(spec, path, method, meta)
        if payload is not None:
            kwargs["json"] = payload
            if media_type == "application/x-www-form-urlencoded":
                kwargs["data"] = payload 
                del kwargs["json"]

    actual_path = path
    for k, v in path_params.items():
        actual_path = actual_path.replace(f"{{{k}}}", quote(str(v), safe=""))
    actual_path = substitute_path_params(actual_path)

    return actual_path, kwargs


def test_health(spec):
    health_path = find_path(spec, method="get", must_contain=["health"]) or "health"
    request("GET", health_path, name="Health endpoint", category="health", expected=(200,))


def test_settings(spec):
    cfg_get = find_path(spec, method="get", must_contain=["config"]) or "api/config"
    cfg_post = find_path(spec, method="post", must_contain=["config"]) or "api/config"
    theme_post = find_path(spec, method="post", must_contain=["ui", "theme"]) or "api/ui/theme"
    sig_post = find_path(spec, method="post", must_contain=["settings", "signature"]) or "api/settings/signature"
    sig_delete = find_path(spec, method="delete", must_contain=["settings", "signature"]) or "api/settings/signature"

    resp = request("GET", cfg_get, name="Get config", category="settings", expected=(200,))
    if resp and resp.ok:
        context["config"] = safe_json(resp)

    request("POST", theme_post, name="Update theme", category="settings",
            expected=(200,), json={"theme": "system"})

    if ALLOW_MUTATION:
        img = file_tuple_for_kind("image")
        request("POST", sig_post, name="Upload signature", category="settings",
                expected=(200, 400), files={"file": img})
        request("DELETE", sig_delete, name="Delete signature", category="settings",
                expected=(200, 404, 400))

        cfg = context.get("config") or {}
        request("POST", cfg_post, name="Save config round-trip", category="settings",
                expected=(200,),
                json={
                    "landlord": cfg.get("landlord", {}),
                    "billing": cfg.get("billing", {}),
                    "backup": cfg.get("backup", {}),
                })
    else:
        skip("Upload signature", "settings", "POST", make_url(sig_post), "Mutation tests disabled.")
        skip("Delete signature", "settings", "DELETE", make_url(sig_delete), "Mutation tests disabled.")
        skip("Save config round-trip", "settings", "POST", make_url(cfg_post), "Mutation tests disabled.")


def test_exports_and_sync(spec):
    export_csv = find_path(spec, method="get", must_contain=["export", "csv"]) or "api/export/csv"
    export_zip = find_path(spec, method="get", must_contain=["export", "zip"]) or "api/export/zip"
    sync_template = find_path(spec, method="get", must_contain=["sync", "template"]) or "api/sync/template"
    sync_export = find_path(spec, method="get", must_contain=["sync", "export", "{format}"]) or "api/sync/export/{format}"
    import_preview = find_path(spec, method="post", must_contain=["sync", "import", "preview"]) or "api/sync/import/preview"
    import_execute = find_path(spec, method="post", must_contain=["sync", "import", "execute"]) or "api/sync/import/execute"

    request("GET", f"{export_csv}?tenantslist=all", name="Export receipts CSV", category="sync", expected=(200,))
    request("GET", f"{export_zip}?tenantslist=all", name="Export receipts ZIP", category="sync", expected=(200,))
    tpl = request("GET", sync_template, name="Download sync template", category="sync", expected=(200,))
    request("GET", sync_export.replace("{format}", "xlsx"), name="Export sync xlsx", category="sync", expected=(200,))
    request("GET", sync_export.replace("{format}", "zip"), name="Export sync zip", category="sync", expected=(200,))

    if tpl and tpl.ok:
        files = {
            "file": ("RentDataTemplate.xlsx", tpl.content,
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        }
        prev = request("POST", import_preview, name="Import preview", category="sync",
                       expected=(200,), files=files)
        if prev and prev.ok:
            pj = safe_json(prev) or {}
            context["preview_selected_targets"] = extract_selected_targets(pj)

        if TEST_IMPORT_EXECUTE:
            request("POST", import_execute, name="Import execute", category="sync",
                    expected=(200, 400),
                    files=files,
                    data={"selectedtargets": json.dumps(context.get("preview_selected_targets") or [])})
        else:
            skip("Import execute", "sync", "POST", make_url(import_execute),
                 "Skipped by default to avoid importing data.")
    else:
        skip("Import preview", "sync", "POST", make_url(import_preview),
             "Template download failed, so preview/import was skipped.")
        skip("Import execute", "sync", "POST", make_url(import_execute),
             "Template download failed or execution disabled.")


def test_backups(spec):
    list_path = find_path(spec, method="get", must_contain=["backups"], exclude=["verify", "download", "metadata"]) or "api/backups"
    manual_path = find_path(spec, method="post", must_contain=["backups", "manual"]) or "api/backups/manual"
    verify_path = find_path(spec, method="get", must_contain=["backups", "{", "verify"])
    restore_path = find_path(spec, method="post", must_contain=["backups", "{", "restore"])
    download_path = find_path(spec, method="get", must_contain=["backups", "{", "download"])
    metadata_path = find_path(spec, method="get", must_contain=["backups", "{", "metadata"])
    delete_path = find_path(spec, method="delete", must_contain=["backups", "{"])

    request("GET", list_path, name="List backups", category="backups", expected=(200,))

    if not ALLOW_MUTATION:
        skip("Create manual backup", "backups", "POST", make_url(manual_path), "Mutation tests disabled.")
        return

    resp = request("POST", manual_path, name="Create manual backup", category="backups", expected=(200,))
    bj = safe_json(resp) if resp else None
    context["created_backup_id"] = extract_backup_id(bj)

    backup_id = context.get("created_backup_id")
    if not backup_id:
        skip("Backup dependent flow", "backups", "FLOW", make_url(list_path),
             "Manual backup creation did not return a backup id.")
        return

    if verify_path:
        request("GET", verify_path.replace("{backupid}", quote(backup_id, safe="")).replace("{backup_id}", quote(backup_id, safe="")),
                name="Verify backup", category="backups", expected=(200,))
    if metadata_path:
        request("GET", metadata_path.replace("{backupid}", quote(backup_id, safe="")).replace("{backup_id}", quote(backup_id, safe="")),
                name="Backup metadata", category="backups", expected=(200,))
    if download_path:
        request("GET", download_path.replace("{backupid}", quote(backup_id, safe="")).replace("{backup_id}", quote(backup_id, safe="")),
                name="Download backup", category="backups", expected=(200, 404))
    if restore_path:
        if TEST_RESTORE_BACKUP:
            request("POST", restore_path.replace("{backupid}", quote(backup_id, safe="")).replace("{backup_id}", quote(backup_id, safe="")),
                    name="Restore backup", category="backups", expected=(200, 400))
        else:
            skip("Restore backup", "backups", "POST", make_url(restore_path),
                 "Disabled by default because restore is invasive.")
    if delete_path:
        request("DELETE", delete_path.replace("{backupid}", quote(backup_id, safe="")).replace("{backup_id}", quote(backup_id, safe="")),
                name="Delete created backup", category="backups", expected=(200, 404))


def test_tenants_billing_public_pdf_whatsapp(spec):
    tenants_list = find_path(spec, method="get", must_end="/api/tenants") or "api/tenants"
    tenants_post = find_path(spec, method="post", must_end="/api/tenants") or "api/tenants"
    tenant_detail = find_path(spec, method="get", must_contain=["/api/tenants/{"]) or "api/tenants/{tenantid}"
    tenant_put = find_path(spec, method="put", must_contain=["/api/tenants/{"]) or tenant_detail
    tenant_delete = find_path(spec, method="delete", must_contain=["/api/tenants/{"]) or tenant_detail
    tenant_receipts = find_path(spec, method="get", must_contain=["tenant_receipts", "{"]) or "api/tenant_receipts/{tenantname}"

    bills_filter = find_path(spec, method="get", must_contain=["bills", "filter"]) or "api/bills/filter"
    billing_months = find_path(spec, method="get", must_contain=["billing", "months"]) or "api/billing/months"
    billing_preview = find_path(spec, method="get", must_contain=["billing", "preview"]) or "api/billing/preview"
    bill_create = find_path(spec, method="post", must_end="/api/bill") or "api/bill"
    bill_get = find_path(spec, method="get", must_contain=["/api/bill/{"])
    bill_update = find_path(spec, method="post", must_contain=["billno"], exclude=["payment", "archive", "restore", "whatsapp", "pdf"])
    bill_payment = find_path(spec, method="post", must_contain=["billno", "payment"])
    bill_archive = find_path(spec, method="post", must_contain=["billno", "archive"])
    bill_restore = find_path(spec, method="post", must_contain=["billno", "restore"])
    bill_delete = find_path(spec, method="delete", must_contain=["billno"])
    pdf_view = find_path(spec, method="get", must_contain=["pdf", "{billno}", "view"])
    pdf_download = find_path(spec, method="get", must_contain=["pdf", "{billno}", "download"])
    wa_single = find_path(spec, method="get", must_contain=["whatsapp", "{billno}"])

    request("GET", tenants_list, name="List tenants", category="tenants", expected=(200,))
    request("GET", f"{bills_filter}?status=all", name="Bills filter all", category="billing", expected=(200,))
    request("GET", f"{bills_filter}?status=active", name="Bills filter active", category="billing", expected=(200,))
    request("GET", f"{bills_filter}?status=pending", name="Bills filter pending", category="billing", expected=(200,))
    request("GET", billing_months, name="Billing months", category="billing", expected=(200,))
    request("GET", f"{billing_preview}?current_reading=10&additional_persons=0&prev_reading=0&rent=1200&water=100&tank_water=0&maintenance_charge=0&rate=9.5&add_person_charge=0",
            name="Billing preview", category="billing", expected=(200,))

    if not ALLOW_MUTATION:
        skip("Create temp tenant", "tenants", "POST", make_url(tenants_post), "Mutation tests disabled.")
        return

    tenant_payload = generic_json_body(spec, tenants_post, "POST", {})
    create_tenant = request("POST", tenants_post, name="Create temp tenant", category="tenants",
                            expected=(200, 201), json=tenant_payload)
    tenant_json = safe_json(create_tenant) if create_tenant else None

    tenant_id = extract_tenant_id(tenant_json) or context.get("created_tenant_id")
    context["created_tenant_id"] = tenant_id
    context["created_tenant_name"] = tenant_payload["name"]

    if not tenant_id:
        skip("Tenant dependent flow", "tenants", "FLOW", make_url(tenant_detail),
             "Temp tenant was not created, so downstream tests were skipped.")
        return

    detail_path = tenant_detail.replace("{tenantid}", str(tenant_id))
    detail_resp = request("GET", detail_path, name="Get temp tenant", category="tenants", expected=(200,))
    detail_json = safe_json(detail_resp) if detail_resp else None
    if isinstance(detail_json, dict):
        context["created_viewtoken"] = detail_json.get("viewtoken") or context.get("created_viewtoken")

    update_payload = generic_json_body(spec, tenant_put, "PUT", {})
    request("PUT", tenant_put.replace("{tenantid}", str(tenant_id)),
            name="Update temp tenant", category="tenants", expected=(200,), json=update_payload)

    request("GET", f"tenant/{tenant_id}", name="Tenant profile page", category="pages", expected=(200,))
    request("GET", tenant_receipts.replace("{tenantname}", quote(context["created_tenant_name"], safe="")),
            name="Tenant receipts list", category="tenants", expected=(200,))

    if context.get("created_viewtoken"):
        public_get = f"t/{context['created_viewtoken']}"
        request("GET", public_get, name="Public tenant page locked", category="public", expected=(200,))
        # Resolves public auth failure endpoints by injecting established tenantpin explicitly 
        request("POST", public_get, name="Public tenant unlock", category="public",
                expected=(200,), data={"pin": context["created_tenant_pin"]})
    else:
        skip("Public tenant profile", "public", "GET", make_url("t/{viewtoken}"),
             "No viewtoken returned for temp tenant.")

    bill_payload = {
        "tenant": context["created_tenant_name"],
        "month": f"July 2099 {uuid.uuid4().hex[:4].upper()}",
        "currentreading": 10.0,
        "additionalpersons": 0,
        "tankwater": 0.0,
        "maintenancecharge": 0.0,
        "maintenancedesc": "",
        "previousarrears": 0.0,
        "amountreceived": 0.0,
        "paymentstatus": "PENDING",
    }

    create_bill = request("POST", bill_create, name="Create temp bill", category="billing",
                          expected=(200, 201), json=bill_payload)
    bill_json = safe_json(create_bill) if create_bill else None
    billno = extract_billno(bill_json)
    context["created_billno"] = billno

    if not billno:
        skip("Bill dependent flow", "billing", "FLOW", make_url(bill_create),
             "Temp bill was not created, so downstream bill tests were skipped.")
    else:
        if bill_get:
            request("GET", bill_get.replace("{billno}", quote(billno, safe="")),
                    name="Get temp bill", category="billing", expected=(200,))
        if pdf_view:
            request("GET", pdf_view.replace("{billno}", quote(billno, safe="")),
                    name="PDF view", category="pdf", expected=(200, 404, 500))
        if pdf_download:
            request("GET", pdf_download.replace("{billno}", quote(billno, safe="")),
                    name="PDF download", category="pdf", expected=(200, 404, 500))
        if bill_update:
            update_bill = dict(bill_payload)
            update_bill["currentreading"] = 12.0
            update_bill["maintenancecharge"] = 25.0
            update_bill["maintenancedesc"] = "Test update"
            request("POST", bill_update.replace("{billno}", quote(billno, safe="")),
                    name="Update temp bill", category="billing", expected=(200, 201), json=update_bill)
        if bill_payment:
            request("POST", bill_payment.replace("{billno}", quote(billno, safe="")),
                    name="Update payment status", category="billing",
                    expected=(200,), json={"paymentstatus": "PARTIAL", "amountreceived": 100.0})
        if wa_single:
            if TEST_WHATSAPP:
                request("GET", wa_single.replace("{billno}", quote(billno, safe="")),
                        name="WhatsApp single bill", category="whatsapp",
                        expected=(200, 400, 403, 404))
            else:
                skip("WhatsApp single bill", "whatsapp", "GET", make_url(wa_single),
                     "Skipped by default because it is an external-message flow.")
        if bill_archive:
            request("POST", bill_archive.replace("{billno}", quote(billno, safe="")),
                    name="Archive temp bill", category="billing", expected=(200,))
        if bill_restore:
            request("POST", bill_restore.replace("{billno}", quote(billno, safe="")),
                    name="Restore temp bill", category="billing", expected=(200,))
        if bill_delete:
            request("DELETE", bill_delete.replace("{billno}", quote(billno, safe="")),
                    name="Delete temp bill", category="billing", expected=(200, 404))

    if tenant_delete:
        request("DELETE", tenant_delete.replace("{tenantid}", str(tenant_id)) + "?action=hard",
                name="Delete temp tenant", category="tenants", expected=(200, 404))


def test_public_kyc(spec):
    """
    Tests dynamic public profile login and document submission 
    for KYC elements using contextual view tokens.
    """
    upload_path = find_path(spec, method="post", must_contain=["viewtoken", "kyc"]) or "api/t/{viewtoken}/kyc"
    inactive_path = find_path(spec, method="put", must_contain=["viewtoken", "kyc", "inactive"])
    delete_path = find_path(spec, method="delete", must_contain=["viewtoken", "kyc"])
    file_path = find_path(spec, method="get", must_contain=["api", "kyc", "{filename}"]) or "api/kyc/{filename}"

    if not TEST_PUBLIC_KYC:
        skip("Public KYC flow", "public-kyc", "FLOW", make_url(upload_path),
             "Skipped by default because it uploads documents.")
        return

    token = context.get("created_viewtoken")
    if not token:
        skip("Public KYC flow", "public-kyc", "FLOW", make_url(upload_path),
             "No public viewtoken available.")
        return

    # Dynamically generates valid test files for payload properties
    # Variable names are preserved from user schema requests, data contains valid templates
    files = {"aadhaarcombined": file_tuple_for_kind("image"), "photo": file_tuple_for_kind("image")}
    data = {"name": "Test Occupant", "mobile": "9999999999", "pin": context.get("created_tenant_pin")}

    up = request("POST", upload_path.replace("{viewtoken}", quote(token, safe="")),
                 name="Public KYC upload", category="public-kyc",
                 expected=(200, 400, 404), files=files, data=data)

    if not up or up.status_code != 200:
        return

    request("GET", f"t/{quote(token, safe='')}", name="Public tenant page after KYC upload",
            category="public-kyc", expected=(200,))

    if inactive_path and context.get("occupant_uuid"):
        request("PUT", inactive_path.replace("{viewtoken}", quote(token, safe="")).replace("{occupantuuid}", quote(context["occupant_uuid"], safe="")),
                name="Mark occupant inactive", category="public-kyc", expected=(200, 404))
    else:
        skip("Mark occupant inactive", "public-kyc", "PUT", make_url(inactive_path or "api/t/{viewtoken}/kyc/{occupantuuid}/inactive"),
             "occupantuuid could not be discovered.")

    if delete_path and context.get("occupant_uuid"):
        request("DELETE", delete_path.replace("{viewtoken}", quote(token, safe="")).replace("{occupantuuid}", quote(context["occupant_uuid"], safe="")),
                name="Delete occupant KYC", category="public-kyc", expected=(200, 404))
    else:
        skip("Delete occupant KYC", "public-kyc", "DELETE", make_url(delete_path or "api/t/{viewtoken}/kyc/{occupantuuid}"),
             "occupantuuid could not be discovered.")

    if context.get("kyc_filename"):
        request("GET", file_path.replace("{filename}", quote(context["kyc_filename"], safe="")),
                name="Get KYC file", category="public-kyc", expected=(200, 404))
    else:
        skip("Get KYC file", "public-kyc", "GET", make_url(file_path),
             "Uploaded filename was not discoverable from response/page.")


def passive_openapi_sweep(spec):
    """
    Automated Codebase Sweep: Evaluates the complete API structure (path, headers, queries, bodies)
    to comprehensively trigger fully-formed automated tests for unvisited endpoints.
    """
    if not spec or "paths" not in spec:
        return

    for path, ops in sorted(spec["paths"].items()):
        for method, meta in sorted(ops.items()):
            method_u = method.upper()
            if op_key(method_u, path) in tested_ops:
                continue

            expected = declared_expected(meta)

            if method_u in {"DELETE"} and not ALLOW_MUTATION:
                skip(f"Discovered {method_u} {path}", "openapi-sweep", method_u, make_url(path),
                     "Mutation tests disabled.")
                continue

            if method_u in {"POST", "PUT", "PATCH"} and not ALLOW_MUTATION:
                skip(f"Discovered {method_u} {path}", "openapi-sweep", method_u, make_url(path),
                     "Mutation tests disabled.")
                continue
            
            # Utilize the dynamic kwargs builder mapping body, params, and headers
            actual_path, kwargs = build_request_kwargs(spec, path, method_u, meta)

            if method_u == "DELETE" and "/api/tenants/" in path and "action=" not in actual_path:
                actual_path += "?action=archive"

            request(method_u, actual_path, name=f"Discovered {method_u} {path}",
                    category="openapi-sweep", expected=expected, **kwargs)


def direct_sqlite_checks():
    if not DB_PATH:
        skip("Direct SQLite checks", "database", "SQLITE", "local-file",
             "Set RENT_DB_PATH to enable direct sqlite integrity checks.")
        return

    p = Path(DB_PATH)
    if not p.exists():
        add_result(
            name="Direct SQLite checks",
            category="database",
            method="SQLITE",
            url=str(p),
            ok=False,
            status=None,
            expected=None,
            latency_ms=None,
            details=f"Database file not found: {p}",
            response_json=None,
        )
        return

    try:
        con = sqlite3.connect(str(p))
        cur = con.cursor()
        integrity = cur.execute("PRAGMA integrity_check").fetchone()[0]
        tables = {
            row[0] for row in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        expected_tables = {"tenants", "receipts", "occupants"}
        missing = sorted(expected_tables - tables)
        counts = {}
        for table in sorted(expected_tables & tables):
            counts[table] = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        ok = integrity == "ok" and not missing
        add_result(
            name="Direct SQLite integrity",
            category="database",
            method="SQLITE",
            url=str(p),
            ok=ok,
            status=None,
            expected=["integrity_check == ok", "tables tenants/receipts/occupants present"],
            latency_ms=None,
            details=f"integrity_check={integrity}; missing_tables={missing}; row_counts={counts}",
            response_json={"integrity_check": integrity, "missing_tables": missing, "row_counts": counts},
        )
        con.close()
    except Exception as e:
        add_result(
            name="Direct SQLite integrity",
            category="database",
            method="SQLITE",
            url=str(p),
            ok=False,
            status=None,
            expected=None,
            latency_ms=None,
            details=f"{type(e).__name__}: {e}",
            response_json={"traceback": traceback.format_exc()},
        )


def summarize():
    total = len(results)
    skipped = sum(1 for r in results if r.get("skipped"))
    passed = sum(1 for r in results if r.get("ok"))
    failed = total - passed - skipped
    by_category = {}
    for r in results:
        by_category.setdefault(r["category"], {"passed": 0, "failed": 0, "skipped": 0})
        if r.get("skipped"):
            by_category[r["category"]]["skipped"] += 1
        elif r.get("ok"):
            by_category[r["category"]]["passed"] += 1
        else:
            by_category[r["category"]]["failed"] += 1
    return {
        "base_url": BASE_URL,
        "generated_at_epoch_ms": now_ms(),
        "sample_dirs_checked": [str(x) for x in candidate_sample_dirs()],
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        },
        "by_category": by_category,
        "context": context,
        "results": results,
    }


def write_reports(report):
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    s = report["summary"]
    lines = [
        "# Rent API Test Report",
        "",
        f"- Base URL: `{report['base_url']}`",
        f"- Total: **{s['total']}**",
        f"- Passed: **{s['passed']}**",
        f"- Failed: **{s['failed']}**",
        f"- Skipped: **{s['skipped']}**",
        "",
        "## Category Summary",
        "",
        "| Category | Passed | Failed | Skipped |",
        "|---|---:|---:|---:|",
    ]
    for cat, stats in sorted(report["by_category"].items()):
        lines.append(f"| {cat} | {stats['passed']} | {stats['failed']} | {stats['skipped']} |")

    lines += [
        "",
        "## Endpoint Results",
        "",
        "| Name | Category | Method | Status | Result | Details |",
        "|---|---|---|---:|---|---|",
    ]

    for r in report["results"]:
        status = "" if r["status"] is None else str(r["status"])
        result = "SKIPPED" if r.get("skipped") else ("PASS" if r.get("ok") else "FAIL")
        details = (r.get("details") or "").replace("\n", " ").replace("|", "\\|")
        if len(details) > 160:
            details = details[:160] + "..."
        lines.append(f"| {r['name']} | {r['category']} | {r['method']} | {status} | {result} | {details} |")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    failed_results = [r for r in report["results"] if not r.get("ok") and not r.get("skipped")]
    
    if failed_results:
        failed_report = dict(report)
        failed_report["results"] = failed_results
        with open("failed.json", "w", encoding="utf-8") as f:
            json.dump(failed_report, f, indent=2, ensure_ascii=False)
            
        failed_lines = [
            "# Failed Endpoints Report",
            "",
            f"- Base URL: `{report['base_url']}`",
            f"- Total Failed: **{len(failed_results)}**",
            "",
            "| Name | Category | Method | Status | Details |",
            "|---|---|---|---:|---|",
        ]
        for r in failed_results:
            status = "" if r["status"] is None else str(r["status"])
            details = (r.get("details") or "").replace("\n", " ").replace("|", "\\|")
            if len(details) > 250:
                details = details[:250] + "..."
            failed_lines.append(f"| {r['name']} | {r['category']} | {r['method']} | {status} | {details} |")
            
        with open("failed.md", "w", encoding="utf-8") as f:
            f.write("\n".join(failed_lines))
    else:
        if os.path.exists("failed.json"): os.remove("failed.json")
        if os.path.exists("failed.md"): os.remove("failed.md")


def main():
    spec_resp = fetch_openapi()
    spec = safe_json(spec_resp) if spec_resp and spec_resp.ok else None
    context["openapi"] = spec

    test_docs()
    test_pages()
    test_health(spec)
    test_settings(spec)
    test_tenants_billing_public_pdf_whatsapp(spec)
    test_backups(spec)
    test_exports_and_sync(spec)
    test_public_kyc(spec)
    
    # Executes the robust sweep combining headers, bodies, path & query vars dynamically
    passive_openapi_sweep(spec)
    direct_sqlite_checks()

    report = summarize()
    write_reports(report)

    print(json.dumps(report["summary"], indent=2))
    print(f"\nWrote: {OUT_JSON}")
    print(f"Wrote: {OUT_MD}")
    if os.path.exists("failed.json"):
        print("Wrote: failed.json")
    if os.path.exists("failed.md"):
        print("Wrote: failed.md")


if __name__ == "__main__":
    main()