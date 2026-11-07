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

    # Spring Boot
    spring_boot_base_url: str = "http://localhost:8080"
    spring_boot_timeout: float = 10.0

    chat_history_limit: int = 8
    chat_max_message_chars: int = 8000
    conversations_page_size: int = 20
    conversations_max_page_size: int = 50
    guest_cookie_name: str = "bb_guest_session"
    guest_session_max_age: int = 60 * 60 * 24 * 30 
    user_id_header: str = "X-User-Id"
    guest_session_header: str = "X-Guest-Session-Id"
    enable_listing_tools: bool = False  
    enable_knowledge_tools: bool = True
    cors_origins: str = "http://localhost:4200,http://127.0.0.1:4200,http://localhost:8100,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
