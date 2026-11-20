from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

# Automatically locate .env from repo root or working directory
_REPO_ROOT = Path(__file__).resolve().parents[4]
_ENV_FILE_CANDIDATES = [
    str(_REPO_ROOT / ".env"),
    str(Path.cwd() / ".env"),
    str(Path.cwd().parent / ".env"),
    "../../.env",
    ".env",
]
_RESOLVED_ENV = next((f for f in _ENV_FILE_CANDIDATES if Path(f).is_file()), ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_RESOLVED_ENV, extra="ignore")

    database_url: str = "sqlite:///./campusflow-local.db"
    jwt_secret: str = "development-only-change-me-before-use-000000000000"
    jwt_previous_secrets: str = ""
    jwt_issuer: str = "dayleaf-api"
    jwt_audience: str = "dayleaf-web"
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    require_email_verification: bool = False
    web_origin: str = "http://127.0.0.1:3010"
    api_origin: str = "http://localhost:8000"
    llm_provider: str = "gemini"
    llm_api_key: str | None = None
    llm_model: str | None = "gemini-3.5-flash-lite"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    mail_from: str | None = None
    auto_create_schema: bool = True
    log_level: str = "INFO"
    rate_limit_redis_url: str | None = None

    @model_validator(mode="after")
    def validate_signing_secrets(self):
        if len(self.jwt_secret.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 bytes.")
        previous = [secret.strip() for secret in self.jwt_previous_secrets.split(",") if secret.strip()]
        if any(len(secret.encode("utf-8")) < 32 for secret in previous):
            raise ValueError("Every JWT_PREVIOUS_SECRETS key must contain at least 32 bytes.")
        production_origins = (self.web_origin.lower().startswith("https://") or
                              self.api_origin.lower().startswith("https://"))
        if production_origins:
            weak_markers = ("replace", "change-me", "development-only")
            if any(marker in self.jwt_secret.lower() for marker in weak_markers):
                raise ValueError("Production JWT_SECRET must be a unique random value, not a placeholder.")
        return self


settings = Settings()
