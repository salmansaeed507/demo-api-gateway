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


def parse_session_key_user_id(key: str) -> int | None:
    """Extract user_id from session:{user_id}.{token_secret} keys."""
    if not key.startswith(SESSION_KEY_PREFIX):
        return None
    rest = key[len(SESSION_KEY_PREFIX) :]
    user_id_str, sep, secret = rest.partition(".")
    if not sep or not secret:
        return None
    try:
        return int(user_id_str)
    except ValueError:
        return None


def list_active_session_user_ids() -> set[int]:
    """Return user_ids that currently have a live Redis session key."""
    client = get_redis()
    active: set[int] = set()
    for key in client.scan_iter(match=f"{SESSION_KEY_PREFIX}*"):
        user_id = parse_session_key_user_id(key)
        if user_id is not None:
            active.add(user_id)
    return active


def find_auth_session_for_user(user_id: int) -> tuple[str, dict[str, Any]] | None:
    """Return (token, payload) for an existing Redis session for this user, if any."""
    client = get_redis()
    for key in client.scan_iter(match=f"{SESSION_KEY_PREFIX}{user_id}.*"):
        raw = client.get(key)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict) or "user_id" not in data:
            continue
        token = key[len(SESSION_KEY_PREFIX) :]
        return token, data
    return None


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
    client = get_redis()
    ttl = settings.session_idle_seconds
    client.setex(session_key(token), ttl, json.dumps(payload))


def get_auth_session(token: str) -> dict[str, Any] | None:
    client = get_redis()
    raw = client.get(session_key(token))
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


def delete_auth_session(token: str) -> int | None:
    """Delete session key. Returns user_id when known."""
    client = get_redis()
    key = session_key(token)
    raw = client.get(key)
    user_id: int | None = None
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and "user_id" in data:
                user_id = int(data["user_id"])
        except (json.JSONDecodeError, TypeError, ValueError):
            user_id = None
    client.delete(key)
    return user_id
