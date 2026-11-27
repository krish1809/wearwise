import pytest

from app.core.config import ConfigError, Settings, load_settings


def test_a_missing_database_url_stops_startup_and_names_the_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ConfigError, match=r"DATABASE_URL \(missing\)"):
        load_settings(env_file=None)


def test_every_problem_is_named_in_the_one_message(monkeypatch: pytest.MonkeyPatch) -> None:
    # A host's logs show only the first crash, so fixing settings one restart at a time is slow.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("APP_ENV", "staging")

    with pytest.raises(ConfigError) as caught:
        load_settings(env_file=None)

    message = str(caught.value)
    assert "APP_ENV (invalid)" in message
    assert "DATABASE_URL (missing)" in message


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
        ConfigError, match="S3_ENDPOINT_URL, S3_REGION, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY"
    ):
        load_settings(env_file=None)


def test_an_endpoint_pasted_without_https_gets_it() -> None:
    # Backblaze shows the endpoint as a bare host name.
    settings = Settings(
        _env_file=None,
        database_url="postgresql://u:p@localhost/db",
        s3_endpoint_url="s3.eu-central-003.backblazeb2.com",
    )

    assert settings.s3_endpoint_url == "https://s3.eu-central-003.backblazeb2.com"


def test_production_refuses_local_photo_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("STORAGE_BACKEND", "local")

    with pytest.raises(ConfigError, match="STORAGE_BACKEND must be s3 in production"):
        load_settings(env_file=None)


def test_the_scripted_stylist_is_refused_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    for name in (
        "S3_ENDPOINT_URL",
        "S3_REGION",
        "S3_BUCKET",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
    ):
        monkeypatch.setenv(name, "x")
    monkeypatch.setenv("AI_PROVIDER", "fake")

    with pytest.raises(ConfigError, match="AI_PROVIDER=fake isn't allowed in production"):
        load_settings(env_file=None)


def test_the_real_stylist_needs_its_address_key_and_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_PROVIDER", "openai-compatible")
    monkeypatch.setenv("AI_API_KEY", "key")

    with pytest.raises(ConfigError, match="AI_BASE_URL, AI_MODEL_CHAT, AI_MODEL_VISION"):
        load_settings(env_file=None)


def test_a_free_model_needs_no_prices_but_production_needs_https(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in {
        "AI_PROVIDER": "openai-compatible",
        "AI_API_KEY": "key",
        "AI_MODEL_CHAT": "chat-model",
        "AI_MODEL_VISION": "vision-model",
        "AI_BASE_URL": "http://localhost:11434/v1",
    }.items():
        monkeypatch.setenv(name, value)

    local = load_settings(env_file=None)
    assert local.ai_price_input_per_mtok == 0 and local.ai_price_output_per_mtok == 0

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    for name in (
        "S3_ENDPOINT_URL",
        "S3_REGION",
        "S3_BUCKET",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
    ):
        monkeypatch.setenv(name, "x")
    with pytest.raises(ConfigError, match="AI_BASE_URL must start with https://"):
        load_settings(env_file=None)
