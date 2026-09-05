#!/usr/bin/env node
/**
 * route-migrate.mjs — Route-base migration tool for the Rent Receipt System.
 *
 * Migrates the canonical base path from `/rent/` to `/` across the frontend
 * (4 SPAs + shared config), Cloudflare Pages config, and nginx infra.
 *
 * Commands:
 *   node scripts/route-migrate.mjs discover            # scan -> migration-plan.json + report
 *   node scripts/route-migrate.mjs apply [--dry-run]   # apply MIGRATE edits (+ .bak backups)
 *   node scripts/route-migrate.mjs verify              # re-scan + infra/build assertions
 *
 * Design principles:
 *   - Type-aware transforms, NOT blind string replacement.
 *   - Idempotent: re-running apply is a no-op once migrated.
 *   - Safe: .bak backup before every write; --dry-run emits a unified diff only.
 *   - Classifies every /rent occurrence: MIGRATE (drop prefix) / SKIP (docs/comments) /
 *     INFRA (nginx) / WARNING (manual review).
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");

const STATE_DIR = path.join(ROOT, ".migrate");
const PLAN_JSON = path.join(STATE_DIR, "migration-plan.json");
const PLAN_MD = path.join(STATE_DIR, "migration-report.md");
const LOG_JSON = path.join(STATE_DIR, "migration-log.json");
const DIFF_PATCH = path.join(STATE_DIR, "migration-diff.patch");
const VERIFY_JSON = path.join(STATE_DIR, "verification-report.json");
const VERIFY_MD = path.join(STATE_DIR, "verification-report.md");

const DRY_RUN = process.argv.includes("--dry-run") || process.argv.includes("-n");

/* ------------------------------------------------------------------ *
 * Classification
 * ------------------------------------------------------------------ */

const ROOT_DIRS = ["frontend", "gateway", "deploy", "backend", "scripts"];
const EXCLUDE_DIRS = new Set([
  "node_modules", "dist", "build-output", ".migrate", ".audit",
  ".git", "public", "legacy", "__pycache__", "coverage",
]);
const SCAN_EXTS = [".ts", ".tsx", ".js", ".jsx", ".json", ".sh", ".py", ".conf", ".yml", ".yaml", ".toml", ".md", ".html", ".css"];

// Files whose /rent occurrences are infra to rewrite (nginx etc.), handled by
// dedicated handlers in apply — reported separately from code MIGRATE edits.
const INFRA_FILES = [
  "gateway/nginx/nginx.conf",
  "gateway/nginx/routes/frontend.conf",
  "gateway/nginx/routes/redirect.conf",
];
const DELETED_FILES = ["gateway/nginx/routes/tenant-api.conf"];

// A MIGRATE edit is any of these literal /rent substrings. /rent at an exact
// boundary (e.g. "/rent ") as a bare base path is handled by dedicated handlers.
const MIGRATE_PATTERNS = [
  "/rent/",
  "/rent\"",
  "/rent'",
  "/rent`",
  "/rent)",
  "/rent]",
  "/rent}",
  "/rent,",
  "/rent ",
  "/rent\n",
  "/rent;",
  '/rent"}',
  "+ \"/rent\"",
  '"/rent"',
  "'/rent'",
  "|| \"/rent\"",
  "|| '/rent'",
];

/**
 * Decide classification for a matched line in a given file.
 * Returns { action: "MIGRATE"|"SKIP"|"INFRA"|"WARNING", note? }
 */
function classify(fileRel, line, lineText) {
  const low = lineText.toLowerCase();

  // Handled by dedicated handlers in apply() (nginx ingress edits).
  if (INFRA_FILES.includes(fileRel)) return { action: "INFRA" };

  // Comments / docs / historical references — not route construction.
  const isComment =
    lineText.trim().startsWith("//") ||
    lineText.trim().startsWith("#") ||
    lineText.trim().startsWith("*") ||
    lineText.trim().startsWith("/*") ||
    /^\s*\/\//.test(lineText) ||
    /\s\/\/\s/.test(lineText);
  const isDocFile = fileRel.endsWith(".md") || /(^|\/)(legacy|docs|doc)\//.test(fileRel);

  if (isComment) return { action: isDocFile ? "SKIP" : "MIGRATE", note: "inline comment" };

  // Config already handled by dedicated handlers.
  if (
    fileRel.includes("vite.config.ts") ||
    fileRel.endsWith("lib/runtime.ts") ||
    fileRel.endsWith("api/client.ts") ||
    fileRel.endsWith("lib/login-api.ts") ||
    fileRel.endsWith("lib/tenant-runtime.ts") ||
    fileRel.endsWith("hooks/useHealthStream.ts") ||
    fileRel.endsWith("hooks/useSync.ts") ||
    fileRel.endsWith("hooks/useAuthSync.ts") ||
    fileRel.endsWith("functions/_middleware.js") ||
    fileRel.endsWith("build.sh") ||
    fileRel.endsWith("shared/routes.json") ||
    fileRel.endsWith("_middleware.js")
  ) {
    return { action: "MIGRATE", note: "handled: dedicated transform" };
  }

  // Scripts that emit VITE_APP_BASE_PATH or assemble outputs.
  if (fileRel.endsWith(".py") || fileRel.endsWith(".sh") || fileRel.endsWith(".yml") || fileRel.endsWith(".yaml")) {
    return { action: "MIGRATE", note: "config/env emission" };
  }

  // Env files: VITE_APP_BASE_PATH=/rent -> remove/empty.
  if (/(^|\/)\.env(\..*)?$/.test(fileRel)) {
    if (/VITE_APP_BASE_PATH/.test(lineText)) return { action: "MIGRATE", note: "env base path" };
    return { action: "SKIP", note: "env file" };
  }

  // Everything else that is not a doc/comment and contains a real path token.
  if (isDocFile && !MIGRATE_PATTERNS.some((p) => lineText.includes(p))) {
    return { action: "SKIP", note: "documentation" };
  }

  return { action: "MIGRATE", note: "generic path" };
}

