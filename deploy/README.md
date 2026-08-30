# Dev/Release Split — Single-Slot Deployment

Two fully isolated environments. `release` is production; `main` is development.

```
RELEASE (production, api.vijaykrsha.online)        DEVELOPMENT (ngrok)
──────────────────────────────────────────        ─────────────────────────
cloudflared / DNS  →  propaura_nginx_gateway_prod  ngrok tunnel  →  propaura_backend_dev (28001)
                      (host 28005 → cont 28007)                    │
                         │                                         │
                      storage/release/rent.db                  storage/dev/rent.db
                         │
   propaura_backend_prod (28005) ──── propaura_frontend_prod (host 28004 → cont 28006)
      rent.vijaykrsha.online         (Cloudflare Pages, release build)
```

A single release backend container runs at a time (SQLite is shared via
`storage/release`), so there is never a second writer on the database. The edge
nginx points at it via `gateway/nginx/upstream/active.conf`. A deploy rebuilds
and force-recreates that one container (brief restart), then reloads the edge.

## Ports

| Service         | Dev  | Release |
|-----------------|------|---------|
| Backend         | 28001 → 28001 (ngrok) | 28005 → 28005 (single slot) |
| Frontend        | 28003 → 28002 (Vite) | 28004 → 28006 (static SPA container) |
| Edge            | 28080 → 28003 (dev nginx) | 28005 → 28007 (nginx_gateway) |
| ngrok dashboard | 28004 → 4040 | — |

## Required Docker network

```bash
docker network create propaura-network
```

`compose.prod.yml` joins this network so the edge nginx can resolve the backend
by container name. If you keep the legacy `gateway/compose.yml` edge, it must
also be connected: `docker network connect propaura-network propaura_legacy_gateway`.

## Env files (both gitignored — never commit)

```bash
cp .env.release.example .env.release
cp .env.development.example .env.development
```

- `.env.release` — `APP_ENV=release`, `SERVE_FRONTEND=false`, `ENABLE_SWAGGER=false`,
  separate secrets, `CORS_ALLOW_ORIGINS=https://rent.vijaykrsha.online,...`,
  DB in `storage/release/rent.db`.
- `.env.development` — `APP_ENV=development`, `SERVE_FRONTEND=true`,
  `ENABLE_SWAGGER=true`, separate secrets, DB in `storage/dev/rent.db`, plus the
  ngrok auth token and `NGROK_API_BASE_URL`.

**Never** share JWT/pin-vault secrets between the two files. Generate unique ones:

```bash
openssl rand -hex 32        # JWT secrets
openssl rand -base64 32     # tenantPin_VAULT_KEY
```

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
  Services (GSI) ID-token flow: the frontend
  (`frontend/landlord-app/src/main.tsx` → `GoogleOAuthProvider`) obtains a
  credential and `backend/app/app/services/google_oauth_service.py` verifies it
  with `id_token.verify_oauth2_token(...)`. No redirect URI is used and the
  client secret is not read by the backend.
- **Redirect URIs / authorized JavaScript origins live in the Google Cloud
  Console** for the OAuth client above, not in this repo. For the dev flow to
  work end-to-end, the dev origin (ngrok URL) must be registered there.
- **`VITE_GOOGLE_CLIENT_ID` is not a secret** and is committed in
  `frontend/landlord-app/.env.example`; `GOOGLE_CLIENT_SECRET` is gitignored
  and must never be committed.

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
| `--dev` | Development stack (`compose.dev.yml` + `.env.development`, ngrok) | `python3 deploy.py --dev --sshPublic` |
| `--prod` | Production single-slot (`deploy/deploy-release.sh`) | `python3 deploy.py --prod --sshPublic` |
| `--main` | Main-branch deploy — runs **here** (self-pull on the server) | `python3 deploy.py --main` |
| `--release` | Release-branch deploy — runs **here** (self-pull on the server) | `python3 deploy.py --release` |

Existing flags still work: `--local`, `--sshLocal`, `--sshPublic`, `--clean`
(dev only — refused for prod), `--no-build`. No env flag given defaults to
`--dev`. `--main`/`--release` default to running locally on the server
(self-pull); combine them with `--sshLocal`/`--sshPublic` to push from a
machine instead. For manual push deploys, `DEPLOY_PASSWORD` (server password,
default `1010`) overrides the embedded password.

