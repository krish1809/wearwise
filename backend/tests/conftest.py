"""Shared test setup.

Tests that need a database use a real Postgres one, `wearwise_test` by default, dropped and
rebuilt from the migrations at the start of each run. Set TEST_DATABASE_URL to use another.
Each test runs inside a transaction that is rolled back afterwards, so tests can't see each
other's data even when the code under test commits.
"""

import os
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.adapters.storage import MemoryStorage

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

# Requests that change data must carry this header (see app/api/deps.py).
CSRF_HEADER = {"X-Requested-With": "test"}


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
    """A fresh database with every migration applied and the reference data from seed/ loaded."""
    from app.services.reference_seed import seed_reference_data

    _recreate_test_database()
    config = Config(BACKEND_DIR / "alembic.ini")
    config.attributes["database_url"] = TEST_DATABASE_URL
    command.upgrade(config, "head")
    seed_engine = create_engine(TEST_DATABASE_URL)
    with Session(seed_engine) as session:
        seed_reference_data(session)
    seed_engine.dispose()
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
def engine(migrated_database: str) -> Iterator[Engine]:
    test_engine = create_engine(migrated_database)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """A session whose work is all rolled back after the test, including its commits."""
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        yield session
        session.close()
        transaction.rollback()


@pytest.fixture
def storage() -> MemoryStorage:
    """Photo storage in memory, so a test can see exactly which files exist."""
    from app.adapters.storage import MemoryStorage

    return MemoryStorage()


@pytest.fixture
def app(db: Session, storage: MemoryStorage) -> Iterator[FastAPI]:
    from app.adapters.storage import get_storage
    from app.core.db import get_session
    from app.main import create_app

    application = create_app()
    application.dependency_overrides[get_session] = lambda: db
    application.dependency_overrides[get_storage] = lambda: storage
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, headers=CSRF_HEADER) as test_client:
        yield test_client


TEST_PASSWORD = "correct horse battery staple"


def _logged_in_client(app: FastAPI, db: Session, email: str) -> Iterator[TestClient]:
    from app.services import auth

    auth.register(db, email=email, password=TEST_PASSWORD, name=None)
    db.commit()
    with TestClient(app, headers=CSRF_HEADER) as test_client:
        response = test_client.post(
            "/api/v1/auth/login", json={"email": email, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        yield test_client


@pytest.fixture
def sam(app: FastAPI, db: Session) -> Iterator[TestClient]:
    """A client logged in as a new account, sam@example.com."""
    yield from _logged_in_client(app, db, "sam@example.com")


@pytest.fixture
def ana(app: FastAPI, db: Session) -> Iterator[TestClient]:
    """A second account, for checking that one person can't see another's data."""
    yield from _logged_in_client(app, db, "ana@example.com")
