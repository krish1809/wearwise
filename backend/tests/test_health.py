from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import __version__
from app.core.db import get_session


def test_health_reports_api_and_database_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__, "database": "ok"}


def test_health_reports_an_unreachable_database(app: FastAPI, client: TestClient) -> None:
    # Nothing listens on port 1, so the query fails straight away.
    unreachable = create_engine("postgresql+psycopg://nobody:nothing@127.0.0.1:1/none")

    def broken_session() -> Iterator[Session]:
        with Session(unreachable) as session:
            yield session

    app.dependency_overrides[get_session] = broken_session

    response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "version": __version__, "database": "error"}
