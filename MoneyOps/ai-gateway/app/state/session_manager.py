import time
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.models.draft import InvoiceDraft
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Conditionally import Redis
try:
    from app.integrations.redis_client import get_redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available for session manager")

class VoiceSession(BaseModel):
    session_id: str
    user_id: str
    org_id: str
    business_id: Optional[int] = 1
    invoice_draft: Optional[InvoiceDraft] = None
    invoice_draft_data: Optional[Dict[str, Any]] = None
    client_draft: Optional[Dict[str, Any]] = None
    expense_draft: Optional[Dict[str, Any]] = None
    payment_draft: Optional[Dict[str, Any]] = None
    locked_intent: Optional[str] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)
    last_active: float = Field(default_factory=time.time)
    onboarding_verified: bool = False
    dialog_pending: bool = False
    dialog_id: Optional[str] = None
    last_tool: Optional[str] = None
    last_business_profile: Optional[Dict[str, Any]] = None
    last_market_query: Optional[str] = None
    last_market_results: List[str] = Field(default_factory=list)
    last_invoice_results: List[Dict[str, Any]] = Field(default_factory=list)
    last_client_results: List[Dict[str, Any]] = Field(default_factory=list)
    verified_team_code: Optional[str] = None
    team_code_attempts: int = 0
    client_cache: List[Dict[str, Any]] = Field(default_factory=list)
    last_client_mentioned: Optional[str] = None
    last_invoice_mentioned: Optional[str] = None
    last_response_context: Optional[str] = None

    def mark_active(self):
        self.last_active = time.time()

class SessionManager:
    def __init__(self):
        self._use_redis = REDIS_AVAILABLE and settings.REDIS_HOST
        if not self._use_redis:
            self._sessions: Dict[str, VoiceSession] = {}
        self._ttl = 600  # 10 minutes

    async def _get_redis_key(self, session_id: str) -> str:
        return f"session:{session_id}"

    async def get_session(
        self,
        session_id: str,
        user_id: str = "unknown",
        org_id: str = "unknown",
        business_id: Optional[int] = None,
    ) -> VoiceSession:
        # Try Redis first if available
        if self._use_redis:
            try:
                r = await get_redis()
                data = await r.get(await self._get_redis_key(session_id))
                if data:
                    session_dict = json.loads(data)
                    session = VoiceSession(**session_dict)
                    # Update fields if provided
                    if user_id and user_id != "unknown":
                        session.user_id = user_id
                    if org_id and org_id != "unknown":
                        session.org_id = org_id
                    if business_id is not None:
                        session.business_id = business_id
                    session.mark_active()
                    return session
            except Exception as e:
                logger.warning("redis_session_get_failed", session_id=session_id, error=str(e))

        # Fallback to in-memory
        if session_id in self._sessions:
            session = self._sessions[session_id]
            if user_id and user_id != "unknown":
                session.user_id = user_id
            if org_id and org_id != "unknown":
                session.org_id = org_id
            if business_id is not None:
                session.business_id = business_id
            session.mark_active()
            return session

        session = VoiceSession(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            business_id=business_id if business_id is not None else 1,
        )
        self._sessions[session_id] = session
        return session

    async def save_session(self, session: VoiceSession):
        if self._use_redis:
            try:
                r = await get_redis()
                key = await self._get_redis_key(session.session_id)
                session.mark_active()
                await r.setex(key, self._ttl, session.model_dump_json())
            except Exception as e:
                logger.warning("redis_session_save_failed", session_id=session.session_id, error=str(e))
        else:
            self._sessions[session.session_id] = session

    async def add_turn(self, session_id: str, role: str, content: str, intent: str = None):
        if self._use_redis:
            try:
                r = await get_redis()
                key = await self._get_redis_key(session_id)
                data = await r.get(key)
                if data:
                    session_dict = json.loads(data)
                    session = VoiceSession(**session_dict)
                    session.history.append({
                        "role": role,
                        "content": content,
                        "intent": intent,
                        "timestamp": time.time()
                    })
                    session.mark_active()
                    await r.setex(key, self._ttl, session.model_dump_json())
            except Exception as e:
                logger.warning("redis_session_add_turn_failed", session_id=session_id, error=str(e))
        elif session_id in self._sessions:
            self._sessions[session_id].history.append({
                "role": role,
                "content": content,
                "intent": intent,
                "timestamp": time.time()
            })

    async def cleanup(self):
        """Clean up expired sessions (for in-memory mode). Redis handles TTL automatically."""
        if not self._use_redis:
            now = time.time()
            expired = [k for k, v in self._sessions.items() if now - v.last_active > self._ttl]
            for k in expired:
                self._sessions.pop(k, None)

session_manager = SessionManager()
