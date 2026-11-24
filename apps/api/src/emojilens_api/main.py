"""FastAPI application factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from emojilens_api import __version__
from emojilens_api.config import Settings, get_settings
from emojilens_api.db import make_engine, make_sessionmaker
from emojilens_api.errors import install_error_handlers
from emojilens_api.routers import annotation, datasets, multilingual, system, transforms, unicode

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
    )
    app = FastAPI(
        title="EmojiLens API",
        version=__version__,
        description="Defensive research API for emoji- and Unicode-based adversarial analysis.",
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.engine = make_engine(settings.database_url)
    app.state.sessionmaker = make_sessionmaker(app.state.engine)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    install_error_handlers(app)
    app.include_router(system.router, prefix=API_PREFIX)
    app.include_router(unicode.router, prefix=API_PREFIX)
    app.include_router(multilingual.router, prefix=API_PREFIX)
    app.include_router(datasets.router, prefix=API_PREFIX)
    app.include_router(transforms.router, prefix=API_PREFIX)
    app.include_router(annotation.router, prefix=API_PREFIX)
    return app