### Scoped deploys — ship only what was fixed

Add a scope flag to limit the upload (and the dev compose step) to the
components you actually changed. Default is `--all` (the whole repo).

| Scope       | Ships | Dev compose step |
|-------------|-------|------------------|
| `--all`     | entire repo (default) | `build` + `up -d` all services |
| `--frontend`| `frontend/` + root infra | `build`/`up` `propaura_frontend_dev` |
| `--backend` | `backend/` + root infra | `build`/`up` `propaura_backend_dev` |
| `--storage` | `storage/` incl. SQLite DBs + config + backups | `restart propaura_backend_dev` (reloads config) |
| `--database`| `backend/app/app/database/`, `core/db.py`, `rent.db` + root infra | `build`/`up` `propaura_backend_dev` (runs `init_db`) |

- Scoped zips **always** also carry the small root infra set
  (`compose.dev.yml`, `compose.prod.yml`, `.env*`, `nginx/`, `gateway/`,
  `deploy/`, `infrastructure/`) so the server overlay stays self-sufficient.
- Extraction is additive — files outside the scope are left untouched on the
  server.
- `--clean` **requires `--all`**: it wipes the server repo and re-extracts the
  package, so combining it with a scope is rejected by the parser.
- `--storage` and `--database` **overwrite server data with your local files**
  (SQLite DBs, config). Only use them when you intentionally want to ship those.

```bash
python3 deploy.py --dev --sshPublic --clean             # full clean dev deploy
python3 deploy.py --dev --sshPublic --backend           # only backend/ fixes
python3 deploy.py --dev --sshPublic --frontend          # only frontend/ fixes
python3 deploy.py --dev --sshPublic --storage           # storage incl. DBs
python3 deploy.py --dev --sshPublic --database          # schema code + rent.db
python3 deploy.py --dev --sshPublic --clean --backend   # ERROR (clean implies --all)
```

```bash
# Development
python3 deploy.py --dev --sshPublic

# Production (single slot, brief restart)
python3 deploy.py --prod --sshPublic
```

### What `--dev` runs

Uploads the repo (no npm builds — Vite runs live), then on the server:
`docker compose --env-file .env.development -f compose.dev.yml build && up -d`.
Backend on port 28001 (hot reload), tenant-app Vite on host 28003 (container 28002).

The dev ngrok tunnel on the server is the **systemd-hosted** agent
(`ngrok.service`, `/home/vega/.config/ngrok/ngrok.yml`) — it owns the account's
reserved URL and is repointed to `http://localhost:28001`. The docker `ngrok`
service is behind the `ngrok` compose profile (avoids a port/URL clash):

```bash
# only where no host ngrok exists (e.g. a laptop):
docker compose --env-file .env.development -f compose.dev.yml --profile ngrok up -d
# dashboard: http://localhost:28004
```

Copy the tunnel URL into `NGROK_API_BASE_URL` and `VITE_API_BASE_URL` in
`.env.development` and redeploy to apply.

### What `--prod` runs

Uploads the repo (building the 4 frontend apps unless `--no-build`), then on the
server runs `./deploy/deploy-release.sh`: builds the backend image, force-recreates
`propaura_backend_prod`, waits for `/health`, reloads the edge nginx, and
smoke-tests. Requires `.env.release` on the server (shipped inside the upload).

```bash
# First deploy
python3 deploy.py --prod --sshPublic
# Thereafter: same command — it recreates the single slot every time
```

The script:
1. Builds `propaura_backend_prod`.
2. Starts/force-recreates the backend container.
3. Waits for `/health` (30 × 3s) inside the container.
4. Brings up `propaura_frontend_prod` + `propaura_nginx_gateway_prod` if needed.
5. Reloads the edge nginx and smoke-tests `/health` through the edge.

### Rollback

```bash
# Re-deploy the previous image (single slot — no pointer to flip)
docker compose --env-file .env.release -f compose.prod.yml up -d --force-recreate propaura_backend_prod
```

