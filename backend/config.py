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
        from urllib.parse import urlparse, parse_qsl, urlunparse
        # Fallback order: os.environ DATABASE_URL -> os.environ database_url -> pydantic field
        url = os.environ.get("DATABASE_URL") or os.environ.get("database_url") or self.database_url
        if url and url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        
        # Add SSL parameter for Supabase external connections
        if url:
            parsed = urlparse(url)
            query_params = dict(parse_qsl(parsed.query))
            # Add or update sslmode
            query_params['sslmode'] = 'require'
            # Reconstruct URL with updated params
            new_query = "&".join(f"{k}={v}" for k, v in query_params.items())
            url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
        
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
    cors_origins: list[str] = [
        "http://localhost:3000", 
        "https://ai-architect.vercel.app",
        "https://907-bot.github.io",  # GitHub Pages
        "https://907-bot.github.io/AI-Architect",  # GitHub Pages with path
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
