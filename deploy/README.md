# Dev/Production Split — Single-Slot Deployment

Two fully isolated environments. `production` is production; `dev` is development.

```
RELEASE (production)                                        DEVELOPMENT (ngrok)
──────────────────────────────────────────────              ─────────────────────────
cloudflared / DNS ─► rent.vijaykrsha.online                 ngrok tunnel ─► propaura_nginx_gateway_dev (28005)
                        ▲ (Cloudflare Pages)                                    │
                        │                                                       ├─ /health, API → propaura_backend_dev (28002)
api.vijaykrsha.online ─► propaura_nginx_gateway_prod                            └─ every page path → 404
                        (host 28014 → cont 28014)                                     (API-only backend, no page router)
                            │
                            └─ /health, /api, /ws → propaura_backend_prod (28011, expose only)
   data: PostgreSQL pgdata_prod (28013) │ storage/release (28012)           data: pgdata_dev (28004) │ storage/dev (28003)
```

A single release backend container runs at a time; application data lives in
PostgreSQL (`pgdata_prod` named volume) plus the shared `storage/release` tree
for keys/uploads/backups — SQLite is retired. The edge nginx points at the
backend via `gateway/nginx/upstream/active.conf` and proxies API paths only:
every frontend page path on `api.vijaykrsha.online` / `app.vijaykrsha.online`
(and on the dev ngrok host) is a strict `404` with no redirect. All frontends —
public (`rent.vijaykrsha.online`), landlord/admin (`app.vijaykrsha.online`, via
the same SPA), and dev (`dev.rent-8rf.pages.dev`) — are served ONLY by Cloudflare
Pages from the `production` / `dev` branches. A deploy rebuilds and
force-recreates that one backend container (brief restart), then reloads the
edge.

Canonical ports are single-sourced in `deploy/ports.py` and regenerated into
`deploy/ports.env` by `deploy.py` — never hand-edit either file's values.

## Ports

| Service    | Dev                     | Release                    |
|------------|-------------------------|----------------------------|
| Frontend   | — (Cloudflare Pages `dev` branch → dev.rent-8rf.pages.dev) | — (Cloudflare Pages `production` branch → rent.vijaykrsha.online) |
| Backend    | 28002 → 28002 (exposed) | 28011 → 28011 (expose only)|
| Storage    | 28003 → 28003 (expose)  | 28012 → 28012 (expose only)|
| Database   | 28004 → 28004 (expose)  | 28013 → 28013 (expose only)|
| Edge       | 28005 → 28005 (dev nginx) | 28014 → 28014 (nginx_gateway) |

PostgreSQL and storage are expose-only (never published to the host); only the
edge (and backend in dev) get host-published ports. The dev ngrok tunnel has no
compose service or reserved host port — it is the account's reserved URL served
by the systemd-hosted agent on the server (see "What `--dev` runs" below).

## Required Docker network

```bash
docker network create propaura-network
```

`compose.prod.yml` joins this external network so the edge nginx can resolve
the backend by container name. `compose.dev.yml` uses a private bridge
(`dev-net`) and needs no external network.

## Env files (both gitignored — never commit)

```bash
cp .env.release.example .env.release
cp .env.development.example .env.development
```

- `.env.release` — `APP_ENV=release`, `SERVE_FRONTEND=false`, `ENABLE_SWAGGER=false`,
  separate secrets, `CORS_ALLOW_ORIGINS=https://rent.vijaykrsha.online,...`,
  `RENT_PG*`/`POSTGRES_*` for PostgreSQL (`propaura_database_prod`).
- `.env.development` — `APP_ENV=development`, `SERVE_FRONTEND=false` (both envs
  are API-only by default), `ENABLE_SWAGGER=true`, separate secrets, same
  `RENT_PG*`/`POSTGRES_*` against `propaura_database_dev`. Dev differs only in
  `PUBLIC_APP_URL=https://dev.rent-8rf.pages.dev` (frontend origin for
  share/WhatsApp/QR links) and `VITE_API_BASE_URL` = the server's reserved ngrok
  URL (the dev API origin). The ngrok agent itself runs as a systemd service on
  the server — no `NGROK_*` vars are needed in the env file.

