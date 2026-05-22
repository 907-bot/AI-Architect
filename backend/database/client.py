"""
Database client for Supabase with SQLAlchemy ORM
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import asyncpg
from backend.config import settings
import structlog

log = structlog.get_logger()

# SQLAlchemy engine setup for PostgreSQL
DATABASE_URL = settings.database_url_clean

if not DATABASE_URL:
    log.warning("database_url_missing")
    # Allow app to run without DB (procedural generation doesn't need database)
    DATABASE_URL = ""

# Only create engine if DATABASE_URL exists and is valid
if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        echo=settings.debug,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    engine = None
    SessionLocal = None
    log.warning('database_disabled')


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
