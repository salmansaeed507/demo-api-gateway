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


class PresignUploadRequest(BaseModel):
    content_type: str = Field(min_length=1, max_length=255)
    filename: str | None = Field(default=None, max_length=255)


class PresignDownloadRequest(BaseModel):
    key: str = Field(min_length=1, max_length=1024)


class PresignUploadResponse(BaseModel):
    key: str
    upload_url: str
    download_url: str
    expires_in: int


class PresignDownloadResponse(BaseModel):
    key: str
    download_url: str
    expires_in: int
