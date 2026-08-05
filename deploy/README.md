# Dev/Release Split — Zero-Downtime Deployment

Two fully isolated environments. `release` is production; `main` is development.

```
RELEASE (production, api.vijaykrsha.online)        DEVELOPMENT (ngrok)
──────────────────────────────────────────        ─────────────────────────
cloudflared / DNS  →  nginx_gateway (28005)        ngrok tunnel  →  backend_dev (28001)
                         │                                             │
      ┌──────────────────┼───────────────────┐                    storage/dev/rent.db
      │                    │                   │                        │
backend_release_blue  backend_release_green  frontend_release    frontend_dev (28003)
      │  (28002, active)   │ (28012, standby)  │ (28004, SPA)      (Vite, tenant-app)
      └──────────┬─────────┘                    │
                 ▼                             rent.vijaykrsha.online
      storage/release/rent.db                   (Cloudflare Pages, release build)
```

Only ONE release backend slot runs at a time (SQLite is shared via
`storage/release`), so there is never a second writer on the database. The edge
nginx points at the active slot via `gateway/nginx/upstream/active.conf` and is
atomically reloaded — the release container is never rebuilt or restarted
in-place during a deploy.

## Ports

| Service         | Dev  | Release |
|-----------------|------|---------|
| Backend         | 28001 (ngrok) | 28002 / 28012 (blue/green, via nginx) |
| Frontend        | 28003 (Vite) | 28004 (static SPA container) |
| Edge            | —            | 28005 (nginx_gateway → 8080 in-container) |

## Required Docker network

```bash
docker network create vega-gateway
```

`compose.prod.yml` joins this network so the edge nginx can resolve the backend
slots by container name. If you keep the legacy `gateway/compose.yml` edge, it
must also be connected: `docker network connect vega-gateway vega_gateway`.

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

## One script for both environments — `deploy.py`

`deploy.py` is the single entry point for dev and prod deploys, on your machine
or from GitHub Actions.

| Flags | Deploys | Example |
|-------|---------|---------|
| `--dev` | Development stack (`compose.dev.yml` + `.env.development`, ngrok) | `python3 deploy.py --dev --sshPublic` |
| `--prod` | Production blue-green (`deploy/deploy-release.sh`) | `python3 deploy.py --prod --sshPublic` |
| `--main` | Main-branch deploy — runs **here** (self-pull on the server) | `python3 deploy.py --main` |
| `--release` | Release-branch deploy — runs **here** (self-pull on the server) | `python3 deploy.py --release` |

Existing flags still work: `--local`, `--sshLocal`, `--sshPublic`, `--clean`
(dev only — refused for prod), `--no-build`. No env flag given defaults to
`--dev`. `--main`/`--release` default to running locally on the server
(self-pull); combine them with `--sshLocal`/`--sshPublic` to push from a
machine instead. For manual push deploys, `DEPLOY_PASSWORD` (server password,
default `1010`) overrides the embedded password.

```bash
# Development
python3 deploy.py --dev --sshPublic

# Production (blue-green, zero downtime)
python3 deploy.py --prod --sshPublic
```

### What `--dev` runs

Uploads the repo (no npm builds — Vite runs live), then on the server:
`docker compose --env-file .env.development -f compose.dev.yml build && up -d`.
Backend on port 28001 (hot reload), tenant-app Vite on 28003.

The dev ngrok tunnel on the server is the **systemd-hosted** agent
(`ngrok.service`, `/home/vega/.config/ngrok/ngrok.yml`) — it owns the account's
reserved URL and is repointed to `http://localhost:28001`. The docker `ngrok`
service is behind the `ngrok` compose profile (avoids a port/URL clash):

```bash
# only where no host ngrok exists (e.g. a laptop):
docker compose --env-file .env.development -f compose.dev.yml --profile ngrok up -d
# dashboard: http://localhost:4041
```

Copy the tunnel URL into `NGROK_API_BASE_URL` and `VITE_API_BASE_URL` in
`.env.development` and redeploy to apply.

### What `--prod` runs

Uploads the repo (building the 4 frontend apps unless `--no-build`), then on the
server runs `./deploy/deploy-release.sh`: builds the inactive slot, waits for
`/health`, flips the edge nginx, smoke-tests, stops the old slot. Requires
`.env.release` on the server (shipped inside the upload).

```bash
# First deploy
python3 deploy.py --prod --sshPublic
# Thereafter: same command — it blue-greens every time
```

The script:
1. Detects the active slot from `gateway/nginx/upstream/active.conf`.
2. Builds and starts the **inactive** slot (active keeps serving).
3. Waits for `/health` (30 × 3s) inside the new container.
4. Writes the new slot into `active.conf` and reloads the edge nginx (atomic).
5. Smoke-tests `/health` through the edge, then stops the old slot.

### Rollback

```bash
# Point the edge back at the previous slot and bring it up
sed -i 's/backend_release_green/backend_release_blue/' gateway/nginx/upstream/active.conf
docker exec nginx_gateway nginx -s reload
docker compose --env-file .env.release -f compose.prod.yml up -d --no-deps backend_release_blue
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
             python3 deploy.py --release --no-build (prod) ──► deploy-release.sh (blue-green)
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
cloudflared tunnel ingress has been switched from the legacy `vega_gateway`
(port 80) to `nginx_gateway` (port 28005) — the first blue-green deploy retires
the legacy edge.

## GitHub Actions (auto deploy)

| Workflow | Trigger | Deploys |
|----------|---------|---------|
| server self-pull | push to `main` or `release` (polled every 2 min by systemd timer) | `deploy.py --main` (main → dev stack) or `deploy.py --release` (release → blue-green prod) |
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

All page serving is moved to `frontend_release` (port 28004) and Cloudflare
Pages. The edge nginx routes `/rent/*` and tenant deep links to the frontend;
everything else (API, `/static/uploads`, WebSockets) goes to the backend slot.
