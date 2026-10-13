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


def test_s3_storage_names_each_missing_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_BUCKET", "photos")

    with pytest.raises(
        ConfigError, match="S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY"
    ):
        load_settings(env_file=None)


def test_production_refuses_local_photo_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("STORAGE_BACKEND", "local")

    with pytest.raises(ConfigError, match="STORAGE_BACKEND must be s3 in production"):
        load_settings(env_file=None)