function resolveFiles() {
  const out = [];
  // Root-level files that participate in the migration (env sources, compose, deploy).
  const rootRelevant = [
    ".env.development", ".env.development.example",
    ".env.example", ".env.release", ".env.release.example",
    "compose.dev.yml", "compose.prod.yml", "deploy.py",
  ];
  for (const f of rootRelevant) {
    const abs = path.join(ROOT, f);
    if (fs.existsSync(abs)) out.push({ rel: f, abs });
  }
  for (const dir of ROOT_DIRS) {
    const absDir = path.join(ROOT, dir);
    if (!fs.existsSync(absDir)) continue;
    walk(absDir, (f) => {
      const abs = f;
      const rel = path.relative(ROOT, f).replace(/\\/g, "/");
      const parts = rel.split("/");
      if (parts.some((p) => EXCLUDE_DIRS.has(p))) return;
      const ext = path.extname(f).toLowerCase();
      if (!SCAN_EXTS.includes(ext)) return;
      out.push({ rel, abs });
    });
  }
  return out;
}

function walk(dir, cb) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(p, cb);
    else if (entry.isFile()) cb(p);
  }
}

/* ------------------------------------------------------------------ *
 * discover
 * ------------------------------------------------------------------ */

function discover() {
  fs.mkdirSync(STATE_DIR, { recursive: true });
  const files = resolveFiles();
  const occurrences = [];
  let totalMatches = 0;

  for (const { rel, abs } of files) {
    let text;
    try {
      text = fs.readFileSync(abs, "utf8");
    } catch {
      continue;
    }
    const lines = text.split("\n");
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const idxs = findAllRentIndex(line);
      for (const col of idxs) {
        totalMatches++;
        const { action, note } = classify(rel, i + 1, line);
        const match = line.slice(col, col + 5);
        occurrences.push({
          file: rel,
          line: i + 1,
          column: col + 1,
          match,
          snippet: line.trim().slice(0, 120),
          action,
          note: note || "",
        });
      }
    }
  }

  occurrences.sort((a, b) =>
    a.file === b.file ? a.line - b.line : a.file.localeCompare(b.file)
  );

  const byAction = occurrences.reduce((acc, o) => {
    acc[o.action] = (acc[o.action] || 0) + 1;
    return acc;
  }, {});
  const migrate = occurrences.filter((o) => o.action === "MIGRATE");
  const infras = occurrences.filter((o) => o.action === "INFRA");
  const warnings = occurrences.filter((o) => o.action === "WARNING");

  fs.writeFileSync(PLAN_JSON, JSON.stringify({ generated: new Date().toISOString(), totalMatches, byAction, occurrences }, null, 2));

  const md = [];
  md.push("# Route-Base Migration — Discover Report");
  md.push("");
  md.push(`Generated: ${new Date().toISOString()}`);
  md.push("");
  md.push(`**Total /rent matches:** ${totalMatches}`);
  md.push("");
  md.push("## Classification summary");
  md.push("");
  md.push(`| Action | Count |`);
  md.push(`|--------|-------|`);
  for (const [k, v] of Object.entries(byAction)) md.push(`| ${k} | ${v} |`);
  md.push("");
  md.push(`**Deleted files:** ${DELETED_FILES.join(", ")}`);
  md.push("");
  md.push("## MIGRATE occurrences (code/config to drop /rent)");
  md.push("");
  if (migrate.length) {
    md.push("| File | Line | Match | Snippet | Note |");
    md.push("|------|------|-------|---------|------|");
    for (const o of migrate) md.push(`| ${o.file} | ${o.line} | ${o.match} | \`${o.snippet}\` | ${o.note} |`);
  } else {
    md.push("_None._");
  }
  md.push("");
  md.push(`## WARNING occurrences (${warnings.length})`);
  md.push("");
  for (const o of warnings) md.push(`- ${o.file}:${o.line} \`${o.snippet}\``);
  fs.writeFileSync(PLAN_MD, md.join("\n"));

  console.log(`discover: ${totalMatches} matches, ${Object.entries(byAction).map(([k, v]) => `${k}=${v}`).join(" ")}`);
  console.log(`  plan -> ${path.relative(ROOT, PLAN_JSON)}`);
  console.log(`  report -> ${path.relative(ROOT, PLAN_MD)}`);
  if (warnings.length) console.log(`  WARNING: ${warnings.length} manual-review item(s)`);
  return { totalMatches, migrateCount: migrate.length, infras: infras.length, warnings };
}

