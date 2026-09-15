from collections.abc import Generator

from sqlalchemy.orm import Session

from common.db import create_session_factory

from .config import settings

_session_factory = create_session_factory(settings.database_url)


def get_db() -> Generator[Session, None, None]:
    db = _session_factory()
    try:
        yield db
    finally:
        db.close()
