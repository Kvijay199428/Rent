# app\app\core\routes_manifest.py

"""
Auto-generated route manifest from shared/routes.json.
Do not edit manually if possible. If you change routes.json, update this file.
"""

class Paths:
    """Legacy path constants. Use Routes class for new code."""
    HOME = "/"
    BILLING = "/billing"
    HISTORY = "/history"
    TENANTS = "/tenants"
    SETTINGS = "/settings"
    ARCHIVE = "/archive"
    BACKUPS = "/backups"
    TENANT = "/tenant"
    PUBLIC = "/t"

class Routes:
    BASEPATH = "/rent"
    HEALTHCHECK = "/health"
    PUBLICLANDING = "/"

    # Static
    STATICUPLOADS = "/static/uploads"
    STATICSTATIC = "/static"
    STATICADMINASSETS = "/admin/assets"
    STATICTENANTASSETS = "/tenant/assets"
    STATICFAVICON = "/admin/favicon.svg"


class Names:
    """Route names for use with request.url_for() and FastAPI name= parameter."""
    # Public
    PUBLICLANDING = "publiclanding"
    HEALTHCHECK = "health_check"
    FAVICON = "favicon"


class Templates:
    """Jinja2 template filenames."""
    ERROR = "error.html"


class Prefixes:
    """URL path prefixes."""
    API = "/api"
    STATIC = "/static"
    UPLOADS = "/static/uploads"
