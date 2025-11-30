# task_flow/config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # General
    app_name: str = "task_flow"
    environment: str = "local"   # or "dev" or "prod"

    # Database
    database_url: str

    # Broker
    broker_url: str = "redis://localhost:6379/0"

    # Metrics / Observability
    enable_metrics: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",           # Load environment variables from .env
        env_prefix="TASKFLOW_",    # Use prefix for all env vars
        extra="ignore",
    )


settings = Settings()
