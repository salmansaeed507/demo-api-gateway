import json
from datetime import datetime, timezone
from typing import Any

import redis

from .config import settings

_client: redis.Redis | None = None

SESSION_KEY_PREFIX = "session:"


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def session_key(token: str) -> str:
    return f"{SESSION_KEY_PREFIX}{token}"


def save_auth_session(
    token: str,
    *,
    user_id: int,
    name: str,
    last_activity_at: datetime | None = None,
) -> None:
    activity = last_activity_at or datetime.now(timezone.utc)
    if activity.tzinfo is None:
        activity = activity.replace(tzinfo=timezone.utc)
    payload = {
        "user_id": user_id,
        "name": name,
        "last_activity_at": activity.isoformat(),
    }
    get_redis().setex(
        session_key(token),
        settings.session_idle_seconds,
        json.dumps(payload),
    )


def get_auth_session(token: str) -> dict[str, Any] | None:
    raw = get_redis().get(session_key(token))
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def touch_auth_session(token: str) -> dict[str, Any] | None:
    """Refresh idle TTL and last_activity_at. Returns updated payload or None."""
    client = get_redis()
    key = session_key(token)
    raw = client.get(key)
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "user_id" not in data:
        return None
    data["last_activity_at"] = datetime.now(timezone.utc).isoformat()
    client.setex(key, settings.session_idle_seconds, json.dumps(data))
    return data


def delete_auth_session(token: str) -> None:
    get_redis().delete(session_key(token))
