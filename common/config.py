from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    """Base settings shared across services."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "<Add your database URL here or .env file>"
    log_level: str = "INFO"
    service_name: str = "unknown"
