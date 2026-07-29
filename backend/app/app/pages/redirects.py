from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["Legacy Redirects"])

legacy_paths = [
    "/dashboard",
    "/billing",
    "/history",
    "/tenants",
    "/settings",
    "/archive",
    "/backups",
    "/login"
]

for path in legacy_paths:
    # Handle GET
    @router.get(path, include_in_schema=False)
    async def legacy_redirect_get(request: Request, path=path):
        return RedirectResponse(url=f"{request.scope.get('root_path', '')}/admin{path}", status_code=301)
    
    # Handle POST
    @router.post(path, include_in_schema=False)
    async def legacy_redirect_post(request: Request, path=path):
        return RedirectResponse(url=f"{request.scope.get('root_path', '')}/admin{path}", status_code=308)

# NOTE: The root / redirect (/ → /admin/) has been removed.
# GET / is now handled by app/pages/landing.py which serves the public landing page.
