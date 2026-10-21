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

    # Photos: a folder in development, an S3-compatible bucket (Backblaze B2) in production.
    storage_backend: Literal["local", "s3"] = "local"
    # Relative paths are relative to the folder the API runs in (backend/).
    storage_local_dir: Path = Path(".storage")
    # Backblaze shows both on the bucket's page: endpoint s3.<region>.backblazeb2.com, and the
    # region is the part between "s3." and ".backblazeb2.com", such as eu-central-003.
    s3_endpoint_url: str | None = None
    s3_region: str | None = None
    s3_bucket: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    max_upload_mb: int = Field(default=8, ge=1, le=25)
    # Forecasts and place search: Open-Meteo, or canned answers for working offline.
    weather_provider: Literal["open-meteo", "fake"] = "open-meteo"
    # Reading a product page someone pastes: "fake" for working offline.
    page_reader: Literal["web", "fake"] = "web"
    # The stylist chat and photo tagging (docs/AI.md): "off" until a key is set; "fake" only
    # in tests. The real provider's prices (US dollars per million tokens) turn token counts
    # into spend, so the daily cap can be enforced.
    ai_provider: Literal["off", "fake", "anthropic"] = "off"
    ai_api_key: str | None = None
    ai_model_chat: str | None = None
    ai_model_vision: str | None = None
    ai_daily_spend_cap_usd: float = Field(default=1.0, ge=0)
    ai_price_input_per_mtok: float = Field(default=0.0, ge=0)
    ai_price_output_per_mtok: float = Field(default=0.0, ge=0)
    # Accounts that may open the owner's page of counts (/admin), comma-separated. Empty: nobody.
    admin_emails: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def admins(self) -> frozenset[str]:
        return frozenset(e.strip().lower() for e in self.admin_emails.split(",") if e.strip())

    @model_validator(mode="after")
    def check_storage(self) -> Settings:
        if self.storage_backend == "s3":
            needed = {
                "S3_ENDPOINT_URL": self.s3_endpoint_url,
                "S3_REGION": self.s3_region,
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

    @model_validator(mode="after")
    def check_ai(self) -> Settings:
        if self.ai_provider == "fake" and self.is_production:
            # Scripted replies are for tests and local work, never for real people.
            raise ValueError("AI_PROVIDER=fake isn't allowed in production")
        if self.ai_provider == "anthropic":
            needed = {
                "AI_API_KEY": self.ai_api_key,
                "AI_MODEL_CHAT": self.ai_model_chat,
                "AI_MODEL_VISION": self.ai_model_vision,
                "AI_PRICE_INPUT_PER_MTOK": self.ai_price_input_per_mtok,
                "AI_PRICE_OUTPUT_PER_MTOK": self.ai_price_output_per_mtok,
            }
            missing = [name for name, value in needed.items() if not value]
            if missing:
                raise ValueError(f"AI_PROVIDER=anthropic also needs {', '.join(missing)}")
        return self

    @field_validator("s3_endpoint_url")
    @classmethod
    def use_https(cls, url: str | None) -> str | None:
        # Backblaze shows the endpoint without https://, and boto3 needs it.
        if url is None or "://" in url:
            return url
        return "https://" + url

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
