"""Конфигурация приложения через переменные окружения.

Используется pydantic-settings для валидации. Все секреты берутся из .env.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    app_secret_key: str = Field(min_length=16)
    app_name: str = "AI Tutor 7"

    # Database
    database_url: str = "postgresql+psycopg2://tutor:tutor@db:5432/tutor"

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Uploads
    upload_dir: str = "/app/uploads"
    max_upload_size_mb: int = 20

    # AI Gateway (Этап 5+)
    ai_base_url: str = "http://localhost:9999/mock"
    ai_api_key: str = "mock-key"
    ai_model: str = "mock-model"
    ai_timeout_seconds: int = 30
    ai_max_retries: int = 2
    ai_max_input_chars: int = 8000

    # Auth
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 60 * 24  # 24 часа
    jwt_refresh_ttl_days: int = 30

    # Rate limit
    rate_limit_ai_per_minute: int = 30
    rate_limit_register_per_hour: int = 5
    rate_limit_login_per_15min: int = 10

    # Sprint 3.6.3: kill switch для AI. user_id через запятую — для этих
    # пользователей AI endpoints возвращают 503 (даже если rate-limit не превышен).
    # Emergency use case: ребёнок попал в AI-loop, родитель нажал кнопку в /admin
    # → admin endpoint добавляет user_id в этот список → AI перестаёт работать.
    # Пустая строка = kill switch выключен (default).
    ai_kill_switch_user_ids: str = ""

    @property
    def ai_kill_switch_user_id_set(self) -> set[int]:
        """Парсит строку ai_kill_switch_user_ids → set[int]."""
        if not self.ai_kill_switch_user_ids:
            return set()
        return {int(x.strip()) for x in self.ai_kill_switch_user_ids.split(",") if x.strip().isdigit()}

    # Sprint 4.3: доверенные прокси (CIDR-список для X-Forwarded-For).
    # По умолчанию — приватные сети. Если пусто, XFF игнорируется.
    trusted_proxies: str = "127.0.0.1/32,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"

    @field_validator("cors_origins")
    @classmethod
    def _strip_cors(cls, v: str) -> str:
        return v.strip()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def trusted_proxies_list(self) -> list[str]:
        return [c.strip() for c in self.trusted_proxies.split(",") if c.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Singleton-доступ к настройкам."""
    return Settings()  # type: ignore[call-arg]