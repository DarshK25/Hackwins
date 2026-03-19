import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.models.draft import InvoiceDraft

class VoiceSession(BaseModel):
    session_id: str
    user_id: str
    org_id: str
    business_id: Optional[int] = 1
    invoice_draft: Optional[InvoiceDraft] = None
    client_draft: Optional[Dict[str, Any]] = None
    locked_intent: Optional[str] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)
    last_active: float = Field(default_factory=time.time)
    onboarding_verified: bool = False
    dialog_pending: bool = False
    dialog_id: Optional[str] = None

    def mark_active(self):
        self.last_active = time.time()

class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, VoiceSession] = {}
        self._ttl = 600

    def get_session(self, session_id: str, user_id: str = "unknown", org_id: str = "unknown") -> VoiceSession:
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.mark_active()
            return session
        
        session = VoiceSession(session_id=session_id, user_id=user_id, org_id=org_id)
        self._sessions[session_id] = session
        return session

    def save_session(self, session: VoiceSession):
        self._sessions[session.session_id] = session

    def add_turn(self, session_id: str, role: str, content: str, intent: str = None):
        if session_id in self._sessions:
            self._sessions[session_id].history.append({
                "role": role,
                "content": content,
                "intent": intent,
                "timestamp": time.time()
            })

    def cleanup(self):
        now = time.time()
        expired = [k for k, v in self._sessions.items() if now - v.last_active > self._ttl]
        for k in expired:
            self._sessions.pop(k, None)

session_manager = SessionManager()