**Never** share JWT/pin-vault secrets between the two files. Generate unique ones:

```bash
openssl rand -hex 32        # JWT secrets
openssl rand -base64 32     # tenantPin_VAULT_KEY
```

`POSTGRES_PASSWORD` / `RENT_PGPASSWORD` must be set in each file (compose fails
fast if `POSTGRES_PASSWORD` is missing) and should differ between environments.

## Google OAuth parity (audit)

Google sign-in uses the **same Google OAuth client in every environment** — dev
and release are intentionally identical so an audit of the Google config can be
run against either. Verified `2026-08-08` by byte + sha256 comparison.

| Variable                | `.env` | `.env.development` | `.env.release` |
|-------------------------|--------|--------------------|----------------|
| `GOOGLE_CLIENT_ID`      | same   | same               | same           |
| `GOOGLE_CLIENT_SECRET`  | same   | same               | same           |
| `VITE_GOOGLE_CLIENT_ID` | same   | same               | same           |

Shared client ID:
`682816703845-ek2up1l56iah950pohj1ol3h7ijlidmr.apps.googleusercontent.com`

Notes for the audit:

- **No `redirect_uri` / `auth_uri` in the repo.** The app uses Google Identity
  Services (GSI) auth-code flow: the frontend
  (`frontend/landlord-app/src/pages/LandlordAuthPage.tsx` →
  `useGoogleLogin({ flow: "auth-code" })`) opens Google's popup and forwards the
  returned authorization `code` to
  `backend/app/app/services/google_oauth_service.py`, which exchanges it at
  `https://oauth2.googleapis.com/token` for an ID token using
  `GOOGLE_CLIENT_SECRET` (with `redirect_uri=postmessage`), then verifies it
  with `id_token.verify_oauth2_token(...)`. No explicit redirect URI needs to be
  registered; the GSI popup handshake validates JavaScript origins only.
- **Authorized JavaScript origins live in the Google Cloud Console** for the
  OAuth client above, not in this repo. Every origin that serves a frontend
  build must be registered there or the Google popup is rejected
  (`origin_mismatch`). Required origins today:
  - `https://app.vijaykrsha.online` (release landlord/admin SPA)
  - `https://rent.vijaykrsha.online` (public frontend)
  - `https://dev.rent-8rf.pages.dev` (dev frontend, Cloudflare Pages `dev`
    branch; the ngrok URL serves only the API, never a page, so it is not a
    JS origin)
  - http://localhost:3000 / other local Vite origins for local development
- **`VITE_GOOGLE_CLIENT_ID` is not a secret** and is committed in
  `frontend/landlord-app/.env.example`; `GOOGLE_CLIENT_SECRET` is gitignored
  and must never be committed. The backend reads `GOOGLE_CLIENT_SECRET` from the
  environment to exchange the auth code — it must be present in both
  `.env.development` and `.env.release`.

Reproduce the check (values are hashed only, never printed):

```bash
for k in GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET VITE_GOOGLE_CLIENT_ID; do
  for f in .env .env.development .env.release; do
    printf "%-20s %-16s sha: %s\n" "$k" "$f" \
      "$(grep -E "^$k=" "$f" | head -1 | cut -d= -f2- | sha256sum | cut -c1-12)"
  done
done
```

All three files must show the same sha per variable. The only Google-adjacent
dev/release delta is non-OAuth: `VITE_API_BASE_URL` in `.env.development` is a
placeholder (`https://CHANGE_ME.ngrok-free.app`) vs `https://api.vijaykrsha.online`
in release — do not mistake this for a Google mismatch.

## One script for both environments — `deploy.py`

`deploy.py` is the single entry point for dev and prod deploys, on your machine
or from GitHub Actions.

