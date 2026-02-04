"""
Configuration management for AI Gateway
"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


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
    GROQ_MODEL: str = "groq/compound"  
    GROQ_MODEL_COMPLEX: str = "groq/compound"  # For complex tasks
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"  # Backup
    
    # LLM Settings
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 2000
    LLM_TIMEOUT: int = 30
    LLM_MAX_RETRIES: int = 3
    
    # Backend Services
    BACKEND_BASE_URL: str = "http://localhost:8000"
    BACKEND_TIMEOUT: int = 30
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance
    Returns the same instance on subsequent calls
    """
    return Settings()


# Convenience function
settings = get_settings()