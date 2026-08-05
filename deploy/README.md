# Dev/Release Split — Zero-Downtime Deployment

Two fully isolated environments. `release` is production; `main` is development.

```
RELEASE (production, api.vijaykrsha.online)        DEVELOPMENT (ngrok)
──────────────────────────────────────────        ─────────────────────────
cloudflared / DNS  →  nginx_gateway (8080)        ngrok tunnel  →  backend_dev (28001)
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

## Development

```bash
docker compose --env-file .env.development -f compose.dev.yml up -d
```

- Backend on `http://localhost:28001` with hot reload.
- Tenant-app Vite dev server on `http://localhost:28003`.
- ngrok dashboard on `http://localhost:4040`. Copy the tunnel URL into
  `NGROK_API_BASE_URL` and `VITE_API_BASE_URL` in `.env.development`, then
  restart: `docker compose --env-file .env.development -f compose.dev.yml up -d`.

## Release (blue-green, zero downtime)

```bash
# First deploy
docker compose --env-file .env.release -f compose.prod.yml build
docker compose --env-file .env.release -f compose.prod.yml up -d
./deploy/deploy-release.sh     # thereafter: builds inactive slot, health-gates,
                               # flips nginx, stops old slot
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

## GitHub Actions (auto deploy)

| Workflow | Trigger | Deploys |
|----------|---------|---------|
| `deploy-release.yml` | push to `release` (backend/nginx/deploy changes) | SSH → server → `deploy-release.sh` → health check |
| `deploy-cloudflare-pages.yml` | push to `release` (`frontend/**`) | Build → Cloudflare Pages (branch `release`) |
| `create-github-release.yml` | tag `v*` | GitHub Release with auto notes |

### Secrets & variables

Settings → Secrets and variables → Actions:

- `SSH_PRIVATE_KEY` (secret) — private key for the deploy server
- `DEPLOY_SERVER_HOST` (secret) — e.g. `100.107.83.28`
- `DEPLOY_SERVER_PORT` (secret) — e.g. `22009`
- `DEPLOY_SERVER_USER` (secret) — e.g. `vega`
- `CLOUDFLARE_API_TOKEN` (secret) — Pages edit token
- `CLOUDFLARE_ACCOUNT_ID` (secret)
- `VITE_GOOGLE_CLIENT_ID` (secret)
- `CLOUDFLARE_PROJECT_NAME` (variable) — `rent`

### One-time SSH key setup (GitHub Actions → server)

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_actions_deploy
ssh-copy-id -i ~/.ssh/github_actions_deploy.pub vega@100.107.83.28 -p 22009
gh secret set SSH_PRIVATE_KEY < ~/.ssh/github_actions_deploy
gh secret set DEPLOY_SERVER_HOST --body "100.107.83.28"
gh secret set DEPLOY_SERVER_PORT --body "22009"
gh secret set DEPLOY_SERVER_USER --body "vega"
```

The server also needs `docker` (with compose v2) and `curl`.

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
