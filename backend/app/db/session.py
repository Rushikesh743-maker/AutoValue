"""
Database engine and session management.
Hardened with connection pooling, automatic ping validation, recycling, and rollback safety.
"""
from typing import Generator
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from ..core.config import settings

logger = logging.getLogger("autovalue.db")

# Build engine configuration based on dialect
engine_kwargs = {}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    engine_kwargs["pool_timeout"] = settings.DB_POOL_TIMEOUT
    engine_kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE
    engine_kwargs["connect_args"] = {"connect_timeout": 5}

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


from fastapi import HTTPException

def get_db() -> Generator[Session, None, None]:
    """
    Dependency for obtaining database sessions per request.
    Guarantees automatic session cleanup and rollback on exception.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        if not isinstance(e, HTTPException):
            logger.error(f"Database session exception occurred, rolled back: {e}")
        raise e
    finally:
        db.close()
