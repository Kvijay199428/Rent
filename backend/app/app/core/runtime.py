"""Runtime environment helpers for the dev/release split."""
import os


def app_env() -> str:
    """Return the runtime environment: 'release' or 'development'."""
    return os.environ.get("APP_ENV", "development").strip().lower()


def serve_frontend() -> bool:
    """Whether this backend instance serves frontend pages (dev only).

    Release backends are API-only — page routers and frontend static
    mounts are skipped so no HTML is ever served on the API host.
    """
    value = os.environ.get("SERVE_FRONTEND", "true").strip().lower()
    return value not in ("0", "false", "no")


def enable_swagger() -> bool:
    """Whether /docs, /redoc and /openapi.json are exposed."""
    value = os.environ.get("ENABLE_SWAGGER", "true").strip().lower()
    return value not in ("0", "false", "no")


def cors_origins() -> list[str]:
    """Comma-separated CORS allowlist from CORS_ALLOW_ORIGINS."""
    raw = os.environ.get(
        "CORS_ALLOW_ORIGINS", "https://rent.vijaykrsha.online"
    )
    return [o.strip() for o in raw.split(",") if o.strip()]