| Flags | Deploys | Example |
|-------|---------|---------|
| `--dev` | Alpha / developer branch (`dev`) via `compose.dev.yml` + `.env.development`, ngrok | `python3 deploy.py --dev --sshPublic` |
| `--prod` | Beta / production-grade branch (`production`) via `deploy/deploy-release.sh` | `python3 deploy.py --prod --sshPublic` |
| `--release` | Release branch (`main`) via `deploy/deploy-release.sh` | `python3 deploy.py --release --sshPublic` |

Existing flags still work: `--local`, `--sshLocal`, `--sshPublic`, `--clean`
(dev only — refused for prod/release), `--no-build`. No env flag given defaults to
`--dev`. An explicit `--dev`/`--prod`/`--release` with no transport flag defaults
to running locally on the server (self-pull of that branch); combine them with
`--sshLocal`/`--sshPublic` to push from a machine instead. For manual push
deploys, `DEPLOY_PASSWORD` (server password, default `1010`) overrides the
embedded password.

Deploy writes `deploy/ports.env` from `deploy/ports.py` before provisioning the
frontend env so every `*_DEV_PORT` / `*_RELEASE_PORT` stays in sync.

### Scoped deploys — ship only what was fixed

Add a scope flag to limit the upload (and the dev compose step) to the
components you actually changed. Default is `--all` (the whole repo).

| Scope       | Ships | Dev compose step |
|-------------|-------|------------------|
| `--all`     | entire repo (default) | `build` + `up -d` all services |
| `--frontend`| `frontend/` + root infra | sync + reload nginx (no container; dev frontend builds on Cloudflare Pages `dev` branch) |
| `--backend` | `backend/` + root infra | `build`/`up` `propaura_backend_dev` |
| `--storage` | `storage/` incl. config + backups (dev) | `restart propaura_backend_dev` (reloads config) |
| `--database`| `backend/app/app/database/`, `core/db.py` + root infra | `build`/`up` `propaura_backend_dev` (runs `init_db`) |

- Scoped zips **always** also carry the small root infra set
  (`compose.dev.yml`, `compose.prod.yml`, `.env*`, `nginx/`, `gateway/`,
  `deploy/`, `infrastructure/`) so the server overlay stays self-sufficient.
- Extraction is additive — files outside the scope are left untouched on the
  server.
- `--clean` **requires `--all`**: it wipes the server repo and re-extracts the
  package, so combining it with a scope is rejected by the parser.
- `--storage` and `--database` **overwrite server data with your local files**
  (config, dev backups). Only use them when you intentionally want to ship those.

```bash
python3 deploy.py --dev --sshPublic --clean             # full clean dev deploy
python3 deploy.py --dev --sshPublic --backend           # only backend/ fixes
python3 deploy.py --dev --sshPublic --frontend          # only frontend/ fixes
python3 deploy.py --dev --sshPublic --storage           # storage incl. dev data
python3 deploy.py --dev --sshPublic --database          # schema code (+ init_db)
python3 deploy.py --dev --sshPublic --clean --backend   # ERROR (clean implies --all)
```

```bash
# Development
python3 deploy.py --dev --sshPublic

# Production (single slot, brief restart)
python3 deploy.py --prod --sshPublic
```

### What `--dev` runs

Uploads the repo (no npm builds — the frontend is built and hosted on Cloudflare
Pages: `dev` branch → `dev.rent-8rf.pages.dev`, `production` branch →
`rent.vijaykrsha.online`), then on the server:
`docker compose --env-file .env.development -f compose.dev.yml build && up -d`.
Backend on container port 28002 (hot reload, host-published), edge dev nginx on
host 28005. The dev backend is API-only (`SERVE_FRONTEND=false`): it registers
no page router, so the dev edge nginx returns a strict `404` for every page path
(`/t/`, `/tenant/...`, `/landlord/...`, `/admin/`, `/`) and only proxies
API/health/static/tenant-portal-API paths to `propaura_backend_dev`.

