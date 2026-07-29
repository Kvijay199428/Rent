# Rent Receipt System v3.0.0

Multi-tenant rent receipt management system with a FastAPI backend and four React frontend apps. Deployed via Docker + Nginx with Cloudflare Tunnel for production and Cloudflare Pages for static frontend assets.

---

## Architecture

```
Browser (rent.vijaykrsha.online)
  └─ Cloudflare Pages (static: landing, landlord, admin SPAs)
  └─ Cloudflare Tunnel ── Gateway Nginx (port 8080) ── Backend (port 28001)
       │                                                   └─ SQLite
       │                                                   └─ Storage (configs, uploads, backups)
       └─ WebSocket (sync, auth, health streams)
```

All routes are prefixed with `/rent/`. The production gateway strips this prefix before forwarding. Frontend apps are built with `VITE_API_BASE_URL` to point API calls at the backend origin.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, Uvicorn, SQLite |
| Auth | JWT (python-jose), Argon2 (passlib), TOTP (pyotp), SameSite=None cookies |
| PDF | ReportLab, num2words |
| Excel | openpyxl (import/export) |
| Frontend (Landlord) | React 19, Vite 7, Tailwind CSS 3, shadcn/ui, Recharts |
| Frontend (Admin) | React 18, React Router 6 |
| Frontend (Tenant) | React 19, Vite 8, Tailwind CSS 4, shadcn/ui, TanStack Query |
| Frontend (Landing) | React 18, Vite 5 |
| Proxy | Nginx (gateway + frontend-test) |
| Tunnel | cloudflared (Cloudflare Tunnel) |
| Deployment | Docker Compose, Python SSH scripts |

---

## Features

- **Landlord Portal**: Dashboard, billing/receipts management, tenant management, KYC, PDF receipts, WhatsApp sharing, backup/restore, TOTP 2FA, audit logs
- **Tenant Portal**: View receipts, profile, KYC upload, PIN-based access via sharing link
- **Platform Admin**: Multi-landlord oversight, system stats, security alerts, broadcast messaging, session management
- **Receipt Generation**: PDF with customizable templates, Indian number-to-words conversion
- **Data Sync**: CSV/Excel/ZIP import/export templates
- **Recovery**: Tenant recovery snapshots with TTL expiry

---

## Project Structure

```
Rent/
├── app/                    # FastAPI backend application
│   ├── app/
│   │   ├── api/            # API endpoint modules (billing, tenants, health, sync, PDF, WhatsApp, …)
│   │   ├── authentication/ # JWT + cookie auth (admin, landlord, tenant, platform)
│   │   ├── core/           # DB init, router registry, config, startup, paths
│   │   ├── database/       # Repositories, raw SQL schema
│   │   ├── models/         # Pydantic models
│   │   ├── pages/          # Server-rendered Jinja2 pages (tenant SPA, errors, etc.)
│   │   ├── routers/        # Auth routers, platform admin router
│   │   ├── services/       # Business logic (billing, PDF, backup, tenant recovery)
│   │   └── main.py         # FastAPI app entry point
│   ├── config/             # Domain, receipt, system, UI JSON configs
│   └── requirements.txt    # Python dependencies
├── backend/                # Dockerfile + compose files for backend
│   ├── Dockerfile
│   ├── compose.yml         # Production backend
│   └── compose.test.yml    # Local test override (port exposure)
├── frontend/               # All frontend applications
│   ├── shared/             # Shared code (api-config.ts, routes.json)
│   ├── landing-app/        # Public landing page (base: /rent/)
│   ├── landlord-app/       # Landlord dashboard (base: /rent/landlord/)
│   ├── platform-admin-app/ # Admin panel (base: /rent/admin/)
│   └── tenant-app/         # Tenant portal (base: /rent/t/)
├── frontend-test/          # Docker test environment (nginx + backend)
│   ├── compose.yml
│   └── nginx.conf
├── gateway/                # Production reverse proxy + tunnel
│   ├── compose.yml
│   └── nginx/
│       ├── nginx.conf      # Gateway Nginx config
│       └── routes/         # Per-service route definitions
├── deploy/                 # Python deployment scripts
│   ├── build_frontend.py   # Build all SPAs → Cloudflare Pages output
│   ├── deploy_backend.py   # SSH deploy backend to server
│   └── deploy_gateway.py   # Upload nginx routes + reload
├── scripts/                # Utility scripts (route validation, migrations)
├── shared/                 # Shared routes.json (source of truth)
├── storage/                # Runtime data (ignored by git)
│   ├── config/             # 16 JSON config files
│   ├── database/           # SQLite database
│   ├── backups/            # Backup archives
│   └── uploads/            # User uploads (KYC, signatures)
├── .env.example            # Environment variable template
├── requirements.txt        # Root Python deps (synced with app/)
└── README.md               # This file
```

---

## Frontend Apps

