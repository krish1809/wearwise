"""GET /api/v1/health: is the API up, and can it read from its database?"""

from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app import __version__
from app.api.deps import SessionDep
from app.services.health import database_is_ready

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    database: Literal["ok", "error"]


@router.get(
    "/health",
    responses={503: {"model": HealthResponse, "description": "The database check failed."}},
)
def get_health(session: SessionDep, response: Response) -> HealthResponse:
    if database_is_ready(session):
        return HealthResponse(status="ok", version=__version__, database="ok")
    # 503 with the same body, so the page can still say which part is down.
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status="degraded", version=__version__, database="error")
