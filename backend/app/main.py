"""The FastAPI application. Run with `uvicorn app.main:app`."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute

from app import __version__
from app.agents import checkpoint
from app.api import email_links
from app.api.errors import install_error_handlers
from app.api.middleware import RequestContext, SecurityHeaders
from app.api.router import api_router
from app.core.config import ConfigError, get_settings
from app.core.logs import configure_logging


def _operation_id(route: APIRoute) -> str:
    # Short operation names (get_health) keep the generated frontend types readable.
    return route.name


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    # The stylist's checkpointer opens a small pool on first use.
    checkpoint.close_shared()


def create_app() -> FastAPI:
    # Read settings now so a missing variable stops startup instead of failing a request later.
    settings = get_settings()
    if settings.is_production and settings.storage_backend != "s3":
        # Render's disk is wiped on every deploy; "none" is only for the scheduled jobs.
        raise ConfigError("STORAGE_BACKEND must be s3 in production")
    configure_logging(settings.is_production)
    app = FastAPI(
        title="WearWise API",
        version=__version__,
        generate_unique_id_function=_operation_id,
        lifespan=_lifespan,
    )
    install_error_handlers(app)
    # The last added runs first: headers go on every answer, the 500 included.
    app.add_middleware(RequestContext)
    app.add_middleware(SecurityHeaders)
    app.include_router(api_router)
    # Mail apps' one-click unsubscribe can't send the custom header every other change needs;
    # its signed token guards it instead (D57).
    app.include_router(email_links.one_click)
    return app


app = create_app()
