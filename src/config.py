from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    service_name: str = "api-gateway"
    login_token: str = "<Add your login token here or .env file>"
    redis_url: str = "redis://localhost:6379/0"
    session_idle_seconds: int = 30
    purge_inactive_sessions_cron: str = "0 */2 * * *" # every 2 hours
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    request_delay_seconds: float = 0.7  # local default; set 0 in production
    lead_qualification_url: str = "http://lead-qualification-system:8000"
    customer_support_url: str = "http://localhost:5071"
    # S3 / S3-compatible (e.g. RustFS) — fill via .env
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_endpoint_url: str = ""  # e.g. http://localhost:9000 for RustFS; empty = AWS
    s3_bucket: str = ""
    s3_key_prefix: str = ""
    s3_presign_expires_seconds: int = 3600


settings = Settings()
