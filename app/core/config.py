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


@lru_cache
def get_settings() -> Settings:
    return Settings()