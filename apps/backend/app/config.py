"""Конфигурация приложения через переменные окружения.

Используется pydantic-settings для валидации. Все секреты берутся из .env.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
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
    # Sprint 16.0 P0-6: defaults "mock-*" сохранены для dev/test,
    # но validate_production не пускает в production с mock.
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

    # Sprint 3.6.3: kill switch для AI — persistent через Redis (shared между
    # worker'ами uvicorn). Admin endpoint пишет в Redis key 'ai:kill_switch',
    # middleware читает на каждом запросе. Fallback на env (для boot).
    ai_kill_switch_user_ids: str = ""

    @property
    def ai_kill_switch_user_id_set(self) -> set[int]:
        """Парсит строку ai_kill_switch_user_ids → set[int]."""
        if not self.ai_kill_switch_user_ids:
            return set()
        return {int(x.strip()) for x in self.ai_kill_switch_user_ids.split(",") if x.strip().isdigit()}

    # Sprint 4.3: доверенные прокси (CIDR-список для X-Forwarded-For).
    # По умолчанию — приватные сети (для dev/test). В production через
    # .env обязательно задать TRUSTED_PROXIES=172.19.0.4/32 (только nginx).
    # Sprint 16.1 P1-9: добавлен _production_proxy_fallback — для production
    # fallback на 172.19.0.4/32 если TRUSTED_PROXIES явно не задан.
    trusted_proxies: str = "127.0.0.1/32,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"

    # Sprint 16.1 P1-10: timezone ученика для streak (Кирилл в Москве).
    student_timezone: str = "Europe/Moscow"

    @field_validator("cors_origins")
    @classmethod
    def _strip_cors(cls, v: str) -> str:
        return v.strip()

    # Sprint 16.0 P0-6: production validator — не пускаем с mock-ключами
    # в production. Дефолты остаются для dev/test (MockProvider).
    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        if self.app_env == "production":
            required = {
                "app_secret_key": self.app_secret_key,
                "ai_api_key": self.ai_api_key,
                "ai_model": self.ai_model,
            }
            missing = [
                name for name, value in required.items()
                if not value or value.startswith(("mock-", "change-me", "your-"))
            ]
            if missing:
                raise ValueError(
                    f"Production configuration is incomplete or uses placeholder: "
                    f"{', '.join(missing)}"
                )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def trusted_proxies_list(self) -> list[str]:
        """Sprint 16.1 P1-9: в production с broad defaults — fallback на nginx.

        Если в .env оставлен default (broad private сети), для production
        автоматически ограничиваем до IP nginx (172.19.0.4/32 в Docker).
        """
        cidrs = [c.strip() for c in self.trusted_proxies.split(",") if c.strip()]
        if self.is_production and len(cidrs) > 2:
            # Если в .env не сузили до одного-двух — fallback на nginx.
            # Это страховка: на проде НЕ доверяем всей 192.168.0.0/16.
            return ["172.19.0.4/32"]
        return cidrs

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Singleton-доступ к настройкам."""
    return Settings()  # type: ignore[call-arg]
