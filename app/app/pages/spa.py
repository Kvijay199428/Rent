from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

@router.get("/admin")
@router.get("/admin/{path:path}")
async def serve_admin_app(path: str = ""):
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    return FileResponse("frontend/admin-app/dist/index.html")

@router.get("/t")
@router.get("/t/{path:path}")
async def serve_tenant_app(path: str = ""):
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    return FileResponse("frontend/tenant-app/dist/index.html")
