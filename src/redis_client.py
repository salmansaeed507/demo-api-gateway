import json
from datetime import datetime, timezone
from typing import Any

import redis

from .config import settings

_client: redis.Redis | None = None

SESSION_KEY_PREFIX = "session:"
TOKEN_INDEX_PREFIX = "session_token:"


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def session_key(user_id: int, token: str) -> str:
    return f"{SESSION_KEY_PREFIX}{user_id}:{token}"


def token_index_key(token: str) -> str:
    return f"{TOKEN_INDEX_PREFIX}{token}"


def parse_session_key_user_id(key: str) -> int | None:
    """Extract user_id from session:{user_id}:{token} expire events."""
    if not key.startswith(SESSION_KEY_PREFIX) or key.startswith(TOKEN_INDEX_PREFIX):
        return None
    rest = key[len(SESSION_KEY_PREFIX) :]
    user_id_str, sep, _token = rest.partition(":")
    if not sep:
        return None
    try:
        return int(user_id_str)
    except ValueError:
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
    encoded = json.dumps(payload)
    client.setex(session_key(user_id, token), ttl, encoded)
    client.setex(token_index_key(token), ttl, str(user_id))


def get_auth_session(token: str) -> dict[str, Any] | None:
    client = get_redis()
    user_id_raw = client.get(token_index_key(token))
    if not user_id_raw:
        return None
    try:
        user_id = int(user_id_raw)
    except ValueError:
        return None
    raw = client.get(session_key(user_id, token))
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
    user_id_raw = client.get(token_index_key(token))
    if not user_id_raw:
        return None
    try:
        user_id = int(user_id_raw)
    except ValueError:
        return None

    key = session_key(user_id, token)
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
    encoded = json.dumps(data)
    ttl = settings.session_idle_seconds
    client.setex(key, ttl, encoded)
    client.setex(token_index_key(token), ttl, str(user_id))
    return data


def delete_auth_session(token: str) -> int | None:
    """Delete session keys. Returns user_id when known."""
    client = get_redis()
    user_id_raw = client.get(token_index_key(token))
    user_id: int | None = None
    if user_id_raw is not None:
        try:
            user_id = int(user_id_raw)
        except ValueError:
            user_id = None
        if user_id is not None:
            client.delete(session_key(user_id, token))
    client.delete(token_index_key(token))
    return user_id
