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

    # Photos: a folder in development, an S3-compatible bucket (Backblaze B2) in production,
    # and "none" for the scheduled jobs, which never touch photos (D56).
    storage_backend: Literal["local", "s3", "none"] = "local"
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
    # Tracing of agent runs (docs/AGENTS.md, section 2): "langsmith" sends traces there, and
    # needs its key. Production allows it for the Trend Scout only: the stylist's and the
    # digest's prompts carry wardrobe data.
    agent_tracing: Literal["off", "langsmith"] = "off"
    langsmith_api_key: str | None = None
    # Web search for the Trend Scout (docs/AGENTS.md, section 7): "tavily" needs a key; "fake"
    # serves recorded results, for working offline, and production refuses it.
    search_provider: Literal["off", "fake", "tavily"] = "off"
    search_api_key: str | None = None
    # Search credits a calendar month may use, counted from what each search reports.
    search_monthly_credit_cap: int = Field(default=600, ge=0)
    # Limits on one Trend Scout run; reaching one stops it, keeping what is valid.
    trend_scout_max_queries: int = Field(default=8, ge=1, le=20)
    trend_scout_max_pages: int = Field(default=40, ge=1, le=200)
    trend_scout_max_tokens: int = Field(default=200_000, ge=1_000)
    trend_scout_max_seconds: int = Field(default=600, ge=30)
    # New trends wait for the owner's approval before any digest uses them.
    trends_require_approval: bool = True
    # The most weekly emails one run sends; anyone left over is caught up by the next run.
    digest_batch_cap: int = Field(default=80, ge=1)
    # Email (docs/AGENTS.md, section 7): "console" prints emails, "resend" sends them through
    # Resend (a key and a sender address), "fake" keeps them for tests; production refuses it.
    email_provider: Literal["console", "fake", "resend"] = "console"
    email_api_key: str | None = None
    email_from: str | None = None
    # Until a domain is verified, every email goes only to these addresses (comma-separated).
    # Empty sends to anyone who confirmed, which needs a verified domain (D57).
    email_allowlist: str = ""
    # Below the provider's daily limit (100 on Resend's free plan).
    email_daily_cap: int = Field(default=90, ge=0)
    # Signs unsubscribe and "not for me" links: the same on Render and in GitHub's environment.
    email_link_secret: str | None = None
    # The site's address, for links in emails.
    app_url: str = "http://localhost:3000"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def admins(self) -> frozenset[str]:
        return _addresses(self.admin_emails)

    @property
    def email_allowed(self) -> frozenset[str]:
        """The only addresses email may go to; empty means anyone who confirmed."""
        return _addresses(self.email_allowlist)

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
        elif self.is_production and self.storage_backend == "local":
            # Render's disk is wiped on every deploy, so local photos would vanish. The API
            # also refuses "none" in production (app/main.py); only the jobs use it.
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
        if self.agent_tracing == "langsmith" and not self.langsmith_api_key:
            raise ValueError("AGENT_TRACING=langsmith also needs LANGSMITH_API_KEY")
        if self.search_provider == "tavily" and not self.search_api_key:
            raise ValueError("SEARCH_PROVIDER=tavily also needs SEARCH_API_KEY")
        if self.search_provider == "fake" and self.is_production:
            raise ValueError("SEARCH_PROVIDER=fake isn't allowed in production")
        if self.email_provider == "resend":
            needed = {"EMAIL_API_KEY": self.email_api_key, "EMAIL_FROM": self.email_from}
            missing = [name for name, value in needed.items() if not value]
            if missing:
                raise ValueError(f"EMAIL_PROVIDER=resend also needs {', '.join(missing)}")
        if self.email_provider == "fake" and self.is_production:
            raise ValueError("EMAIL_PROVIDER=fake isn't allowed in production")
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


def _addresses(listed: str) -> frozenset[str]:
    return frozenset(e.strip().lower() for e in listed.split(",") if e.strip())


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
