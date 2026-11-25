"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from emojilens_api import __version__
from emojilens_api.config import Settings, get_settings
from emojilens_api.db import make_engine, make_sessionmaker
from emojilens_api.errors import install_error_handlers
from emojilens_api.routers import (
    annotation,
    consistency,
    dashboard,
    datasets,
    experiments,
    guard,
    model_registry,
    multilingual,
    multimodal,
    reports,
    system,
    transforms,
    unicode,
)
from emojilens_api.services.experiments import ExperimentWorker, mark_interrupted
from emojilens_core.models import select_device
from emojilens_core.models.catalog import default_registry

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            interrupted = mark_interrupted(app.state.sessionmaker)
        except OperationalError:
            # Schema not migrated yet: /ready reports this; nothing can have been running.
            interrupted = 0
        if interrupted:
            logging.getLogger("emojilens").warning(
                "%d experiment(s) marked interrupted", interrupted
            )
        if settings.run_worker:
            app.state.worker.start()
        yield
        app.state.worker.stop()
        app.state.registry.unload_all()

    app = FastAPI(
        lifespan=lifespan,
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
    choice = select_device(settings.device)
    app.state.registry = default_registry(
        device=choice.device,
        max_loaded=settings.max_loaded_models,
        pins_path=Path(settings.model_pins_path),
    )
    app.state.device_reason = choice.reason
    if settings.enable_test_doubles:
        # Automated tests only: never enabled in normal operation.
        from emojilens_core.models.testing import TestDoubleAdapter, make_test_double_config

        app.state.registry.register_adapter("test_double", TestDoubleAdapter)
        app.state.registry.add(make_test_double_config("test-double-all"))
    app.state.artifacts_root = Path(settings.artifacts_dir).resolve()
    app.state.worker = ExperimentWorker(
        app.state.sessionmaker, app.state.registry, artifacts_root=app.state.artifacts_root
    )

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
    app.include_router(model_registry.router, prefix=API_PREFIX)
    app.include_router(experiments.router, prefix=API_PREFIX)
    app.include_router(consistency.router, prefix=API_PREFIX)
    app.include_router(multimodal.router, prefix=API_PREFIX)
    app.include_router(guard.router, prefix=API_PREFIX)
    app.include_router(dashboard.router, prefix=API_PREFIX)
    app.include_router(reports.router, prefix=API_PREFIX)
    return app
