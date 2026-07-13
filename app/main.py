from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import get_settings
from app.graph import build_audit_graph
from app.logging_config import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="GEO Inspector",
        description="Auditoria heurística de prontidão GEO para páginas públicas.",
        version="0.1.0",
    )
    app.state.settings = settings
    app.state.audit_graph = build_audit_graph(settings=settings)
    app.include_router(router)

    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(frontend_dir / "index.html")

    return app


app = create_app()
