"""
Database connection and session management for Galactus.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from .config import db_settings

engine = create_engine(
    f"postgresql+asyncpg://{db_settings.postgres_user}:{db_settings.postgres_password}"
    f"@{db_settings.postgres_host}:{db_settings.postgres_port}/{db_settings.postgres_database}",
    poolclass=QueuePool,
    pool_size=db_settings.pool_size,
    max_overflow=db_settings.max_overflow,
    pool_timeout=db_settings.pool_timeout,
    pool_recycle=db_settings.pool_recycle,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Yields:
        Session: SQLAlchemy database session

    Example:
        with get_db_session() as session:
            result = session.query(MyModel).filter(...).first()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_session_sync() -> Session:
    """
    Get a synchronous database session.

    Returns:
        Session: SQLAlchemy database session
    """
    return SessionLocal()


async def get_async_db_session():
    """
    Get an async database session.

    Note: This requires asyncpg and async SQLAlchemy setup.

    Returns:
        AsyncSession: Async SQLAlchemy database session
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    async_engine = create_async_engine(
        f"postgresql+asyncpg://{db_settings.postgres_user}:{db_settings.postgres_password}"
        f"@{db_settings.postgres_host}:{db_settings.postgres_port}/{db_settings.postgres_database}",
        pool_size=db_settings.pool_size,
        max_overflow=db_settings.max_overflow,
        pool_timeout=db_settings.pool_timeout,
        pool_recycle=db_settings.pool_recycle,
    )

    async_session_factory = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
