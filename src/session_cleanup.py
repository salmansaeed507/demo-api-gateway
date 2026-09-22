import logging

from sqlalchemy import select

from common.db import create_session_factory

from .config import settings
from .csa_client import purge_csa_user
from .models import User
from .redis_client import list_active_session_user_ids

logger = logging.getLogger(__name__)

_session_factory = create_session_factory(settings.database_url)


def purge_inactive_sessions() -> None:
    """Purge CSA DB data for users with no active Redis session."""
    active_user_ids = list_active_session_user_ids()
    db = _session_factory()
    try:
        users = list(db.scalars(select(User)).all())
        purged = 0
        for user in users:
            if user.id in active_user_ids:
                continue
            try:
                purge_csa_user(user.id)
                purged += 1
            except Exception:
                logger.exception(
                    "Failed to purge inactive session data for user_id=%s",
                    user.id,
                )
        logger.info(
            "purge_inactive_sessions: active=%s checked=%s purged=%s",
            len(active_user_ids),
            len(users),
            purged,
        )
    finally:
        db.close()
