from __future__ import annotations

import re
import secrets
from typing import Iterable

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

router = APIRouter(tags=["Landlord Route Alias"])

LANDLORD_ID_LENGTH = 16
LANDLORD_ID_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"
LANDLORD_ID_RE = re.compile(r"^[0-9a-z]{16}$")

RESERVED_LANDLORD_IDS = {
    "landlord",
    "platform-admin",
    "api",
    "static",
    "landlordassets",
    "tassets",
    "t",
    "health",
    "favicon.ico",
    "robots.txt",
    "assets",
}


def generate_landlordUuid(size: int = LANDLORD_ID_LENGTH) -> str:
    if size < 10:
        raise ValueError("landlord uuid size must be at least 10")
    return "".join(secrets.choice(LANDLORD_ID_ALPHABET) for _ in range(size))


def is_valid_landlordUuid(value: str) -> bool:
    return bool(LANDLORD_ID_RE.fullmatch(value))


def validate_landlordUuid(value: str) -> None:
    if not value:
        raise HTTPException(status_code=404, detail="Missing landlord uuid")
    if value in RESERVED_LANDLORD_IDS:
        raise HTTPException(status_code=404, detail="Reserved landlord uuid")
    if not is_valid_landlordUuid(value):
        raise HTTPException(status_code=404, detail="Invalid landlord uuid format")

    from app.core.db import get_conn
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM landlords WHERE landlordUuid = ? AND active = 1", (value,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Landlord not found or inactive")


def external_base(landlordUuid: str) -> str:
    return f"/{landlordUuid}"


def internal_landlord_path(path: str | None) -> str:
    clean = (path or "").strip("/")
    return "/landlord" if not clean else f"/landlord/{clean}"


def internal_asset_path(path: str | None) -> str:
    clean = (path or "").lstrip("/")
    return "/landlord/assets" if not clean else f"/landlord/assets/{clean}"


def rewrite_location(location: str, landlordUuid: str) -> str:
    ext = external_base(landlordUuid)
    rewrites = [
        (f"{ext}/landlord/", f"{ext}/"),
        (f"{ext}/landlord", ext),
        ("/landlord/", f"{ext}/"),
        ("/landlord", ext),
    ]
    result = location
    for old, new in rewrites:
        if result == old or result.startswith(old):
            result = new + result[len(old):]
    return result


def rewrite_set_cookie(cookie_value: str, landlordUuid: str) -> str:
    ext = external_base(landlordUuid)
    rewrites = [
        (f"Path={ext}/landlord/", f"Path={ext}/"),
        (f"Path={ext}/landlord", f"Path={ext}"),
        ("Path=/landlord/", f"Path={ext}/"),
        ("Path=/landlord", f"Path={ext}"),
    ]
    result = cookie_value
    for old, new in rewrites:
        result = result.replace(old, new)
    return result


def filtered_headers(request: Request, landlordUuid: str) -> list[tuple[str, str]]:
    blocked = {"host", "content-length"}
    headers: list[tuple[str, str]] = []
    for key, value in request.headers.multi_items():
        if key.lower() in blocked:
            continue
        headers.append((key, value))
    headers.append(("x-forwarded-prefix", external_base(landlordUuid)))
    headers.append(("x-landlord-uuid", landlordUuid))
    headers.append(("x-landlord-alias", "1"))
    return headers


async def proxy_to_internal(
    request: Request,
    landlordUuid: str,
    target_path: str,
) -> Response:
    body = await request.body()
    headers = filtered_headers(request, landlordUuid)

    transport = httpx.ASGITransport(app=request.app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://landlord-alias.internal",
        follow_redirects=False,
    ) as client:
        upstream = await client.request(
            method=request.method,
            url=target_path,
            params=request.query_params,
            content=body,
            headers=headers,
        )

    response = Response(
        content=upstream.content,
        status_code=upstream.status_code,
    )

    excluded = {
        "content-length",
        "transfer-encoding",
        "connection",
        "keep-alive",
        "server",
        "date",
    }

    for key, value in upstream.headers.multi_items():
        lower = key.lower()
        if lower in excluded:
            continue
        if lower == "location":
            value = rewrite_location(value, landlordUuid)
        elif lower == "set-cookie":
            value = rewrite_set_cookie(value, landlordUuid)
        response.headers.append(key, value)

    return response


LANDLORD_METHODS: list[str] = [
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
    "HEAD",
]

ASSET_METHODS: list[str] = ["GET", "HEAD"]


@router.api_route(
    "/{landlordUuid}/assets/{asset_path:path}",
    methods=ASSET_METHODS,
    include_in_schema=False,
)
async def landlord_asset_alias(
    landlordUuid: str,
    asset_path: str,
    request: Request,
) -> Response:
    validate_landlordUuid(landlordUuid)
    return await proxy_to_internal(
        request=request,
        landlordUuid=landlordUuid,
        target_path=internal_asset_path(asset_path),
    )


@router.api_route(
    "/{landlordUuid}",
    methods=LANDLORD_METHODS,
    include_in_schema=False,
)
@router.api_route(
    "/{landlordUuid}/{path:path}",
    methods=LANDLORD_METHODS,
    include_in_schema=False,
)
async def landlord_admin_alias(
    landlordUuid: str,
    request: Request,
    path: str = "",
) -> Response:
    validate_landlordUuid(landlordUuid)

    normalized = (path or "").strip("/")

    if normalized.startswith("assets/"):
        return await proxy_to_internal(
            request=request,
            landlordUuid=landlordUuid,
            target_path=internal_asset_path(normalized[len("assets/"):]),
        )

    return await proxy_to_internal(
        request=request,
        landlordUuid=landlordUuid,
        target_path=internal_landlord_path(normalized),
    )
