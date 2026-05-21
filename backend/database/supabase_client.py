"""
Supabase client initializer.
"""
from supabase import create_client, Client
from backend.config import settings
import structlog

log = structlog.get_logger()

supabase_client: Client = None

try:
    if settings.supabase_url and settings.supabase_service_key:
        supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )
        log.info("supabase_connected")
    else:
        log.warning("supabase_credentials_missing", url=settings.supabase_url)
except Exception as e:
    log.error("supabase_connection_failed", error=str(e))
