from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from common.config import BaseAppSettings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for shared models."""


def create_db_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True)


def create_session_factory(database_url: str):
    engine = create_db_engine(database_url)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session(settings: BaseAppSettings) -> Generator[Session, None, None]:
    """Yield a database session and close it when done."""
    session_factory = create_session_factory(settings.database_url)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
