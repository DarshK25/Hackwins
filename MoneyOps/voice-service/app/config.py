"""
Voice Service Configuration
All settings loaded from environment variables
"""
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


def _resolve_env_path() -> Path:
    """Prefer the voice-service-local .env; fall back to monorepo root if needed."""
    service_env = Path(__file__).resolve().parents[1] / ".env"
    if service_env.exists():
        return service_env

    repo_env = Path(__file__).resolve().parents[2] / ".env"
    return repo_env


_env_path = _resolve_env_path()
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
    TTS_PROVIDER: str = "auto"

    # VAD (Voice Activity Detection) — tuned for natural conversation
    # min_speech_duration LOW  → picks up speech quickly (no missed start-of-turn)
    VAD_MIN_SPEECH_DURATION: float = 0.18  # seconds — avoid triggering on very short noise bursts
    VAD_MIN_SILENCE_DURATION: float = 0.45  # seconds — slightly longer to reduce chopped utterances
    # activation_threshold: confidence level needed to declare speech activity (0.0–1.0)
    VAD_ACTIVATION_THRESHOLD: float = 0.65  # stricter to suppress background noise
    # How long (seconds) the agent waits after end-of-speech before processing
    TURN_DETECTION_DELAY: float = 0.55      # seconds

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()
