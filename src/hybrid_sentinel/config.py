"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Hybrid Sentinel application settings."""

    model_config = {"env_prefix": "SENTINEL_"}

    app_name: str = "hybrid-sentinel"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    # Stream processing settings
    queue_max_size: int = 10000
    callback_timeout: int = 300  # seconds
    tick_interval: int = 30  # seconds


settings = Settings()
