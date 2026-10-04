"""Konfiguracija aplikacije iz env varijabli."""
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Podešavanja iz .env fajla."""

    database_url: str = f"sqlite+aiosqlite:///{(_PROJECT_ROOT / 'app.db').resolve()}"
    debug: bool = False

    # JWT (koristi jak secret u produkciji)
    secret_key: str = "change-me-in-production-use-env"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS - zarezi razdvojena lista domena (npr. "http://localhost:3000,https://app.example.com"), ili "*" za sve
    cors_origins: str = "*"

    # ESB (RabbitMQ) - prazno = isključeno
    rabbitmq_url: str = ""

    # Webhook - tajna za potvrdu/odbijanje rezervacije (opciono)
    webhook_secret: str = ""

    @field_validator("database_url", mode="after")
    @classmethod
    def resolve_database_url(cls, v: str) -> str:
        prefix_rel = "sqlite+aiosqlite:///./"
        if v.startswith(prefix_rel):
            name = v[len(prefix_rel) :]
            path = (_PROJECT_ROOT / name).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite+aiosqlite:///{path}"
        return v

    class Config:
        env_file = str(_PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"


settings = Settings()
