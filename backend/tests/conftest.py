"""Shared test setup.

Tests that need a database use a real Postgres one, `wearwise_test` by default, dropped and
rebuilt from the migrations at the start of each run. Set TEST_DATABASE_URL to use another.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://wearwise:wearwise@localhost:5433/wearwise_test"
)
TEST_DATABASE_NAME = make_url(TEST_DATABASE_URL).database or ""
if not TEST_DATABASE_NAME.endswith("_test"):
    raise RuntimeError(
        f"Refusing to run: tests drop and recreate {TEST_DATABASE_NAME!r}. "
        "Point TEST_DATABASE_URL at a database whose name ends in _test."
    )

# The app reads DATABASE_URL. Point it at the test database before anything imports the app.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _recreate_test_database() -> None:
    server = create_engine(
        make_url(TEST_DATABASE_URL).set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with server.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DATABASE_NAME}" WITH (FORCE)'))
        connection.execute(text(f'CREATE DATABASE "{TEST_DATABASE_NAME}"'))
    server.dispose()


@pytest.fixture(scope="session")
def migrated_database() -> str:
    """An empty database with every migration applied, which also proves the migrations run."""
    _recreate_test_database()
    config = Config(BACKEND_DIR / "alembic.ini")
    config.attributes["database_url"] = TEST_DATABASE_URL
    command.upgrade(config, "head")
    return TEST_DATABASE_URL


@pytest.fixture
def app(migrated_database: str) -> Iterator[FastAPI]:
    from app.main import create_app

    application = create_app()
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
