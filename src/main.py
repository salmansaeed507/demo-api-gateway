import asyncio
import logging

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from common import s3 as s3_storage

from . import crons
from .auth import CurrentAuth, create_user_with_session, end_session, get_current_user
from .config import settings
from .csa_client import seed_csa_user
from .dependencies import get_db
from .proxy import forward_request
from .schemas import (
    LoginRequest,
    LoginResponse,
    PresignDownloadRequest,
    PresignDownloadResponse,
    PresignUploadRequest,
    PresignUploadResponse,
    SessionResponse,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
)

app = FastAPI(title="API Gateway", version="0.1.0")
crons.init(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def mimic_production_latency(request: Request, call_next):
    if settings.request_delay_seconds > 0:
        await asyncio.sleep(settings.request_delay_seconds)
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.service_name}


@app.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    if body.login_token != settings.login_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login token",
        )

    auth = create_user_with_session(db, body.name, user_id=body.user_id)
    try:
        seed_csa_user(auth.user.id)
    except httpx.HTTPError as exc:
        end_session(auth.token, user_id=auth.user.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to seed support data: {exc}",
        ) from exc

    return LoginResponse(
        user_id=auth.user.id,
        name=auth.user.name,
        token=auth.token,
        last_activity_at=auth.last_activity_at,
    )


@app.post("/logout")
def logout(_auth: CurrentAuth = Depends(get_current_user)):
    return {"status": "ok"}


@app.get("/session", response_model=SessionResponse)
def current_session(auth: CurrentAuth = Depends(get_current_user)):
    return SessionResponse(
        user_id=auth.user.id,
        name=auth.user.name,
        last_activity_at=auth.last_activity_at,
    )


@app.post("/files/presign-upload", response_model=PresignUploadResponse)
def presign_upload(
    body: PresignUploadRequest,
    _auth: CurrentAuth = Depends(get_current_user),
):
    s3_storage.require_s3_configured(settings)
    key = s3_storage.build_object_key(settings, body.filename)
    return PresignUploadResponse(
        key=key,
        upload_url=s3_storage.presign_upload(settings, key, body.content_type),
        download_url=s3_storage.presign_download(settings, key),
        expires_in=settings.s3_presign_expires_seconds,
    )


@app.post("/files/presign-download", response_model=PresignDownloadResponse)
def presign_download(
    body: PresignDownloadRequest,
    _auth: CurrentAuth = Depends(get_current_user),
):
    s3_storage.require_s3_configured(settings)
    s3_storage.assert_key_allowed(settings, body.key)
    return PresignDownloadResponse(
        key=body.key,
        download_url=s3_storage.presign_download(settings, body.key),
        expires_in=settings.s3_presign_expires_seconds,
    )


@app.api_route(
    "/support/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_customer_support(
    request: Request,
    path: str,
    auth: CurrentAuth = Depends(get_current_user),
):
    return await forward_request(
        request,
        settings.customer_support_url,
        path,
        extra_headers={"X-User-Id": str(auth.user.id)},
    )
