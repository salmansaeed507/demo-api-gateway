import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

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


def end_session(token: str) -> None:
    delete_auth_session(token)


def create_user_with_session(db: Session, name: str) -> CurrentAuth:
    user = User(name=name.strip())
    db.add(user)
    db.commit()
    db.refresh(user)

    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)
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
        delete_auth_session(token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    activity = datetime.fromisoformat(touched["last_activity_at"])
    return CurrentAuth(user=user, token=token, last_activity_at=activity)
