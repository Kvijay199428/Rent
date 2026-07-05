import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config_service import ConfigService
from app.core.paths import UPLOADS_DIR, STATIC_DIR, ensure_storage_dirs

class StartupManager:
    @staticmethod
    def initialize(app: FastAPI):
        StartupManager.initialize_storage()
        StartupManager.initialize_config()
        StartupManager.mount_static(app)
        StartupManager.register_middlewares(app)
        StartupManager.register_events(app)

    @staticmethod
    def initialize_storage():
        ensure_storage_dirs()

    @staticmethod
    def initialize_config():
        ConfigService().initialize()

    @staticmethod
    def mount_static(app: FastAPI):
        if not os.path.isdir(STATIC_DIR):
            raise RuntimeError(f"Static asset directory not found: {STATIC_DIR}")
        app.mount("/static/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @staticmethod
    def register_middlewares(app: FastAPI):
        # We will add middlewares here if needed
        pass

    @staticmethod
    def register_events(app: FastAPI):
        @app.on_event("startup")
        async def startup_event():
            print("==================================================")
            print("  Rent Receipt System Initialization Complete")
            print("==================================================")
            print("Registered Routes:")
            print(f"{'METHOD':<10} | {'PATH':<40} | {'NAME':<35} | {'TAGS'}")
            print("-" * 100)
            for route in app.routes:
                if hasattr(route, 'methods'):
                    methods = ",".join(route.methods)
                    name = getattr(route, 'name', 'N/A')
                    tags = getattr(route, 'tags', [])
                    print(f"{methods:<10} | {route.path:<40} | {name:<35} | {tags}")
            print("==================================================")
