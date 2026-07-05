from fastapi import Request
from fastapi.templating import Jinja2Templates
from app.core.config_service import config
from app.core.paths import TEMPLATES_DIR
from app.core.route_builder import RouteBuilder
from app.core.routes import Names


def _normalize_base_path(path: str | None) -> str:
    if not path or path == "/":
        return ""
    normalized = path.strip()
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized.rstrip("/")


def app_base(request: Request | None = None) -> str:
    if request is None:
        return ""
    return _normalize_base_path(
        request.scope.get("root_path") or getattr(request.state, "base_path", "")
    )


def static_url(request: Request, path: str) -> str:
    clean_path = path if path.startswith("/") else f"/{path}"
    return f"{app_base(request)}/static{clean_path}"


templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.globals["config"] = config
templates.env.globals["route"] = RouteBuilder.build
templates.env.globals["Names"] = Names
templates.env.globals["sys"] = config.get("system", {})
templates.env.globals["APP_BASE"] = app_base
templates.env.globals["STATIC_URL"] = static_url

async def get_config(request: Request):
    return request.state.sys

async def get_theme(request: Request):
    return getattr(request.state, 'theme', 'system')
