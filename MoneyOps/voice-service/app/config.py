"""
Voice Service Configuration
All settings loaded from environment variables
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )

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
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    #AI GATEWAY
    AI_GATEWAY_URL: str = "http://localhost:8001"  # Changed URL to use port 8001

    #SESSION
    SESSION_TIMEOUT_S: int = 600  # 10 minutes
    MAX_CONVERSATION_HISTORY: int = 10  # messages

    #EXTERNAL APIs
    ASSEMBLYAI_API_KEY: Optional[str] = None  
    CARTESIA_API_KEY: Optional[str] = None  

    #VAD (Voice Activity Detection)
    # min_speech_duration: minimum ms of speech before we consider it real — lower = more sensitive
    VAD_MIN_SPEECH_DURATION: float = 0.1   # seconds — was 0.3, lower picks up speech faster
    # min_silence_duration: how long silence must last before we consider the turn ended
    # Too short (< 0.7s) = cuts users off mid-sentence. Too long (> 1.5s) = feels sluggish.
    VAD_MIN_SILENCE_DURATION: float = 0.8  # seconds — was 0.5, prevents premature end-of-turn
    # activation_threshold: confidence level needed to declare speech activity (0.0–1.0)
    VAD_ACTIVATION_THRESHOLD: float = 0.5  # standard Silero default
    # How long (seconds) the agent waits after end-of-speech before processing
    # This gives the user a chance to complete their sentence
    TURN_DETECTION_DELAY: float = 0.3      # seconds

    # AI Gateway — use a tighter timeout so failures surface quickly
    AI_GATEWAY_TIMEOUT: int = 15  # seconds (was 30)

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "development"
    
settings = Settings()
