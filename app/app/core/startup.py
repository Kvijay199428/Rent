import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config_service import ConfigService
from app.core.paths import UPLOADS_DIR, STATIC_DIR, ensure_storage_dirs
from app.core.db import init_db

class StartupManager:
    @staticmethod
    def initialize(app: FastAPI):
        try:
            StartupManager.initialize_storage()
            StartupManager.initialize_config()
            init_db()
            StartupManager.mount_static(app)
            StartupManager.register_middlewares(app)
            StartupManager.register_events(app)
        except Exception as e:
            # Log the full error but still allow FastAPI to start
            # so the /health endpoint can report the failure
            print(f"CRITICAL STARTUP ERROR: {e}")
            import traceback
            traceback.print_exc()
            raise

    @staticmethod
    def initialize_storage():
        ensure_storage_dirs()

    @staticmethod
    def initialize_config():
        ConfigService().initialize()

    @staticmethod
    def mount_static(app: FastAPI):
        app.mount("/static/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
        if os.path.isdir(STATIC_DIR):
            app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @staticmethod
    def register_middlewares(app: FastAPI):
        # We will add middlewares here if needed
        pass

    @staticmethod
    def register_events(app: FastAPI):
        @app.on_event("startup")
        async def startup_event():
            print("=" * 50)
            print("  Rent Receipt System Initialization Complete")
            print("=" * 50)
            print("Registered Routes:")
            print(f"{'METHOD':<10} | {'PATH':<40} | {'NAME':<35} | {'TAGS'}")
            print("-" * 100)
            for route in app.routes:
                if hasattr(route, 'methods'):
                    methods = ",".join(route.methods)
                    name = getattr(route, 'name', 'N/A')
                    tags = getattr(route, 'tags', [])
                    print(f"{methods:<10} | {route.path:<40} | {name:<35} | {tags}")
            print("=" * 50)
