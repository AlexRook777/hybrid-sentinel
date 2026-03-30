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

    # Anomaly detection settings
    anomaly_threshold: float = 0.85
    model_warmup_events: int = 1000
    drift_detection_enabled: bool = True
    scoring_queue_max_size: int = 10000
    hst_n_trees: int = 15
    hst_height: int = 6
    hst_window_size: int = 500


settings = Settings()
