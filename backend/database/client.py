"""
Database client for Supabase with SQLAlchemy ORM.
Fully resilient — the app starts and serves procedural endpoints
even when no database is reachable.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Optional
from backend.config import settings
import structlog
import os

log = structlog.get_logger()

DATABASE_URL: str = settings.database_url_clean or os.environ.get("DATABASE_URL") or ""

engine = None
SessionLocal = None

if DATABASE_URL:
    try:
        engine = create_engine(
            DATABASE_URL,
            echo=settings.debug,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5},
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        log.info("database_engine_created", url=DATABASE_URL[:40] + "...")
    except Exception as e:
        log.warning("database_engine_failed", error=str(e))
        engine = None
        SessionLocal = None
else:
    log.warning("database_url_missing — running in no-DB mode (procedural endpoints work fine)")


class DatabaseClient:
    """Manages database connections. All methods degrade gracefully when DB is unavailable."""

    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
        if self.engine:
            log.info("database_client_initialized")
        else:
            log.warning("database_client_no_engine — DB-dependent routes will return 503")

    def get_db(self) -> Generator[Session, None, None]:
        """Dependency-injection session. Raises 503 if DB unavailable."""
        if self.SessionLocal is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=503, detail="Database unavailable")
        db = self.SessionLocal()
        try:
            yield db
        except Exception as e:
            log.error("database_session_error", error=str(e))
            db.rollback()
            raise
        finally:
            db.close()

    async def init_db(self):
        """Create tables. Silently skips when DB is unavailable."""
        if self.engine is None:
            log.warning("init_db_skipped — no database engine")
            return
        try:
            from backend.database.models import Base
            Base.metadata.create_all(bind=self.engine)
            log.info("database_tables_created")
        except Exception as e:
            log.error("database_init_error", error=str(e))
            # Non-fatal — procedural endpoints work without tables

    def health_check(self) -> bool:
        """Returns False (not crash) when DB is unavailable."""
        if self.SessionLocal is None:
            return False
        try:
            with self.SessionLocal() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            log.error("database_health_check_failed", error=str(e))
            return False


# Global singleton
db_client = DatabaseClient()
