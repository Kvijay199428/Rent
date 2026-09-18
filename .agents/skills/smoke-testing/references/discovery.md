# Discovery (Level 0)

Discovery is entirely read-only: listing directories, reading files, grepping. Never write outside `.smoke-test/` here.

## What to look for at the project root

```
.git                      → is a repo; use `git status`/`git diff --stat` for fingerprinting
package.json               → Node project (frontend and/or backend)
requirements.txt/pyproject.toml → Python project
pom.xml / build.gradle     → Java project
Dockerfile / docker-compose.yml → containerized; read for ports/services, don't touch
.env.example                → expected env vars (never read the real .env's secret values into a report)
vite.config.*, next.config.* → frontend build tool
src/, frontend/, backend/, server/, api/ → likely code layout
tests/                       → existing test infra you can reuse instead of reinventing
```

## Stack detection

Use the regex patterns in `references/regex-patterns.md` §Backend discovery and §Frontend discovery against source files (not `node_modules`/`venv`/build output). Record what you find in `smoke-state.json` under `discovery.stack`.

## Route / endpoint discovery

- Backend: `references/regex-patterns.md` §API route discovery, per framework.
- Frontend: `references/regex-patterns.md` §Frontend route discovery (React Router JSX/object routes, or filesystem routes for Next.js: `app/**/page.*`, `pages/**/*.*`).
- Frontend→backend calls: `references/regex-patterns.md` §API call discovery, so you can build the dependency map (which frontend route calls which backend endpoint) referenced in `references/state-management.md`.

Turn what you find into a plain list first (not yet a TODO):

```
Backend endpoints found: GET /health, POST /api/auth/login, GET /api/tenants, ...
Frontend routes found: /login, /dashboard, /tenants, /bills, ...
Frontend→backend edges: POST /api/auth/login (LoginForm.jsx) → matches backend POST /api/auth/login
```

Then hand this to `references/questioning-engine.md` to turn each into TODO items with priorities. Reconcile against the existing `smoke-todo.json`: newly discovered endpoints/routes get new items appended (never reshuffling existing ids); a previously-tracked endpoint/route that no longer appears gets its status set to `not_applicable` with a note explaining it wasn't found this run — never silently delete the item, since its disappearance is itself worth surfacing to the user.

## Configuration mismatch checks

Compare frontend API base URL env vars (`VITE_API_URL`, `NEXT_PUBLIC_API_URL`, `REACT_APP_API_URL`, etc.) against the backend's actual listen host/port (from config, `docker-compose.yml` `ports:`, or the running process). Report a mismatch as a finding — do not "fix" the env file yourself; that's a Zone B change and goes through `references/change-control.md` if the user wants it corrected.

## Database discovery

Identify the DB technology and connection target using `assets/patterns/database.json`'s `technology_detection` patterns against config/env files and the backend's dependency manifest (`requirements.txt`/`package.json`/`pom.xml`) — never print credentials into the report, redact passwords, show only host/db name. If a read-only query capability is available (e.g., `SELECT 1`, a migrations table check, a Mongo/Redis ping), use it only to confirm connectivity/schema presence, per `database.json`'s `connectivity_check_hint`, never to modify data. Record the detected technology in `smoke-state.json` under `discovery.stack.database`.

## Fingerprinting (for every run after the first)

For each TODO item, record which files/config it depends on ("watched files") and a hash of their current content, e.g.:

```json
"fingerprint": {
  "files": ["src/routes/bills.py", "src/models/bill.py"],
  "hash": "sha256:...(concat of file hashes)..."
}
```

At the start of a run, recompute the hash for each item's watched files — `assets/scripts/compute_fingerprint.py <file1> <file2> ...` does this (prints `sha256:<hex>`) and is the concrete tool behind the fingerprint described above; use it directly rather than reinventing the hashing logic each run. For a git repo, `git diff --stat` since the last run's recorded commit is a cheaper first pass to decide *whether* to bother recomputing per-item fingerprints at all. If it changed, mark that TODO item `stale` (not delete it) so it gets re-executed; otherwise it may be carried forward as still-passing per `references/rules.md` §10.

## Decision tree: how far to go this run

```
Backend health/readiness check fails
   → Level 1 remaining items for backend: BLOCKED (not re-attempted individually)
   → Level 3/4 items that depend on backend: BLOCKED
   → Level 2 frontend-only items may still run if a mock/static mode is configured

Backend healthy, frontend fails to load
   → Level 2 remaining items: BLOCKED
   → Level 3/4 items: BLOCKED
   → Level 1 backend items: continue normally

Both healthy
   → proceed through Level 3 (one real critical workflow) then Level 4 (the user's named critical E2E flows)
```

Don't burn time running dozens of checks against a build that's fundamentally broken — that's the entire point of a smoke test (see the background doc: "Is the build basically functional?"). Report the blocking failure prominently and stop that branch.
