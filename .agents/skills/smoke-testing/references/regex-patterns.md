# Regex pattern library

These are **discovery** aids, not a full semantic analyzer — pair them with actually reading the matched file, running the project's real build/test commands, and making real HTTP calls. Never treat a regex match alone as proof something works; it only tells you where to look. The machine-readable versions live in `assets/patterns/{backend,frontend,database,configuration}.json` (flat regex lookups) and `assets/patterns/errors.json` (diagnosis records — see below), and get copied into the project's `.smoke-test/patterns/` on first run so they can be edited per-project without touching this skill. `assets/scripts/health_probe.sh` and `assets/scripts/compute_fingerprint.py` are the executable counterparts — read-only helpers for the health-check and fingerprinting steps described in `references/discovery.md`.

## Backend framework discovery

| Framework | Pattern |
|---|---|
| FastAPI | `(?i)\b(FastAPI|APIRouter|uvicorn)\b` |
| Flask | `(?i)\b(Flask|Blueprint)\b` |
| Django | `(?i)\b(Django|urlpatterns|APIView)\b` |
| Spring (Java) | `(?i)\b(SpringBootApplication|RestController|RequestMapping|SpringApplication)\b` |
| Express (Node) | `(?i)\b(express\(|Router\(|app\.(get|post|put|patch|delete)\()\b` |

## Database technology discovery

Machine-readable version: `assets/patterns/database.json`. Fills a gap the original pattern set didn't cover — detecting *what* the backend talks to, not just the backend framework itself.

| Technology | Pattern |
|---|---|
| PostgreSQL | `(?i)\b(psycopg2|asyncpg|pg8000|postgresql://|postgres://)\b` |
| MySQL | `(?i)\b(pymysql|mysqlclient|mysql2|mysql://)\b` |
| SQLite | `(?i)\b(sqlite3|sqlite://)\b` |
| MongoDB | `(?i)\b(pymongo|mongoose|mongodb(\+srv)?://)\b` |
| Redis | `(?i)\b(redis-py|ioredis|redis://)\b` |
| CockroachDB | `(?i)\b(cockroach|cockroachdb://)\b` |
| ORM signal (SQLAlchemy/Prisma/Mongoose/Hibernate) | see `database.json` — used to confirm the connection layer, not the DB engine itself |

## Frontend framework discovery

| Framework | Pattern |
|---|---|
| React | `(?i)\b(react|createRoot|ReactDOM|jsx|tsx)\b` |
| Vite | `(?i)\b(vite|vite\.config\.(js|ts|mjs))\b` |
| Next.js | `(?i)\b(next|next\.config\.(js|ts|mjs))\b` |
| Vue | `(?i)\b(vue|createApp|\.vue)\b` |
| Angular | `(?i)\b(@angular/core|ngOnInit|angular\.json)\b` |

## Backend API route discovery

| Framework | Pattern |
|---|---|
| Python (FastAPI/Flask) | `(?i)@\s*(app|router)\.(get|post|put|patch|delete)\s*\(` |
| Java (Spring) | `(?i)@(GetMapping|PostMapping|PutMapping|PatchMapping|DeleteMapping|RequestMapping)` |
| Express | `(?i)\b(app|router)\.(get|post|put|patch|delete)\s*\(` |

## Frontend route discovery

| Style | Pattern |
|---|---|
| React Router JSX | `(?i)<Route\b[^>]*\bpath\s*=\s*["'][^"']+["']` |
| React Router object config | `(?i)\bpath\s*:\s*["'][^"']+["']` |
| Next.js (filesystem, no regex needed) | Glob `app/**/page.*` or `pages/**/*.*` |

## Frontend→backend API call discovery

| Language | Pattern |
|---|---|
| JS/TS | `(?i)\b(fetch|axios\.(get|post|put|patch|delete)|api\.(get|post|put|patch|delete))\s*\(` |
| Python client | `(?i)\b(requests\.(get|post|put|patch|delete)|httpx\.(get|post|put|patch|delete))\s*\(` |

Use this to build the dependency map: match a frontend call's path string against a discovered backend route to link them (see `references/discovery.md` and `references/state-management.md`).

## Error detection (logs / output) — diagnosis + candidate fixes

The human-readable table below is a quick reference; the actual working library is `assets/patterns/errors.json`, and it is **not** a flat regex lookup like `backend.json`/`frontend.json`/`configuration.json`/`database.json`. Each entry there is a full diagnosis record — `id`, `category` (using the same vocabulary as `references/reporting.md` §Failure classification), `severity`, `regex`, `signal` (what the match means), `likelyCauses`, and `candidateFixes` (each with a one-line trade-off, and a note on whether it's a Zone A or Zone B change per `references/rules.md` §2). This is what `references/change-control.md` reads from to build the root-cause chain and the proposed-change wording — matching a failure against `errors.json` is how you get from raw evidence to a *specific, defensible* fix proposal instead of a guess.

| Target | Pattern (see errors.json id) |
|---|---|
| Generic log severity | `(?i)\b(error|exception|traceback|fatal|panic|critical)\b` |
| HTTP server errors | `\b5\d{2}\b` — matched more specifically per-status in errors.json (`http-500`, etc.) |
| HTTP client errors | `\b4\d{2}\b` — matched more specifically per-status (`http-401-unexpected`, `http-403-unexpected`, `http-404-on-critical-route`) |
| Python traceback | `errors.json: python-traceback` |
| Java exception | `errors.json: java-nullpointer` (and generic `Caused by:` chains) |
| JS runtime error | covered by `errors.json: react-error-boundary`, `build-failure` |
| React error | `errors.json: react-error-boundary` |
| Database | `errors.json: db-auth-failed`, `db-conn-refused`, `db-relation-missing` |
| Auth/authorization | `errors.json: http-401-unexpected`, `http-403-unexpected`, `jwt-invalid` |
| Build | `errors.json: build-failure` |
| Environment | `errors.json: port-in-use` |
| Network | `errors.json: cors-blocked`, `timeout`, `rate-limited` |

## Network failure detection (browser/API logs)

`(?i)\b(CORS|ERR_CONNECTION_REFUSED|ERR_CONNECTION_RESET|ERR_FAILED|Network Error|ECONNREFUSED|ETIMEDOUT)\b`

A match here should generate a diagnostic question, not a conclusion — e.g. "detected ECONNREFUSED against the configured backend URL; is the backend expected to be running there right now?" Confirm with an actual request before reporting it as a finding.

## Configuration variable discovery (for the mismatch check in discovery.md)

| Target | Pattern |
|---|---|
| Frontend API base URL env vars | `(?i)(VITE_API_URL|NEXT_PUBLIC_API_URL|REACT_APP_API_URL)\s*=` |
| Backend host/port env vars | `(?i)(HOST|PORT|API_PORT|SERVER_PORT)\s*=` |
| Docker exposed ports | `(?i)\bports\s*:` |

## Using these responsibly

1. Regex finds **candidates**. Confirm with a real read of the matched line/file before recording it as discovered.
2. Never let a regex match trigger a write action by itself — it only ever feeds into `references/questioning-engine.md` (creates a question/TODO item) or `references/discovery.md` (records a finding).
3. Exclude `node_modules/`, `.venv`/`venv/`, `dist/`, `build/`, `.next/`, `target/`, and any vendored/minified files from all scans.
4. When a project uses a framework not listed here, say so plainly rather than forcing a bad match — ask the user or fall back to reading the entry point files directly.
