"""
Configuration management for AI Gateway
"""
from pathlib import Path
from functools import lru_cache
from typing import Optional

# Load the shared root .env FIRST — before pydantic-settings reads env vars.
# This matches the pattern used by voice-service and ensures LiveKit credentials
# are always present regardless of the CWD when uvicorn is started.
from dotenv import load_dotenv as _load_dotenv
_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
_load_dotenv(dotenv_path=_ROOT_ENV, override=True)

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    
    # Application
    APP_NAME: str = "MoneyOps AI Gateway"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    
    # LLM Providers
    GROQ_API_KEY: str
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # LLM Models
    GROQ_MODEL: str = "llama-3.3-70b-versatile"  
    GROQ_MODEL_COMPLEX: str = "llama-3.3-70b-versatile"  # For complex tasks
    
    # LLM Settings
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 2000
    LLM_TIMEOUT: int = 30
    LLM_MAX_RETRIES: int = 3
    
    # Backend Services
    BACKEND_BASE_URL: str = "http://localhost:8000"
    BACKEND_TIMEOUT: int = 30
    # Shared secret for service-to-service auth (AI-Gateway → Spring Boot backend)
    INTERNAL_SERVICE_TOKEN: str = "moneyops-internal-ai-gateway-service-secret-2024"

    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_TLS: bool = False  # Set True for Upstash / cloud Redis
    
    # Cache TTL (seconds)
    CACHE_TTL_SHORT: int = 300  # 5 minutes
    CACHE_TTL_MEDIUM: int = 1800  # 30 minutes
    CACHE_TTL_LONG: int = 3600  # 1 hour
    
    # Security
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Conversation Memory
    MAX_CONVERSATION_HISTORY: int = 10
    CONVERSATION_TTL: int = 3600  # 1 hour
    
    # Agent Settings
    AGENT_TIMEOUT: int = 60
    MAX_TOOL_ITERATIONS: int = 5
    
    # LiveKit
    LIVEKIT_URL: str = "wss://your-project.livekit.cloud"
    LIVEKIT_API_KEY: Optional[str] = None
    LIVEKIT_API_SECRET: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=str(_ROOT_ENV),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # silently skip VITE_*, MONGODB_URI, etc. from the shared .env
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance
    Returns the same instance on subsequent calls
    """
    return Settings()


def require_groq_key():
    """
    Ensure GROQ_API_KEY is present
    """
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is required")


# Convenience function
settings = get_settings()