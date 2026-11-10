from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    service_name: str = "api-gateway"
    login_token: str = "<Add your login token here or .env file>"
    redis_url: str = "redis://localhost:6379/0"
    session_idle_seconds: int = 30
    purge_inactive_sessions_cron: str = "0 */2 * * *"  # every 2 hours
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    request_delay_seconds: float = 0  # local default; set 0 in production
    lead_qualification_url: str = "http://lead-qualification-system:8000"
    customer_support_url: str = "http://localhost:5071"
    s3_max_upload_bytes: int = 10 * 1024 * 1024

    # New-user notification email (Gmail SMTP; use a Google App Password)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_username: str = ""  # your Gmail address
    smtp_password: str = ""  # 16-char Gmail App Password
    notify_email_to: str = ""  # defaults to smtp_username when empty


settings = Settings()