| App | URL Path | Vite Base | Purpose |
|---|---|---|---|
| landing-app | `/rent/` | `/rent/` | Public landing page with login/signup links |
| landlord-app | `/rent/landlord/` | `/rent/landlord/` | Landlord dashboard and management |
| platform-admin-app | `/rent/admin/` | `/rent/admin/` | Platform admin system oversight |
| tenant-app | `/rent/t/` (assets) | `/rent/t/` | Tenant portal (HTML served by backend) |

---

## Getting Started

### Prerequisites
- Python 3.13+
- Node.js 20+
- Docker + Docker Compose (optional, for containerized workflow)

### Local Backend

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd app
uvicorn app.main:app --reload --host 127.0.0.1 --port 20081
```

### Local Frontend (per app)

```bash
cd frontend/landlord-app
npm install
VITE_API_BASE_URL= npm run dev
```

Set `VITE_API_BASE_URL=https://api.vijaykrsha.online` to test against the production API.

---

## Docker Environments

### Backend (standalone)

```bash
cd backend
docker compose up -d
docker compose -f compose.test.yml up -d   # with port 28001 exposed
```

### Frontend + Backend (test environment)

```bash
cd frontend-test
docker compose up -d
# Frontend at http://localhost:28080
```

### Production Gateway

```bash
cd gateway
docker compose up -d
```

All services connect to the external Docker network `vega-gateway`.

---

## API Overview

All API routes are prefixed with `/rent/` at the proxy layer. The gateway strips this before forwarding.

| Route Group | Backend Path | Auth |
|---|---|---|
| Health | `/health` | None |
| Platform Admin | `/platform-admin/api/*` | JWT + session |
| Landlord Auth | `/landlord/api/auth/*` | None (public key, login) |
| Landlord Protected | `/landlord/{uuid}/api/*` | JWT + session |
| Tenant | `/{uuid}/t/{id}/{token}/api/*` | View-token based |
| WebSocket Sync | `/rent/ws/*` | Channel-based |

Full route definitions: `frontend/shared/routes.json` and `shared/routes.json`.

---

## Authentication

Four independent auth modules, each with JWT + signed cookies:

- **Admin**: Email/password login, session tracking, session expiry headers
- **Landlord**: Username/email signup, login, TOTP 2FA, password change, brute-force lockout
- **Tenant**: PIN-based authentication via shared URL, view-token gating
- **Platform**: Dedicated admin login for platform oversight

Cookies use `SameSite=None` + `Secure` for cross-origin support (Cloudflare Pages → API).

---

## Deployment

### Cloudflare Pages (Frontend)

```bash
pip install -r deploy/requirements.txt   # if exists, else dependencies inline
python deploy/build_frontend.py          # builds 4 apps → build-output/
```

Output structure:
```
build-output/rent/
├── index.html, assets/                (landing-app)
├── admin/index.html, admin/assets/    (platform-admin-app)
├── landlord/index.html, assets/       (landlord-app)
└── tenant/index.html, tenant/assets/  (tenant-app)
```

Deploy the `build-output/` directory to Cloudflare Pages.

### Backend (SSH)

```bash
python deploy/deploy_backend.py --host <ip> --port <ssh_port>
```

Uploads `app/`, `backend/`, and `requirements.txt`, then builds and starts the Docker container.

### Gateway (SSH)

```bash
python deploy/deploy_gateway.py --host <ip>
```

Uploads nginx route configs and reloads nginx without downtime.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `""` (same-origin) | API origin for frontend requests (e.g. `https://api.vijaykrsha.online`) |
| `RENT_STORAGE_DIR` | `/code/storage` | Runtime storage path (configs, DB, uploads, backups) |
| `JWT_SECRET` | `changeme` | Secret key for JWT signing |
| `CLOUDFLARE_TUNNEL_TOKEN` | — | Cloudflare Tunnel auth token |
| `DEPLOY_HOST` | `192.168.1.50` | Deploy script target host |
| `DEPLOY_PORT` | `22` | Deploy script SSH port |
| `DEPLOY_USER` | `vega` | Deploy script SSH user |
| `DEPLOY_KEY` | `~/.ssh/id_rsa` | Deploy script SSH key path |

---

## Network Topology

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Cloudflare      │     │  Gateway      │     │  Backend         │
│  Pages (static)  │────▶│  Nginx :8080  │────▶│  FastAPI :28001  │
│  rent.vijaykrsha │     │  + cloudflared│     │  └─ SQLite       │
│  .online         │     │              │     │  └─ Storage      │
└─────────────────┘     └──────────────┘     └─────────────────┘
                               │
                          External Docker network: vega-gateway
```

- Production domain: `rent.vijaykrsha.online` (Cloudflare Pages)
- API domain: `api.vijaykrsha.online` (Cloudflare Tunnel → Gateway)
- All routes under `/rent/` prefix
- WebSocket connections upgrade through the same proxy

---

## License

Private project.