The dev ngrok tunnel is the **systemd-hosted** agent on the server
(`ngrok.service`, `/home/vega/.config/ngrok/ngrok.yml`) — it owns the account's
reserved URL and is repointed to `http://localhost:28005` (the dev edge nginx,
not the backend directly — the edge routes API vs 404 for pages). No compose
`ngrok` service exists; the tunnel is purely infrastructure on the server.

Copy the tunnel URL into `VITE_API_BASE_URL` (and it's the same value the server
env uses as the external dev API origin) in `.env.development` and redeploy to
apply.

### What `--prod` runs

Uploads the repo, then on the server runs `./deploy/deploy-release.sh`: builds the
backend image, force-recreates `propaura_backend_prod`, waits for `/health`,
reloads the edge nginx, and smoke-tests. The frontend is NOT built by a deploy —
it is deployed separately to Cloudflare Pages (`production` branch). Requires
`.env.release` on the server (shipped inside the upload).

```bash
# First deploy
python3 deploy.py --prod --sshPublic
# Thereafter: same command — it recreates the single slot every time
```

The script:
1. Builds `propaura_backend_prod` (image `propaura-backend-release`).
2. Starts/force-recreates the backend container.
3. Waits for `/health` (30 × 3s) inside the container.
4. Brings up `propaura_nginx_gateway_prod` if needed (API-only edge; no frontend
   is mounted or served).
5. Reloads the edge nginx and smoke-tests `/health` through the edge
   (`127.0.0.1:28014`).

### Rollback

```bash
# Re-deploy the previous image (single slot — no pointer to flip)
docker compose --env-file .env.release -f compose.prod.yml up -d --force-recreate propaura_backend_prod
```

Or simply: `git revert HEAD` and re-push to `production` (re-deploys old code).

## Server self-pull (automatic backend deploys)

The deploy server is behind home NAT — it only has a Tailscale address
(`100.107.83.28`), so GitHub Actions **cannot push to it**. Instead the server
pulls from GitHub and deploys itself using the same `deploy.py`:

```
GitHub (dev/production/main push)
        │
        ▼  git fetch (outbound — always works)
server systemd timer ──► ./deploy/self-pull.sh dev|production|release
        │                          │
        │   └──► python3 deploy.py --dev (dev)   ──► compose.dev.yml up
        │    python3 deploy.py --prod --no-build (production) ──► deploy-release.sh (single slot)
        └──── python3 deploy.py --release --no-build (release/main) ──► deploy-release.sh (single slot)
```

Setup (run once on the server):

```bash
git clone https://github.com/Kvijay199428/Rent.git /home/vega/rent-app
mkdir -p /home/vega/rent-secrets
cp .env.release .env.development /home/vega/rent-secrets/
# systemd oneshot services + 2-minute timers (as root):
cat > /etc/systemd/system/rent-deploy-dev.service <<'EOF'
[Unit]
Description=Rent dev self-pull deploy
After=network-online.target docker.service
Wants=network-online.target
[Service]
Type=oneshot
WorkingDirectory=/home/vega/rent-app
ExecStart=/home/vega/rent-app/deploy/self-pull.sh dev
EOF
cat > /etc/systemd/system/rent-deploy-dev.timer <<'EOF'
[Unit]
Description=Rent dev self-pull timer
[Timer]
OnBootSec=1min
OnUnitActiveSec=2min
Persistent=true
[Install]
WantedBy=timers.target
EOF
# same for production (self-pull.sh production) and release (self-pull.sh release)
systemctl daemon-reload
systemctl enable --now rent-deploy-dev.timer rent-deploy-production.timer rent-deploy-release.timer
```

Production and release deploys are gated: `deploy/self-pull.sh production` /
`deploy/self-pull.sh release` exit without deploying until
`/home/vega/rent-secrets/RELEASE_READY` exists. Create it only after the
cloudflared tunnel ingress has been switched from the legacy
`propaura_legacy_gateway` (port 80) to `propaura_nginx_gateway_prod`
(host 28014).

