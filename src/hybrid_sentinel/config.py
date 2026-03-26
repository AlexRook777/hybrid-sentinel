"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Hybrid Sentinel application settings."""

    model_config = {"env_prefix": "SENTINEL_"}

    app_name: str = "hybrid-sentinel"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000


settings = Settings()
