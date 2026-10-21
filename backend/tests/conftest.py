"""Shared test setup.

Tests that need a database use a real Postgres one, `wearwise_test` by default, dropped and
rebuilt from the migrations at the start of each run. Set TEST_DATABASE_URL to use another.
Each test runs inside a transaction that is rolled back afterwards, so tests can't see each
other's data even when the code under test commits.
"""

import os
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from langgraph.checkpoint.postgres import PostgresSaver

    from app.adapters.ai.fake import FakeAI
    from app.adapters.email import FakeEmail
    from app.adapters.products import FakePageReader
    from app.adapters.storage import MemoryStorage
    from app.adapters.weather import FakeWeather

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
    """A fresh database with every migration applied, the agents' checkpoint tables made, and
    the reference data from seed/ loaded: what every deploy does."""
    from app.agents.checkpoint import setup
    from app.services.reference_seed import seed_reference_data

    _recreate_test_database()
    config = Config(BACKEND_DIR / "alembic.ini")
    config.attributes["database_url"] = TEST_DATABASE_URL
    command.upgrade(config, "head")
    setup(TEST_DATABASE_URL)
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
def checkpointer(db: Session) -> PostgresSaver:
    """The agents' Postgres checkpointer on the test's own connection, so what it writes is
    rolled back with everything else. Only for graphs whose steps don't use the database:
    LangGraph writes some checkpoints from a background thread, and one connection can't take
    two commands at once (use durable_checkpointer for those)."""
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg import Connection

    connection = cast(Connection[dict[str, Any]], db.connection().connection.driver_connection)
    return PostgresSaver(connection)


@pytest.fixture
def durable_checkpointer(migrated_database: str) -> Iterator[PostgresSaver]:
    """The checkpointer on its own connection, as in production: what it writes is committed
    at once, so it outlasts a rolled-back step. The agents' threads are deleted afterwards,
    except rows the test's own transaction deleted: those stay locked until it rolls back,
    after this, so they're skipped and left for the next run's fresh database."""
    from app.agents.checkpoint import saver
    from app.services.checkpoints import THREAD_TABLES

    with saver(migrated_database) as found:
        yield found
        for table in THREAD_TABLES:
            found.conn.execute(  # type: ignore[union-attr]
                f"DELETE FROM {table} WHERE ctid IN (SELECT ctid FROM {table} WHERE thread_id "
                "LIKE ANY(ARRAY['chat:%', 'scout:%', 'digest:%']) FOR UPDATE SKIP LOCKED)"
            )


@pytest.fixture
def storage() -> MemoryStorage:
    """Photo storage in memory, so a test can see exactly which files exist."""
    from app.adapters.storage import MemoryStorage

    return MemoryStorage()


@pytest.fixture
def weather() -> FakeWeather:
    """A mild fortnight from today and one place, Pune; set `fail` to take the service down."""
    from app.adapters.weather import FakeWeather
    from app.services.wear import today

    return FakeWeather.mild(today())


@pytest.fixture
def pages() -> FakePageReader:
    """No product page is reachable until a test adds it to `found`."""
    from app.adapters.products import FakePageReader

    return FakePageReader()


@pytest.fixture
def ai() -> FakeAI:
    """Scripted replies: tests put turns in `ai.turns` and tags in `ai.tags`."""
    from app.adapters.ai.fake import FakeAI

    return FakeAI()


@pytest.fixture
def outbox() -> FakeEmail:
    """Every email the app sends in the test, kept instead of sent."""
    from app.adapters.email import FakeEmail

    return FakeEmail()


@pytest.fixture
def app(
    db: Session,
    storage: MemoryStorage,
    weather: FakeWeather,
    pages: FakePageReader,
    ai: FakeAI,
    outbox: FakeEmail,
    durable_checkpointer: PostgresSaver,
) -> Iterator[FastAPI]:
    from app.adapters.ai import get_ai
    from app.adapters.email import get_email_sender
    from app.adapters.products import get_page_reader
    from app.adapters.storage import get_storage
    from app.adapters.weather import get_weather
    from app.agents.checkpoint import get_checkpointer
    from app.core.db import get_session
    from app.main import create_app

    application = create_app()
    application.dependency_overrides[get_session] = lambda: db
    application.dependency_overrides[get_storage] = lambda: storage
    application.dependency_overrides[get_weather] = lambda: weather
    application.dependency_overrides[get_page_reader] = lambda: pages
    application.dependency_overrides[get_ai] = lambda: ai
    application.dependency_overrides[get_email_sender] = lambda: outbox
    application.dependency_overrides[get_checkpointer] = lambda: durable_checkpointer
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
