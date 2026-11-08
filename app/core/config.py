from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str  # postgresql+asyncpg://user:pass@host:5432/dbname

    # LLM
    llm_base_url: str
    llm_api_key: SecretStr
    llm_model: str
    llm_connect_timeout: float = 5.0
    llm_read_timeout: float = 60.0
    llm_max_retries: int = 3
    llm_use_fake: bool = False

    # سایت سایت / بک‌اند Spring Boot
    spring_boot_base_url: str = "https://api.beautyboss.ir"
    spring_boot_timeout: float = 10.0
    beautyboss_site_url: str = "https://beautyboss.ir"

    chat_history_limit: int = 8
    chat_max_message_chars: int = 2000
    conversations_page_size: int = 20
    conversations_max_page_size: int = 50
    guest_cookie_name: str = "bb_guest_session"
    guest_session_max_age: int = 60 * 60 * 24 * 30 
    guest_session_header: str = "X-Guest-Session-Id"
    enable_listing_tools: bool = True
    enable_knowledge_tools: bool = True
    # پیش‌فرض بسته؛ فرانت واقعی را در env اضافه کن
    cors_origins: str = ""

    # JWT (توکن صادرشده توسط Spring Boot) — سرویس فقط اعتبارسنجی می‌کند
    jwt_algorithm: str = "HS256"
    jwt_jwks_url: str | None = None
    jwt_secret: SecretStr | None = None
    jwt_public_key: str | None = None
    jwt_user_id_claim: str = "sub"
    jwt_role_claim: str | None = None
    jwt_issuer: str | None = None
    jwt_audience: str | None = None

    # محدودیت نرخ و هزینه
    anonymous_rate_per_minute: int = 10
    anonymous_rate_per_day: int = 30
    user_rate_per_minute: int = 20
    user_rate_per_day: int = 200
    daily_token_limit: int = 2_000_000
    trust_proxy_headers: bool = False
    # پیشوند مسیر API؛ اگر سایت اصلی این سرویس را زیر مسیر دیگری mount می‌کند عوضش کن
    api_prefix: str = "/api/v1"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def api_prefix_clean(self) -> str:
        """پیشوند مسیر بدون اسلش آخر (یا رشتهٔ خالی برای ریشه)."""
        prefix = (self.api_prefix or "").strip()
        if prefix in ("", "/"):
            return ""
        return "/" + prefix.strip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
