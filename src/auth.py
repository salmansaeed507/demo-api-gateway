import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .csa_client import purge_csa_user
from .dependencies import get_db
from .models import User
from .redis_client import (
    delete_auth_session,
    get_auth_session,
    save_auth_session,
    touch_auth_session,
)


@dataclass
class CurrentAuth:
    user: User
    token: str
    last_activity_at: datetime


def _parse_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() == "bearer" and value:
        return value.strip()
    token = authorization.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    return token


def end_session(token: str, user_id: int | None = None) -> None:
    deleted_user_id = delete_auth_session(token)
    uid = user_id if user_id is not None else deleted_user_id
    if uid is None:
        return
    try:
        purge_csa_user(uid)
    except Exception:
        # Best-effort cleanup; session is already cleared.
        pass


def create_user_with_session(
    db: Session,
    name: str,
    user_id: int | None = None,
) -> CurrentAuth:
    cleaned = name.strip()
    user: User | None = None
    if user_id is not None:
        existing = db.scalar(select(User).where(User.id == user_id))
        if existing is not None and existing.name == cleaned:
            user = existing

    if user is None:
        user = User(name=cleaned)
        db.add(user)
        db.commit()
        db.refresh(user)

    now = datetime.now(timezone.utc)
    token = f"{user.id}.{secrets.token_urlsafe(32)}"
    save_auth_session(token, user_id=user.id, name=user.name, last_activity_at=now)
    return CurrentAuth(user=user, token=token, last_activity_at=now)


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> CurrentAuth:
    token = _parse_bearer_token(authorization)
    if get_auth_session(token) is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    touched = touch_auth_session(token)
    if touched is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    user_id = int(touched["user_id"])
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        end_session(token, user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    activity = datetime.fromisoformat(touched["last_activity_at"])
    return CurrentAuth(user=user, token=token, last_activity_at=activity)
