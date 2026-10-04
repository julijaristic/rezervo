"""Konfiguracija restoran servisa."""
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_RESTAURANT_ROOT = Path(__file__).resolve().parents[1]


def _sqlite_absolute(url: str, base_dir: Path, default_name: str) -> str:
    """Relativni sqlite+aiosqlite:///./file.db → uvek pod base_dir (ne zavisi od cwd)."""
    prefix_rel = "sqlite+aiosqlite:///./"
    if url.startswith(prefix_rel):
        name = url[len(prefix_rel) :]
        path = (base_dir / name).resolve()
    elif url == f"sqlite+aiosqlite:///{default_name}" or url.endswith(f"/{default_name}"):
        path = (base_dir / default_name).resolve()
    else:
        return url
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{path}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_RESTAURANT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = f"sqlite+aiosqlite:///{(_RESTAURANT_ROOT / 'restaurant.db').resolve()}"
    secret_key: str = "restaurant-change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    cors_origins: str = "http://localhost:3001,http://127.0.0.1:3001"

    rabbitmq_url: str = ""
    handled_venue_ids: str = "1"

    rezervo_api_url: str = "http://127.0.0.1:8000"
    rezervo_webhook_secret: str = ""

    @field_validator("database_url", mode="after")
    @classmethod
    def resolve_database_url(cls, v: str) -> str:
        return _sqlite_absolute(v, _RESTAURANT_ROOT, "restaurant.db")

    def parsed_handled_venue_ids(self) -> set[int]:
        ids: set[int] = set()
        for part in self.handled_venue_ids.split(","):
            part = part.strip()
            if part.isdigit():
                ids.add(int(part))
        return ids


settings = Settings()
