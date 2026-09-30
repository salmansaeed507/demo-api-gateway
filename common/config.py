from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    """Base settings shared across services."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "<Add your database URL here or .env file>"
    log_level: str = "INFO"
    service_name: str = "unknown"

    # S3 / S3-compatible (e.g. RustFS)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_endpoint_url: str = ""  # e.g. http://localhost:9000 for RustFS; empty = AWS
    s3_bucket: str = ""
    s3_key_prefix: str = ""
    s3_presign_expires_seconds: int = 3600
    s3_public_base_url: str = ""
