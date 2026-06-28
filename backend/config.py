import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "NeuralLens API"
    app_version: str = "2.0.0"
    debug: bool = False

    database_url: str = "sqlite+aiosqlite:///./products.db"
    media_dir: str = "media_storage"
    max_upload_mb: int = 10
    cache_ttl_hours: int = 24

    google_api_key: str = ""
    serpapi_key: str = ""
    huggingfacehub_api_token: str = ""

    # Cloud object detection (Ultralytics HUB Inference API)
    detection_api_url: str = ""
    detection_api_key: str = ""

    # Optional: Local Ollama fallback for Gemini rate limits
    use_ollama: bool = False
    ollama_model: str = "qwen2-vl"
    ollama_base_url: str = "http://localhost:11434/v1"

    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    api_url: str = "http://127.0.0.1:8000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
