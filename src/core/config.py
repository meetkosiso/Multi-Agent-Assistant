from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

from .constants import AppSettings, OllamaModels


class Settings(BaseSettings):
    """Application settings loaded from environment + defaults"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    OLLAMA_MODEL: OllamaModels = AppSettings.OLLAMA_MODEL
    OLLAMA_BASE_URL: str = AppSettings.OLLAMA_BASE_URL
    MCP_HOST: str = AppSettings.MCP_HOST
    MCP_PORT: int = AppSettings.MCP_PORT
    MCP_SERVER_URL: str = AppSettings.MCP_SERVER_URL
    API_VERSION: str = AppSettings.API_VERSION

    @property
    def ollama_config(self) -> dict:
        return {
            "model": self.OLLAMA_MODEL.value,
            "base_url": self.OLLAMA_BASE_URL,
        }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
