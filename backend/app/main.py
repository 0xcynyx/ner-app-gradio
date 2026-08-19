"""Application wiring only, no business rules live here."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.container import Container
from app.settings import Settings

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the container once, optionally paying the model load cost before traffic."""
    settings = Settings.load()
    container = Container.build(settings)
    app.state.container = container
    if settings.warmup and hasattr(container.classifier, "warmup"):
        container.classifier.warmup()
    logger.info("ready with backend=%s", container.classifier.describe()["backend"])
    yield


def create_app() -> FastAPI:
    settings = Settings.load()
    app = FastAPI(
        title="Indonesian NER and PII Studio",
        description="Entity recognition and redaction for Bahasa Indonesia text.",
        version="2.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins(),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    _mount_frontend(app, settings.frontend_dir)
    return app


def _mount_frontend(app: FastAPI, directory: str) -> None:
    """Serve the built React bundle when present, so one container ships both halves."""
    if not os.path.isdir(directory):
        logger.info("frontend directory %s absent, serving api only", directory)
        return
    app.mount("/assets", StaticFiles(directory=os.path.join(directory, "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(os.path.join(directory, "index.html"))


app = create_app()
