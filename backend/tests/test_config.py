import pytest

from app.core.config import ConfigError, Settings, load_settings


def test_a_missing_database_url_stops_startup_and_names_the_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ConfigError, match=r"DATABASE_URL \(missing\)"):
        load_settings(env_file=None)


def test_plain_postgres_urls_get_the_psycopg_driver() -> None:
    # Neon's dashboard hands out postgresql:// URLs; they should work when pasted as they are.
    settings = Settings(
        _env_file=None,
        database_url="postgresql://user:secret@ep-example-pooler.neon.tech/neondb?sslmode=require",
    )

    assert settings.database_url == (
        "postgresql+psycopg://user:secret@ep-example-pooler.neon.tech/neondb?sslmode=require"
    )
