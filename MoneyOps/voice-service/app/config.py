"""
Voice Service Configuration
All settings loaded from environment variables
"""
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# Load the global root .env at the workspace root (MoneyOps/.env, one level above MoneyOps/MoneyOps/).
# parents[3] from config.py: voice-service/app → voice-service → MoneyOps/MoneyOps → MoneyOps (outer)
_env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=_env_path, override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Keep pydantic-settings env_file as fallback; absolute path avoids CWD issues
        env_file=str(_env_path),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",   # silently skip MONGODB_URI, VITE_*, BACKEND_PORT, etc.
    )

    # Voice service settings
    APP_NAME: str = "MoneyOps Voice Service"
    PORT: int = 8003
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # LiveKit
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str
    LIVEKIT_URL: str

    # Groq
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # AI Gateway
    AI_GATEWAY_URL: str = "http://localhost:8001"
    AI_GATEWAY_TIMEOUT: int = 15  # seconds — tighter timeout so failures surface quickly

    # Session
    SESSION_TIMEOUT_S: int = 600  # 10 minutes
    MAX_CONVERSATION_HISTORY: int = 10  # messages

    # External APIs
    ASSEMBLYAI_API_KEY: Optional[str] = None
    CARTESIA_API_KEY: Optional[str] = None

    # VAD (Voice Activity Detection) — tuned for natural conversation
    # min_speech_duration LOW  → picks up speech quickly (no missed start-of-turn)
    VAD_MIN_SPEECH_DURATION: float = 0.1   # seconds — lower picks up speech faster
    # min_silence_duration HIGH → doesn't cut off mid-sentence (critical for UX)
    VAD_MIN_SILENCE_DURATION: float = 0.8  # seconds — prevents premature end-of-turn
    # activation_threshold: confidence level needed to declare speech activity (0.0–1.0)
    VAD_ACTIVATION_THRESHOLD: float = 0.5  # standard Silero default
    # How long (seconds) the agent waits after end-of-speech before processing
    TURN_DETECTION_DELAY: float = 0.3      # seconds

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()