### First-time migration (one-time manual sequence)

The scripted initial deploy (`deploy-release.sh`) starts the backend before
`propaura_nginx_gateway_prod` is up, so the first migration is done by hand on the
release clone (`/home/vega/rent-app-release`):

1. Data seed:
   - PostgreSQL: restore the migrated dump into `pgdata_prod` (verify the
     replica's PG major version matches postgres:16-alpine first), or let
     `database_prod` start empty and run the app's `init_db`/backfill.
   - Storage: copy `config/`, keys, `tenantPin_VAULT_KEY` (legacy value, so
     migrated data decrypts) and any uploads into `storage/release/`.
2. Build and start the stack, edge LAST, then flip the tunnel:
   ```
   docker compose --env-file .env.release -f compose.prod.yml build propaura_backend_prod
   docker compose --env-file .env.release -f compose.prod.yml up -d --no-deps propaura_database_prod
   docker compose --env-file .env.release -f compose.prod.yml up -d --no-deps propaura_backend_prod   # wait for /health
   docker compose --env-file .env.release -f compose.prod.yml up -d --no-deps propaura_nginx_gateway_prod
   curl -f http://127.0.0.1:28014/health
   ```
3. Cloudflare dashboard: point the tunnel's `api.vijaykrsha.online` public
   hostname at `http://localhost:28014`.
4. Verify `https://api.vijaykrsha.online/health` returns the backend JSON
   health, then retire the legacy edge:
   ```
   docker stop propaura_legacy_gateway propaura_legacy_backend
   touch /home/vega/rent-secrets/RELEASE_READY
   ```
After this, all future production deploys run the standard gated single-slot flow
via the self-pull timer.

## GitHub Actions (auto deploy)

| Workflow | Trigger | Deploys |
|----------|---------|---------|
| server self-pull | push to `dev`, `production`, or `main` (polled every 2 min by systemd timer) | `deploy.py --dev` (dev → dev stack), `deploy.py --prod` (production → single-slot prod), or `deploy.py --release` (main → single-slot prod) |
| `deploy-cloudflare-pages.yml` | push to `production` (`frontend/**`) | Build → Cloudflare Pages (branch `production`) |
| `create-github-release.yml` | tag `v*` | GitHub Release with auto notes |

### Secrets & variables

Settings → Secrets and variables → Actions:

- `CLOUDFLARE_API_TOKEN` (secret) — Pages edit token
- `CLOUDFLARE_ACCOUNT_ID` (secret)
- `VITE_GOOGLE_CLIENT_ID` (secret)
- `CLOUDFLARE_PROJECT_NAME` (variable) — `rent`

No server SSH key or password is needed in GitHub Actions — backend deploys run
server-side via self-pull. The server only needs `docker` (with compose v2),
`python3`, and `git`.

### Cloudflare Pages: set production branch to `production`

In the Cloudflare dashboard (Workers & Pages → your `rent` project → Settings →
Builds & deployments), set **Production branch = `production`**. The
`deploy-cloudflare-pages.yml` workflow deploys with `--branch=production`.

## API-only release backend + Pages-hosted frontends

The release backend sets `SERVE_FRONTEND=false` (the default): the landing page,
tenant/landlord SPA routers and the frontend static mounts are **not registered**
(`backend/app/app/core/router_registry.py`, `backend/app/app/core/startup.py`);
swagger/docs are disabled (`ENABLE_SWAGGER=false`); CORS is read from
`CORS_ALLOW_ORIGINS`.

All page serving happens ONLY on Cloudflare Pages: `production` branch →
`rent.vijaykrsha.online` (public + landlord/admin SPA). The edge nginx
(`api.vijaykrsha.online`, `app.vijaykrsha.online`) is API-only — it proxies
`/health`, API, `/static/uploads` and WebSockets to the backend slot and returns
a strict `404` (no redirect) for every page path. No frontend build is mounted
into the gateway or built by backend deploys.