"""
Database client for Supabase with SQLAlchemy ORM
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import asyncpg
from backend.config import settings
import structlog
import os

log = structlog.get_logger()

# Engine and session factory initialization.
# Prefer DATABASE_URL (from env or settings.database_url). If missing, fall back to a local
# SQLite file so the app imports cleanly in development. In production (Railway) ensure
# DATABASE_URL is set in environment variables.
DATABASE_URL = settings.database_url_clean or os.environ.get("DATABASE_URL") or ""

if DATABASE_URL:
    try:
        engine = create_engine(
            DATABASE_URL,
            echo=settings.debug,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        log.info("database_engine_created", url=str(engine.url))
    except Exception as e:
        # If engine creation fails, log and fall back to a local SQLite file to avoid import-time crashes
        log.error("database_engine_creation_failed", error=str(e))
        DATABASE_URL = "sqlite:///./dev_fallback.db"
        engine = create_engine(
            DATABASE_URL,
            echo=settings.debug,
            connect_args={"check_same_thread": False},
        )
        log.warning("fallback_to_sqlite", url=DATABASE_URL)
else:
    # No DATABASE_URL provided — fall back to a local sqlite database for development/test
    DATABASE_URL = "sqlite:///./dev_fallback.db"
    engine = create_engine(
        DATABASE_URL,
        echo=settings.debug,
        connect_args={"check_same_thread": False},
    )
    log.warning(
        "no_database_url_found",
        message="DATABASE_URL not set; falling back to local SQLite dev_fallback.db. Set DATABASE_URL in production."
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class DatabaseClient:
    """Manages database connections and operations"""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
        log.info("database_client_initialized", engine=str(engine.url))
    
    def get_db(self) -> Generator[Session, None, None]:
        """Get database session for dependency injection"""
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
        """Initialize database (create tables)"""
        try:
            from backend.database.models import Base
            Base.metadata.create_all(bind=self.engine)
            log.info("database_initialized")
        except Exception as e:
            log.error("database_init_error", error=str(e))
            raise
    
    def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            with self.SessionLocal() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            log.error("database_health_check_failed", error=str(e))
            return False


# Global database client instance
db_client = DatabaseClient()
