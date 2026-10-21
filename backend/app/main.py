"""The FastAPI application. Run with `uvicorn app.main:app`."""

from fastapi import FastAPI
from fastapi.routing import APIRoute

from app import __version__
from app.api.errors import install_error_handlers
from app.api.middleware import RequestContext, SecurityHeaders
from app.api.router import api_router
from app.core.config import get_settings
from app.core.logs import configure_logging


def _operation_id(route: APIRoute) -> str:
    # Short operation names (get_health) keep the generated frontend types readable.
    return route.name


def create_app() -> FastAPI:
    # Read settings now so a missing variable stops startup instead of failing a request later.
    settings = get_settings()
    configure_logging(settings.is_production)
    app = FastAPI(
        title="WearWise API", version=__version__, generate_unique_id_function=_operation_id
    )
    install_error_handlers(app)
    # The last added runs first: headers go on every answer, the 500 included.
    app.add_middleware(RequestContext)
    app.add_middleware(SecurityHeaders)
    app.include_router(api_router)
    return app


app = create_app()
