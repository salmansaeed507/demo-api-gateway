import logging
import threading
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .auth import CurrentAuth, create_user_with_session, end_session, get_current_user
from .config import settings
from .csa_client import purge_csa_user, seed_csa_user
from .dependencies import get_db
from .proxy import forward_request
from .redis_client import get_redis, parse_session_key_user_id, token_index_key
from .schemas import LoginRequest, LoginResponse, SessionResponse

logger = logging.getLogger(__name__)

_expiry_stop = threading.Event()
_expiry_thread: threading.Thread | None = None


def _session_expiry_loop() -> None:
    """Purge CSA data when a Redis session key expires (idle timeout)."""
    client = get_redis()
    pubsub = client.pubsub()
    try:
        pubsub.psubscribe("__keyevent@*__:expired")
        while not _expiry_stop.is_set():
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message is None:
                continue
            key = message.get("data")
            if not isinstance(key, str):
                continue
            user_id = parse_session_key_user_id(key)
            if user_id is None:
                continue
            parts = key.split(":", 2)
            if len(parts) == 3:
                client.delete(token_index_key(parts[2]))
            try:
                purge_csa_user(user_id)
            except Exception:
                logger.exception("Failed to purge CSA data for expired user_id=%s", user_id)
    finally:
        try:
            pubsub.close()
        except Exception:
            pass


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _expiry_thread
    _expiry_stop.clear()
    _expiry_thread = threading.Thread(
        target=_session_expiry_loop,
        name="session-expiry-listener",
        daemon=True,
    )
    _expiry_thread.start()
    yield
    _expiry_stop.set()
    if _expiry_thread is not None:
        _expiry_thread.join(timeout=2.0)


app = FastAPI(title="API Gateway", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

    auth = create_user_with_session(db, body.name)
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
def logout(auth: CurrentAuth = Depends(get_current_user)):
    end_session(auth.token, user_id=auth.user.id)
    return {"status": "ok"}


@app.get("/session", response_model=SessionResponse)
def current_session(auth: CurrentAuth = Depends(get_current_user)):
    return SessionResponse(
        user_id=auth.user.id,
        name=auth.user.name,
        last_activity_at=auth.last_activity_at,
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
