"""
Voice Service Configuration
All settings loaded from environment variables
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    #voice service settings 

    APP_NAME: str = "MoneyOps Voice Service"
    PORT: int = 8003  # Changed port to 8003
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    #LIVEKIT
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str
    LIVEKIT_URL: str

    #GROQ
    GROQ_API_KEY: str
    GROQ_MODEL: str = "groq/compound"

    #AI GATEWAY
    AI_GATEWAY_URL: str = "http://localhost:8001"  # Changed URL to use port 8001
    AI_GATEWAY_TIMEOUT: int = 30  # seconds

    #SESSION
    SESSION_TIMEOUT_S: int = 600  # 10 minutes
    MAX_CONVERSATION_HISTORY: int = 10  # messages

    #EXTERNAL APIs
    ASSEMBLYAI_API_KEY: str  # Required for STT
    CARTESIA_API_KEY: str = ""

    #VAD (Voice Activity Detection)
    VAD_MIN_SPEECH_DURATION: float = 0.3  # seconds
    VAD_MIN_SILENCE_DURATION: float = 0.5  # seconds

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()