Or simply: `git revert HEAD` and re-push to `release` (re-deploys old code).

## Server self-pull (automatic backend deploys)

The deploy server is behind home NAT — it only has a Tailscale address
(`100.107.83.28`), so GitHub Actions **cannot push to it**. Instead the server
pulls from GitHub and deploys itself using the same `deploy.py`:

```
GitHub (main/release push)
        │
        ▼  git fetch (outbound — always works)
server systemd timer ──► ./deploy/self-pull.sh main|release
        │                          │
             └──► python3 deploy.py --main (dev)   ──► compose.dev.yml up
              python3 deploy.py --release --no-build (prod) ──► deploy-release.sh (single slot)
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
ExecStart=/home/vega/rent-app/deploy/self-pull.sh main
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
# same for release (self-pull.sh release)
systemctl daemon-reload
systemctl enable --now rent-deploy-dev.timer rent-deploy-release.timer
```

Release deploys are gated: `deploy/self-pull.sh release` exits without deploying
until `/home/vega/rent-secrets/RELEASE_READY` exists. Create it only after the
cloudflared tunnel ingress has been switched from the legacy `propaura_legacy_gateway`
(port 80) to `propaura_nginx_gateway_prod` (host 28005) — the first deploy retires
the legacy edge.

### First-time migration (one-time manual sequence)

The scripted initial deploy (`deploy-release.sh`) starts the backend before
`propaura_nginx_gateway_prod` is up, so the first migration is done by hand on the
release clone (`/home/vega/rent-app-release`):

1. Seed data into `storage/release/` (copy the legacy `rent.db` + `uploads/`,
   `receipts/`, `config/` from the old backend's storage), and set
   `tenantPin_VAULT_KEY` in `.env.release` to the legacy value so the migrated
   DB can be decrypted.
2. Build and start the stack, edge LAST, then flip the tunnel:
   ```
   docker compose --env-file .env.release -f compose.prod.yml build propaura_backend_prod
   docker compose --env-file .env.release -f compose.prod.yml up -d --no-deps propaura_backend_prod   # wait for /health
   docker compose --env-file .env.release -f compose.prod.yml up -d --no-deps propaura_nginx_gateway_prod propaura_frontend_prod
   curl -f http://127.0.0.1:28005/health
   ```
3. Cloudflare dashboard: point the tunnel's `api.vijaykrsha.online` public
   hostname at `http://localhost:28005`.
4. Verify `https://api.vijaykrsha.online/health` returns the backend JSON
   health, then retire the legacy edge:
   ```
   docker stop propaura_legacy_gateway propaura_legacy_backend
   touch /home/vega/rent-secrets/RELEASE_READY
   ```
After this, all future release deploys run the standard gated single-slot flow
via the self-pull timer.

## GitHub Actions (auto deploy)

| Workflow | Trigger | Deploys |
|----------|---------|---------|
| server self-pull | push to `main` or `release` (polled every 2 min by systemd timer) | `deploy.py --main` (main → dev stack) or `deploy.py --release` (release → single-slot prod) |
| `deploy-cloudflare-pages.yml` | push to `release` (`frontend/**`) | Build → Cloudflare Pages (branch `release`) |
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

### Cloudflare Pages: set production branch to `release`

In the Cloudflare dashboard (Workers & Pages → your `rent` project → Settings →
Builds & deployments), set **Production branch = `release`**. The `deploy-cloudflare-pages.yml`
workflow deploys with `--branch=release`.

## API-only release backend

The release backend sets `SERVE_FRONTEND=false`:

- Landing page, tenant/landlord SPA routers and the 4 frontend static mounts are
  **not registered** (`backend/app/app/core/router_registry.py`,
  `backend/app/app/core/startup.py`).
- Swagger/docs are disabled (`ENABLE_SWAGGER=false`).
- CORS is read from `CORS_ALLOW_ORIGINS`.

All page serving is moved to `propaura_frontend_prod` (host 28004) and Cloudflare
Pages. The edge nginx routes `/rent/*` and tenant deep links to the frontend;
everything else (API, `/static/uploads`, WebSockets) goes to the backend slot.
