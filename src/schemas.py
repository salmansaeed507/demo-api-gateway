from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    login_token: str
    name: str = Field(min_length=1, max_length=255)
    user_id: int | None = None


class LoginResponse(BaseModel):
    user_id: int
    name: str
    token: str
    last_activity_at: datetime


class SessionResponse(BaseModel):
    user_id: int
    name: str
    last_activity_at: datetime
