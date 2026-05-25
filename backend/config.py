"""
Application configuration using pydantic-settings.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""
    database_url: str = ""

    @property
    def database_url_clean(self) -> str:
        import os
        # Fallback order: os.environ DATABASE_URL -> os.environ database_url -> pydantic field
        url = os.environ.get("DATABASE_URL") or os.environ.get("database_url") or self.database_url
        if url and url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    # Redis
    upstash_redis_url: str = ""
    upstash_redis_token: str = ""

    # HuggingFace
    huggingface_api_token: str = ""

    # Replicate
    replicate_api_token: str = ""

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

    # App
    app_name: str = "AI Architect"
    app_version: str = "0.1.0"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000", "https://ai-architect.vercel.app"]
    # Debug secret used by /debug endpoints (set in Railway or .env for one-time operations)
    debug_secret: str = ""
    # OpenRouter debug/mocking flags
    openrouter_mock: bool = False
    openrouter_debug: bool = False

    # ========== Artifact Pipeline ==========
    artifact_storage_path: str = "/tmp/ai-architect-artifacts"
    artifact_storage_backend: str = "local"  # local or r2
    render_queue_redis_url: str = ""

    # Cloudflare R2
    cloudflare_r2_endpoint: str = ""
    cloudflare_r2_access_key: str = ""
    cloudflare_r2_secret_key: str = ""
    cloudflare_r2_bucket: str = "ai-architect-artifacts"
    cloudflare_r2_public_url: str = ""

    # Default output mode
    default_output_mode: str = "fast_preview"

    # Blender worker
    blender_worker_concurrency: int = 2
    blender_worker_poll_interval: float = 1.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