// Universal /rent path-token matcher.
//   - Lookahead: /rent must be followed by a boundary (quote/brace/separator/EOL)
//     so we never match "renter", "rent/" inside a longer identifier.
//   - Negative lookbehind: /rent must NOT be preceded by an alphanumeric, so
//     filesystem paths (/home/vega/rent/...) and domain hosts
//     (rent.vijaykrsha.online) are never treated as URL route bases.
const RENT_PATH_RE = /(?<![A-Za-z0-9])\/rent(?=[/"'`)\],} \n;]|$)/g;

function findAllRentIndex(line) {
  const out = [];
  let m;
  while ((m = RENT_PATH_RE.exec(line)) !== null) {
    out.push(m.index);
  }
  return out;
}

/* ------------------------------------------------------------------ *
 * apply
 * ------------------------------------------------------------------ */

const ROUTES_JSON_FILES = [
  "frontend/shared/routes.json",
  "backend/shared/routes.json",
];

function transformFile(rel) {
  const relNorm = rel.replace(/\\/g, "/");
  const abs = path.join(ROOT, rel);
  const orig = fs.readFileSync(abs, "utf8");
  let next = orig;
  let changed = false;
  let hasDedicatedHandler = false;
  const edits = [];

  const apply = (oldStr, newStr, label) => {
    if (next.includes(oldStr)) {
      const before = next;
      next = next.split(oldStr).join(newStr);
      if (before !== next) {
        changed = true;
        edits.push({ label, oldStr, newStr });
      }
    }
  };

  // ---- Vite configs ----
  if (rel.endsWith("vite.config.ts")) {
    hasDedicatedHandler = true;
    const baseMap = {
      "tenant-app/vite.config.ts": ["'/rent/t/'", "'/t/'"],
      "admin-app/vite.config.ts": [`"/rent/admin/"`, `"/admin/"`],
      "landlord-app/vite.config.ts": ["'/rent/landlord/'", "'/landlord/'"],
      "landing-app/vite.config.ts": [`"/rent/"`, `"/"`],
    };
    if (baseMap[relNorm]) apply(baseMap[relNorm][0], baseMap[relNorm][1], "vite base");
  }

  // ---- admin runtime ----
  if (rel.endsWith("admin-app/src/lib/runtime.ts")) {
    hasDedicatedHandler = true;
    apply(`APP_BASE = "/rent/admin"`, `APP_BASE = "/admin"`, "admin APP_BASE");
    apply(`getApiBaseUrl() + "/rent/admin/api"`, `getApiBaseUrl() + "/admin/api"`, "admin API_BASE");
  }

  // ---- landlord runtime ----
  if (rel.endsWith("landlord-app/src/lib/runtime.ts")) {
    hasDedicatedHandler = true;
    apply(`'/rent/landlord'`, `'/landlord'`, "landlord APP_BASE fallback");
    apply(`getApiBaseUrl() + "/rent"`, `getApiBaseUrl()`, "landlord API_BASE");
  }

  // ---- admin client ----
  if (rel.endsWith("admin-app/src/api/client.ts")) {
    hasDedicatedHandler = true;
    apply(`API_PREFIX = "/rent/admin/api"`, `API_PREFIX = "/admin/api"`, "admin API_PREFIX");
  }

  // ---- tenant login-api ----
  if (rel.endsWith("tenant-app/src/lib/login-api.ts")) {
    hasDedicatedHandler = true;
    const before = next;
    next = next.replace(/\/rent\/tenant\/api\//g, "/tenant/api/");
    if (before !== next) { changed = true; edits.push({ label: "tenant login-api /rent/tenant/api", oldStr: "/rent/tenant/api/", newStr: "/tenant/api/" }); }
  }

  // ---- tenant runtime ----
  if (rel.endsWith("tenant-app/src/lib/tenant-runtime.ts")) {
    hasDedicatedHandler = true;
    apply(`VITE_APP_BASE_PATH || "/rent"`, `VITE_APP_BASE_PATH || ""`, "tenant runtime APP_BASE");
  }

  // ---- WebSocket hooks ----
  if (/hooks\/(useHealthStream|useSync|useAuthSync)\.ts$/.test(rel)) {
    hasDedicatedHandler = true;
    apply(`/rent/ws/`, `/ws/`, "websocket base");
  }

  // ---- _middleware ----
  if (rel.endsWith("functions/_middleware.js") || /_middleware\.js$/.test(rel)) {
    hasDedicatedHandler = true;
    next = middlewareTransform(next);
    changed = next !== orig;
    if (changed) edits.push({ label: "_middleware.js", oldStr: "<middleware body>", newStr: "<rewritten>" });
  }

  // ---- build.sh ----
  if (rel.endsWith("build.sh")) {
    hasDedicatedHandler = true;
    next = buildShTransform(next);
    changed = next !== orig;
    if (changed) edits.push({ label: "build.sh", oldStr: "<assembly body>", newStr: "<rewritten>" });
  }

  // ---- shared routes.json ----
  if (ROUTES_JSON_FILES.includes(relNorm)) {
    hasDedicatedHandler = true;
    apply(`"basePath": "/rent"`, `"basePath": "/"`, "routes.json basePath");
  }

  // ---- env files ----
  if (/(^|\/)\.env(\..*)?$/.test(rel)) {
    hasDedicatedHandler = true;
    apply(`VITE_APP_BASE_PATH=/rent`, `VITE_APP_BASE_PATH=`, "env VITE_APP_BASE_PATH");
  }

  // ---- deploy.py / compose.yml ----
  if (rel.endsWith("deploy.py")) {
    hasDedicatedHandler = true;
    apply(`env_map.get("VITE_APP_BASE_PATH", "/rent")`, `env_map.get("VITE_APP_BASE_PATH", "")`, "deploy.py base default");
  }
  if (rel.endsWith("compose.dev.yml")) {
    hasDedicatedHandler = true;
    apply(`VITE_APP_BASE_PATH=/rent`, `VITE_APP_BASE_PATH=`, "compose env base");
  }

  // ---- routes_manifest.py: base path derives from shared routes.json ----
  if (relNorm.endsWith("core/routes_manifest.py")) {
    hasDedicatedHandler = true;
    apply(`BASEPATH = "/rent"`, `BASEPATH = "/"`, "routes_manifest BASEPATH");
  }

  // ---- pages/landing.py: dev landing redirect now that landing lives at / ----
  if (relNorm.endsWith("pages/landing.py")) {
    hasDedicatedHandler = true;
    next = landingPyTransform(next);
    changed = next !== orig;
    if (changed) edits.push({ label: "landing.py serve-at-root", oldStr: "<redirect body>", newStr: "<served index>" });
  }

  // ---- pages/frontend.py: remove the bare /rent root-redirect (the bare path
  // no longer exists after complete drop; a "/rent" -> "/" drop yields an
  // invalid empty route "@router.get('')"). The rest is handled by generic drop.
  if (relNorm.endsWith("pages/frontend.py")) {
    hasDedicatedHandler = true;
    next = frontendPyTransform(next);
    changed = next !== orig;
    if (changed) edits.push({ label: "frontend.py remove bare /rent redirect", oldStr: "<bare /rent block>", newStr: "<removed>" });
  }

  // ---- nginx infra: dedicated handlers (generic drop produces invalid
  // "location = {" and self-redirects on these files). ----
  if (relNorm === "gateway/nginx/nginx.conf") {
    hasDedicatedHandler = true;
    next = nginxConfTransform(next);
    changed = next !== orig;
    if (changed) edits.push({ label: "nginx.conf infra", oldStr: "<root block + include>", newStr: "<rewritten>" });
  } else if (relNorm === "gateway/nginx/routes/frontend.conf") {
    hasDedicatedHandler = true;
    next = frontendConfTransform(next);
    changed = next !== orig;
    if (changed) edits.push({ label: "frontend.conf infra", oldStr: "</rent blocks>", newStr: "<rewritten>" });
  } else if (relNorm === "gateway/nginx/routes/redirect.conf") {
    hasDedicatedHandler = true;
    next = redirectConfTransform(next);
    changed = next !== orig;
    if (changed) edits.push({ label: "redirect.conf infra", oldStr: "</rent redirects>", newStr: "<root deep-link only>" });
  }

  // ---- generic MIGRATE drop (code, scripts, conf, docs) ----
  // Runs on every transformable file, including after dedicated handlers, so
  // any residual /rent base-path occurrences are dropped (complete drop). The
  // lookbehind in RENT_PATH_RE guards filesystem/domain false positives.
  if (isTransformable(rel)) {
    const re = new RegExp(RENT_PATH_RE.source, "g");
    const candidate = next.replace(re, "");
    if (candidate !== next) {
      next = candidate;
      changed = true;
      edits.push({ label: "generic /rent drop", oldStr: "/rent", newStr: "" });
    }
  }

  return { orig, next, changed, edits };
}

function isCodeFile(rel) {
  return /\.(tsx?|jsx?|json|py)$/.test(rel);
}

// Files that get the guarded generic /rent path drop.
function isTransformable(rel) {
  return /\.(tsx?|jsx?|json|py|sh|conf|yml|yaml|md|html|css)$/.test(rel);
}

// pages/landing.py: after the /rent/ drop the landing app serves at / directly,
// so the old "/ -> redirect to /rent/" becomes a self-redirect. Replace it with
// FileResponse of the landing index, mirroring app/pages/frontend.py.
function landingPyTransform(src) {
  let s = src;
  // Refresh the stale docstring (mentions the retired /rent/ tree). CRLF-tolerant.
  s = s.replace(
    /Redirects to the canonical landing app at \/rent\/ \(mirrors the prod\r?\n_redirects rule "\/ \/rent\/ 301"\)\. The \/rent\/ tree is served by\r?\napp\/pages\/frontend\.py in dev and by the frontend container in prod\./,
    "Serves the landing app directly at the canonical root /. The legacy\nbase-path tree was migrated to the root and is no longer used."
  );
  // After complete drop the bare / could self-redirect: serve the landing SPA
  // directly instead of redirecting / -> /. CRLF-tolerant.
  s = s.replace(
    /    """Redirect the bare domain to the canonical landing app at \/rent\/\."""\r?\n    check_api_host\(request\)\r?\n    return RedirectResponse\(url="\/rent\/", status_code=301\)/,
    '    """Serve the landing app at the canonical root /."""\n    check_api_host(request)\n    return FileResponse("frontend/landing-app/dist/index.html")'
  );
  return s;
}

// app/pages/frontend.py: after complete drop the bare /rent path no longer
// exists, so the rent_root_redirect handler (and its @router.get("/rent") with
// no trailing slash) must be deleted — a generic "/rent" -> "" drop would
// otherwise emit the invalid FastAPI route "@router.get('')". The remaining
// "/rent/"-prefixes are dropped by the generic transform. Tolerant of CRLF.
function frontendPyTransform(src) {
  let s = src;
  s = s.replace(
    /@router\.get\("\/rent", include_in_schema=False\)\r?\nasync def rent_root_redirect\(request: Request\):\r?\n    check_api_host\(request\)\r?\n    return RedirectResponse\(url="\/rent\/", status_code=301\)\r?\n\r?\n/,
    ""
  );
  return s;
}

// gateway/nginx/nginx.conf:
//  - remove the include of the deleted tenant-api.conf
//  - frontend root block: serve index.html instead of the now-broken self
//    redirect "return 301 /rent/;" (generic drop would yield "return 301 /;" —
//    a self-redirect loop). The API-host bare-domain block keeps redirecting to
//    the public frontend root (no /rent) via the generic drop. CRLF-tolerant.
function nginxConfTransform(src) {
  let s = src;
  s = s.replace(/[ \t]*include \/etc\/nginx\/routes\/tenant-api\.conf;\r?\n/, "");
  s = s.replace(
    /        location = \/ \{\r?\n            return 301 \/rent\/;\r?\n        \}/,
    `        location = / {
            try_files /index.html =404;
        }`
  );
  return s;
}

// gateway/nginx/routes/frontend.conf:
//  - delete the bare "location = /rent { return 301 /rent/; }" block (bare
//    /rent no longer exists; generic drop would emit invalid "location = {")
//  - delete the /rent-prefixed tenant deep-link block (originally
//    ^/rent/{uuid}/t/...); after the /rent drop it becomes an identical
//    duplicate of the root-level deep-link block below it — keep one copy.
//  The /rent/xxx SPA-fallback prefixes and try_files paths drop cleanly via
//  the generic transform. CRLF-tolerant.
function frontendConfTransform(src) {
  let s = src;
  s = s.replace(
    /location = \/rent \{\r?\n    return 301 \/rent\/;\r?\n\}\r?\n\r?\n/,
    ""
  );
  s = s.replace(
    /# \/rent\/\{uuid\}\/t\/\{propertyId\}\/\{tenantId\}\/\{viewToken\} deep links \u2192 tenant SPA\r?\nlocation ~ \^\/rent\/\[\^\/\]\+\/t\/\[0-9\]\+\/\[0-9\]\+\/\[\^\/\]\+\(\/\.\*\)\?\$ \{\r?\n    try_files \/rent\/t\/index\.html =404;\r?\n\}\r?\n\r?\n/,
    ""
  );
  // Refresh the root-level deep-link comment left dangling by the /rent drop.
  // Matches the pre-generic-drop comment (which still contains "/rent").
  s = s.replace(
    /# Root-level tenant portal deep links[\s\S]*?tenant SPA entry\.\n(?=location ~)/,
    `# Root-level tenant portal deep links (legacy share links without the
# base-path prefix) -> tenant SPA entry.
`
  );
  return s;
}

// gateway/nginx/routes/redirect.conf: complete drop removes the API-host
// redirects for /rent and /rent/... (those paths now 404 everywhere). Only the
// root-level tenant portal deep-link block remains, forwarding to the public
// frontend with an empty re-add base (no /rent). CRLF-tolerant.
function redirectConfTransform(src) {
  let s = src;
  s = s.replace(
    /location = \/rent \{\r?\n    return 301 https:\/\/rent\.vijaykrsha\.online\/rent\/;\r?\n\}\r?\n\r?\nlocation \/rent\/ \{\r?\n    return 301 https:\/\/rent\.vijaykrsha\.online\$request_uri;\r?\n\}\r?\n\r?\n/,
    ""
  );
  // Root-level tenant deep link: re-add base is now empty (no /rent). The
  // generic RENT_PATH_RE cannot drop "/rent$" because the trailing "$" is not a
  // boundary character, so handle it explicitly.
  s = s.replace(
    /return 301 https:\/\/rent\.vijaykrsha\.online\/rent\$request_uri;/,
    "return 301 https://rent.vijaykrsha.online$request_uri;"
  );
  // Refresh the stale header comment (tenant-api.conf is deleted and /rent
  // redirects are gone; only root-level tenant deep links remain).
  s = s.replace(
    /# Frontend routes are NOT served on the API host\.[\s\S]*?reach these redirects\.\r?\n\r?\n/,
    `# Frontend routes are NOT served on the API host. The public frontend lives
# on rent.vijaykrsha.online (Cloudflare Pages). Root-level tenant portal deep
# links (legacy share links) forward to the same page on the public frontend.
# The ^~ backend locations in api.conf are evaluated first, so only true
# tenant deep-link page paths reach this redirect.

`
  );
  return s;
}

function middlewareTransform(src) {
  let s = src;

  // SPA_INDEXES prefixes -> root paths
  s = s.replace(`{ prefix: "/rent/admin/", index: "/rent/admin/index.html" }`, `{ prefix: "/admin/", index: "/admin/index.html" }`);
  s = s.replace(`{ prefix: "/rent/landlord/", index: "/rent/landlord/index.html" }`, `{ prefix: "/landlord/", index: "/landlord/index.html" }`);
  s = s.replace(`{ prefix: "/rent/tenant/", index: "/rent/t/index.html" }`, `{ prefix: "/t/", index: "/t/index.html" }`);
  s = s.replace(`{ prefix: "/rent/t/", index: "/rent/t/index.html" }`, `{ prefix: "/t/", index: "/t/index.html" }`);
  s = s.replace(`{ prefix: "/rent/", index: "/rent/index.html" }`, `{ prefix: "/", index: "/index.html" }`);

  // Remove / -> /rent/ 301 redirect block
  s = s.replace(
    /  if \(path === "\/" \|\| path === ""\) \{\n[\s\S]*?  \}\n\n/,
    ""
  );

  // Tenant deep-link comment + regex + handler: canonical base is / (no /rent)
  s = s.replace(
    /  \/\/ Tenant portal deep links \(\/rent\/\{landlordUuid\}\/t\/\{propertyId\}\/\{tenantId\}\/\{viewToken\}\) —\n  \/\/ serve the tenant SPA from Pages\. Its router \(basename \/rent\) renders the\n  \/\/ portal from the URL params, so deep links work without touching the API host\.\n  const tenantLinkRe =\n    \/^\\\/rent\\\/\[0-9a-fA-F\]\{8\}-\[0-9a-fA-F\]\{4\}-\[0-9a-fA-F\]\{4\}-\[0-9a-fA-F\]\{4\}-\[0-9a-fA-F\]\{12\}\\\/t\\\/\[0-9\]\+\\\/\[0-9\]\+\\\/\[0-9a-zA-Z-\]\+\(\?:\\\/\.\*\)\?\$\ \/;\n  if \(tenantLinkRe\.test\(path\)\) \{\n    const indexUrl = new URL\("\/rent\/t\/index\.html", url\);\n    const indexResponse = await context\.env\.ASSETS\.fetch\(indexUrl\);\n    if \(indexResponse\.ok\) \{\n      return new Response\(indexResponse\.body, \{\n        status: 200,\n        headers: indexResponse\.headers,\n      \}\);\n    \}\n  \}/,
    `  // Tenant portal deep links (/{landlordUuid}/t/{propertyId}/{tenantId}/{viewToken}) —
  // serve the tenant SPA from Pages. Its router (basename /) renders the
  // portal from the URL params, so deep links work without touching the API host.
  const tenantLinkRe =
    /^\\/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\\/t\\/[0-9]+\\/[0-9]+\\/[0-9a-zA-Z-]+(?:\\/.*)?$/;
  if (tenantLinkRe.test(path)) {
    const indexUrl = new URL("/t/index.html", url);
    const indexResponse = await context.env.ASSETS.fetch(indexUrl);
    if (indexResponse.ok) {
      return new Response(indexResponse.body, {
        status: 200,
        headers: indexResponse.headers,
      });
    }
  }`
  );

  return s;
}

function buildShTransform(src) {
  let s = src;

  // Assembly: root build-output without /rent wrapper
  s = s.replace(
    /rm -rf build-output\nmkdir -p build-output\/rent\n\ncp -r landing-app\/dist\/\* build-output\/rent\/\nmkdir -p build-output\/rent\/admin\ncp -r admin-app\/dist\/\* build-output\/rent\/admin\/\nmkdir -p build-output\/rent\/landlord\ncp -r landlord-app\/dist\/\* build-output\/rent\/landlord\/\nmkdir -p build-output\/rent\/t\ncp -r tenant-app\/dist\/\* build-output\/rent\/t\//,
    `rm -rf build-output
mkdir -p build-output

# Landing app -> root
cp -r landing-app/dist/* build-output/
# Admin app -> /admin
mkdir -p build-output/admin
cp -r admin-app/dist/* build-output/admin/
# Landlord app -> /landlord
mkdir -p build-output/landlord
cp -r landlord-app/dist/* build-output/landlord/
# Tenant app trailing base -> /t (assets); deep links served by _middleware
mkdir -p build-output/t
cp -r tenant-app/dist/* build-output/t/`
  );

  // _headers: drop /rent prefixes
  s = s.replace(/\/rent\/assets\*\//g, `/assets/*`);
  s = s.replace(/\/rent\/\*\.js/g, `/*.js`);
  s = s.replace(/\/rent\/\*\.css/g, `/*.css`);
  s = s.replace(/\/rent\/\*\.html/g, `/*.html`);

  // _redirects: landing is served at / directly (complete drop). Root redirect
  // removed; a minimal explicit 404/SPA fallback is unnecessary because the
  // Pages _routes.json + _middleware handle SPA routing.
  s = s.replace(
    /cat > build-output\/_redirects << 'EOF'\n# Root redirect: bare domain -> landing app\n\/ \/rent\/ 301\nEOF/,
    `cat > build-output/_redirects << 'EOF'
# Complete drop: landing app is served at / directly. No root redirect.
EOF`
  );

  // Write _routes.json to build-output root just before "Build complete".
  const routesJson = JSON.stringify(
    {
      version: 1,
      include: ["/*"],
      exclude: [
        "/assets/*",
        "/admin/assets/*",
        "/landlord/assets/*",
        "/t/assets/*",
        "/*.js",
        "/*.css",
        "/*.png",
        "/*.jpg",
        "/*.jpeg",
        "/*.gif",
        "/*.svg",
        "/*.ico",
        "/*.woff2",
        "/*.woff",
        "/*.eot",
        "/*.ttf",
        "/favicon.ico",
      ],
    },
    null,
    2
  );
  const routeInsert = `
cat > build-output/_routes.json << 'EOF'
${routesJson}
EOF
`;
  s = s.replace(/echo ""\necho "=== Build complete ==="/, `${routeInsert}\necho ""\necho "=== Build complete ==="/`);

  // Final listing path
  s = s.replace(/ls -la build-output\/rent\//, "ls -la build-output/");

  return s;
}

function readDiff(orig, next, rel) {
  const a = orig.split("\n");
  const b = next.split("\n");
  const out = [`--- a/${rel}`, `+++ b/${rel}`];
  let i = 0, j = 0, hunk = [], hunkStart = 1, context = 0;
  const flush = () => {
    if (!hunk.length) return;
    out.push(`@@ -${hunkStart},${hunk.filter((l) => l[0] === "-").length} +${hunkStart},${hunk.filter((l) => l[0] === "+").length} @@`);
    for (const line of hunk) out.push(line);
    hunk = [];
  };
  while (i < a.length || j < b.length) {
    if (i < a.length && j < b.length && a[i] === b[j]) {
      hunkStart = i + 1;
      i++; j++;
      continue;
    }
    if (hunk.length === 0) context = 0;
    if (i < a.length) { hunk.push("-" + a[i]); i++; context++; }
    if (j < b.length) { hunk.push("+" + b[j]); j++; context++; }
    if (hunk.length >= 3 || (i >= a.length && j >= b.length)) flush();
  }
  flush();
  return out;
}

function applyMigration() {
  fs.mkdirSync(STATE_DIR, { recursive: true });

  if (!fs.existsSync(PLAN_JSON)) {
    console.log("No migration-plan.json found — run `discover` first.");
    process.exit(1);
  }

  const plan = JSON.parse(fs.readFileSync(PLAN_JSON, "utf8"));
  const files = resolveFiles().map((f) => f.rel);

  const log = { dryRun: DRY_RUN, started: new Date().toISOString(), files: [], deleted: [], errors: [] };
  const diffs = [];

  for (const f of files) {
    if (DELETED_FILES.includes(f)) continue;
    const { changed, edits, orig, next } = transformFile(f);
    if (!changed) continue;
    if (DRY_RUN) {
      diffs.push(...readDiff(orig, next, f));
      log.files.push({ file: f, edits, applied: false });
      continue;
    }
    const bak = f + ".bak";
    if (!fs.existsSync(bak)) fs.copyFileSync(path.join(ROOT, f), path.join(ROOT, bak));
    fs.writeFileSync(path.join(ROOT, f), next);
    diffs.push(...readDiff(orig, next, f));
    log.files.push({ file: f, edits, applied: true, backup: path.relative(ROOT, bak) });
  }

  for (const f of DELETED_FILES) {
    const abs = path.join(ROOT, f);
    if (!fs.existsSync(abs)) continue;
    const bak = f + ".removed.bak";
    if (!DRY_RUN) {
      if (!fs.existsSync(path.join(ROOT, bak))) fs.copyFileSync(abs, path.join(ROOT, bak));
    }
    log.deleted.push({ file: f, dry: DRY_RUN });
    if (!DRY_RUN) fs.rmSync(abs);
  }

  log.finished = new Date().toISOString();
  fs.writeFileSync(LOG_JSON, JSON.stringify(log, null, 2));
  fs.writeFileSync(DIFF_PATCH, diffs.join("\n"));

  const verb = DRY_RUN ? "DRY-RUN (no files written)" : "applied";
  console.log(`apply: ${verb}`);
  console.log(`  edited files: ${log.files.filter((x) => !x.applied || log.dryRun).length}`);
  for (const f of log.files) console.log(`    ${f.file}${f.applied ? "" : " [dry]"}`);
  for (const d of log.deleted) console.log(`  DELETED ${d.file}${d.dry ? " [dry]" : ""}`);
  console.log(`  diff -> ${path.relative(ROOT, DIFF_PATCH)}`);
  if (log.errors.length) console.log(`  ERRORS: ${log.errors.join("; ")}`);
}

/* ------------------------------------------------------------------ *
 * verify
 * ------------------------------------------------------------------ */

function verify() {
  fs.mkdirSync(STATE_DIR, { recursive: true });
  const results = [];
  let remainingMigrate = 0;

  const files = resolveFiles();
  for (const { rel } of files) {
    const abs = path.join(ROOT, rel);
    const text = fs.readFileSync(abs, "utf8");
    const lines = text.split("\n");
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const cls = classify(rel, i + 1, line);
      if (cls.action === "MIGRATE" && findAllRentIndex(line).length) {
        remainingMigrate++;
      }
    }
  }

  results.push({
    check: "No MIGRATE /rent occurrences remain in code",
    pass: remainingMigrate === 0,
    detail: remainingMigrate === 0 ? "clean" : `${remainingMigrate} remaining`,
  });

  const nginxRaw = fs.existsSync(path.join(ROOT, "gateway/nginx"))
    ? readTree(path.join(ROOT, "gateway/nginx"))
    : "";
  results.push({
    check: "nginx: tenant-api.conf removed from includes",
    pass: !nginxRaw.includes("tenant-api.conf"),
    detail: "tenant-api.conf not referenced",
  });

  const frontendConf = fs.readFileSync(path.join(ROOT, "gateway/nginx/routes/frontend.conf"), "utf8");
  results.push({
    check: "frontend.conf: no /rent locations",
    pass: !/\/rent/.test(frontendConf),
    detail: "clean",
  });

  const redirectConf = fs.readFileSync(path.join(ROOT, "gateway/nginx/routes/redirect.conf"), "utf8");
  results.push({
    check: "redirect.conf: no /rent base readd",
    pass: !/rent\.vijaykrsha\.online\/rent/.test(redirectConf) && !redirectConf.includes("/rent/"),
    detail: "clean",
  });

  const buildSh = fs.readFileSync(path.join(ROOT, "frontend/build.sh"), "utf8");
  results.push({
    check: "build.sh: no /rent assembly or headers",
    pass: !/\/rent/.test(buildSh),
    detail: "clean",
  });

  const vcs = ["vite.config.ts", "runtime.ts", "client.ts", "login-api.ts", "tenant-runtime.ts"];
  const remainingVcs = [];
  for (const { rel } of files) {
    if (!vcs.some((v) => rel.endsWith(v))) continue;
    const text = fs.readFileSync(path.join(ROOT, rel), "utf8");
    if (text.includes("/rent/")) remainingVcs.push(rel);
  }
  results.push({
    check: "Vite/runtime/client configs free of /rent/",
    pass: remainingVcs.length === 0,
    detail: remainingVcs.length ? remainingVcs.join(", ") : "clean",
  });

  const routesJsonOk = ROUTES_JSON_FILES.every((f) => {
    const t = fs.readFileSync(path.join(ROOT, f), "utf8");
    return /"basePath": "\/"/.test(t);
  });
  results.push({
    check: "routes.json basePath = /",
    pass: routesJsonOk,
    detail: routesJsonOk ? "both set to /" : "route json basePath not migrated",
  });

  const allPass = results.every((r) => r.pass);
  const report = { generated: new Date().toISOString(), allPass, results };

  fs.writeFileSync(VERIFY_JSON, JSON.stringify(report, null, 2));
  const md = [];
  md.push("# Route-Base Migration — Verification Report");
  md.push("");
  md.push(`Generated: ${new Date().toISOString()}`);
  md.push("");
  md.push(`## Result: ${allPass ? "PASS" : "FAIL"}`);
  md.push("");
  md.push("| Check | Pass | Detail |");
  md.push("|-------|------|--------|");
  for (const r of results) md.push(`| ${r.check} | ${r.pass ? "✅" : "❌"} | ${r.detail} |`);
  fs.writeFileSync(VERIFY_MD, md.join("\n"));

  console.log(`verify: ${allPass ? "PASS" : "FAIL"}`);
  for (const r of results) console.log(`  [${r.pass ? "PASS" : "FAIL"}] ${r.check} — ${r.detail}`);
  console.log(`  -> ${path.relative(ROOT, VERIFY_MD)}`);
  return allPass;
}

function readTree(dir) {
  const parts = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isFile()) {
      if (entry.name.endsWith(".bak") || entry.name.endsWith(".removed.bak")) continue;
      parts.push(fs.readFileSync(p, "utf8"));
    } else if (entry.isDirectory()) parts.push(readTree(p));
  }
  return parts.join("\n");
}

/* ------------------------------------------------------------------ *
 * main
 * ------------------------------------------------------------------ */

const [cmd] = process.argv.slice(2);

if (!cmd || !["discover", "apply", "verify"].includes(cmd)) {
  console.log(`Usage:
  node scripts/route-migrate.mjs discover
  node scripts/route-migrate.mjs apply [--dry-run|-n]
  node scripts/route-migrate.mjs verify`);
  process.exit(1);
}

try {
  let ok = true;
  if (cmd === "discover") discover();
  else if (cmd === "apply") applyMigration();
  else if (cmd === "verify") ok = verify();
  if (!ok) process.exitCode = 1;
} catch (err) {
  console.error("route-migrate error:", err.message);
  process.exitCode = 1;
}
