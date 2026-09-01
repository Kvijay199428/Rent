# Discarded Remote Features (from origin/main merge)

This records feature work that existed on `origin/main` but was **discarded** during the
merge of `origin/main` into local `main` (commit resolution below), per explicit decision:

> Keep the current local repo behavior. Discard remote's redis/cache, broadcast,
> and blue-green deployment work. Record what was discarded so we can review later
> whether those features are needed.

These features are available in git history (`origin/main`) and can be re-applied /
re-evaluated later without loss.

## Decision date
2026-09-01

## Discarded feature: Redis caching layer
Remote commit: `1c3a008` ("feat(cache): add Redis caching layer for backend performance")

Discarded files:
- `backend/app/app/services/cacheservice.py` (deleted)
- Redis wiring added to: `health.py`, `pdf.py`, `public.py`, `sync_ws.py`,
  `tenant_pdf.py`, `tenants.py`, `platform_admin.py`, `billing_service.py`,
  `tenant_service.py`
- `backend/requirements.txt` (redis dependency)
- `redis-dev-data` service/volume in `compose.dev.yml`
- dev redis container (`127.0.0.1:28086:6379`)

## Discarded feature: Maintenance broadcast system (shared/backend)
Remote commit: `054a902` ("feat(broadcast): maintenance broadcast system with
server-down detection")

Discarded files:
- `backend/app/app/services/broadcastservice.py` (deleted)
- `frontend/shared/BroadcastBanner.tsx` (deleted)
- `frontend/shared/BroadcastBanner.css` (deleted)
- `frontend/shared/useServerStatus.ts` (deleted)
- `frontend/offline.html` (deleted)
- Shared-broadcast wiring in `app/.../App.tsx` (per-app variants) and
  `landlord-app/src/components/layout/MainLayout.tsx`
- Tighter `/health` proxy timeout (3s/5s) in `gateway/nginx/routes/api.conf`
  (reverted to local 10s/60s)

Kept instead: local per-app `BroadcastBanner` components under each
`frontend/<app>/src/components/BroadcastBanner.*`.

## Discarded feature: Production blue-green deployment
Remote commits: `a4a81b3` ("feat(deploy): add --Local target"),
`396e5b3` (merge "redis/broadcast/deploy")

Discarded files:
- `compose.prod.yml`: blue-green `propaura-prod-backend-blue`/`green` slots
  (kept local single-slot `backend_prod` instead)
- `gateway/nginx/upstream/inactive.conf` (deleted; kept single active upstream)
- `deploy/deploy-release.sh`, `deploy/self-pull.sh`: blue-green flip logic
- `nginx/dev-gateway.conf` / `gateway/nginx/nginx.conf`: blue-green upstream wiring

## Discarded feature: Remote dev/prod service naming & structure
Remote renamed dev services to `propaura-dev-*` and added a redis dev service.

Discarded files:
- `compose.dev.yml` / `compose.prod.yml` service renames to `propaura-dev-*`
- `deploy.py` `SCOPE_SERVICES` mapping to `propaura-dev-*`

Kept instead: local naming (`propaura_backend_dev`, `propaura_frontend_dev`,
single-slot prod) and the unified `docker restart propaura_backend_dev` dev scope.

## Other remote-only helper files (not referenced by app, discarded with the merge)
- `Chrome-MCP.md`
- `frontend-test/` (`compose.yml`, `nginx.conf`)

## How to re-review
To inspect any discarded feature without touching `main`:

```bash
git log origin/main --oneline -6
git show 1c3a008        # redis cache
git show 054a902        # broadcast
git show a4a81b3        # deploy --Local
git diff HEAD origin/main   # full remote delta vs local
```
