"""Settings, read from environment variables.

Locally they come from the `.env` file at the repository root. On Render they are set in the
dashboard, and real environment variables always win over the file.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class ConfigError(RuntimeError):
    """A required setting is missing or invalid."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        # The shared .env also holds frontend and later-milestone variables.
        extra="ignore",
        env_ignore_empty=True,
    )

    app_env: Literal["development", "production"] = "development"
    database_url: str
    # Neon recommends running migrations over a direct connection, not the pooled one.
    # When unset, migrations use database_url.
    migration_database_url: str | None = None
    # A login lasts this long, and is extended while the person keeps using the app.
    session_days: int = Field(default=30, ge=1, le=365)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @field_validator("database_url", "migration_database_url")
    @classmethod
    def use_psycopg_driver(cls, url: str | None) -> str | None:
        # Hosts hand out postgresql:// URLs; SQLAlchemy needs the driver named to use psycopg 3.
        if url is None:
            return None
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url


def load_settings(env_file: Path | None = ROOT_ENV_FILE) -> Settings:
    try:
        return Settings(_env_file=env_file)
    except ValidationError as error:
        problems = []
        for item in error.errors():
            reason = "missing" if item["type"] == "missing" else "invalid"
            problems.append(f"{str(item['loc'][0]).upper()} ({reason})")
        raise ConfigError(
            f"Can't start: {', '.join(problems)}. For local development, copy .env.example "
            "to .env. In production, set the variable in the host's dashboard."
        ) from None


@lru_cache
def get_settings() -> Settings:
    return load_settings()
