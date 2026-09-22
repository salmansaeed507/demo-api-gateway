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
    lead_qualification_url: str = "http://lead-qualification-system:8000"
    customer_support_url: str = "http://localhost:5071"


settings = Settings()
