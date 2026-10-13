"""Settings, read from environment variables.

Locally they come from the `.env` file at the repository root. On Render they are set in the
dashboard, and real environment variables always win over the file.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator, model_validator
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

    # Photos: a folder in development, an S3-compatible bucket (Cloudflare R2) in production.
    storage_backend: Literal["local", "s3"] = "local"
    # Relative paths are relative to the folder the API runs in (backend/).
    storage_local_dir: Path = Path(".storage")
    s3_endpoint_url: str | None = None
    s3_bucket: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    max_upload_mb: int = Field(default=8, ge=1, le=25)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def check_storage(self) -> Settings:
        if self.storage_backend == "s3":
            needed = {
                "S3_ENDPOINT_URL": self.s3_endpoint_url,
                "S3_BUCKET": self.s3_bucket,
                "S3_ACCESS_KEY_ID": self.s3_access_key_id,
                "S3_SECRET_ACCESS_KEY": self.s3_secret_access_key,
            }
            missing = [name for name, value in needed.items() if not value]
            if missing:
                raise ValueError(f"STORAGE_BACKEND=s3 also needs {', '.join(missing)}")
        elif self.is_production:
            # Render's disk is wiped on every deploy, so local photos would vanish.
            raise ValueError("STORAGE_BACKEND must be s3 in production")
        return self

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
            if not item["loc"]:
                # A check across several settings; its message names them.
                problems.append(str(item["msg"]).removeprefix("Value error, "))
                continue
            reason = "missing" if item["type"] == "missing" else "invalid"
            problems.append(f"{str(item['loc'][0]).upper()} ({reason})")
        raise ConfigError(
            f"Can't start: {', '.join(problems)}. For local development, copy .env.example "
            "to .env. In production, set the variable in the host's dashboard."
        ) from None


@lru_cache
def get_settings() -> Settings:
    return load_settings()
