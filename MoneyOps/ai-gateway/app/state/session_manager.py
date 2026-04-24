import time
import hashlib
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
    expense_draft: Optional[Dict[str, Any]] = None
    locked_intent: Optional[str] = None
    locked_agent_type: Optional[str] = None  # Locks to same agent type for session
    locked_tts_voice: Optional[str] = None  # Locks TTS voice persona to session
    last_processed_input_hash: Optional[str] = None  # For deduplication
    last_input_timestamp: float = 0.0  # Track last input time
    input_processing_lock: bool = False  # Serialize input processing
    history: List[Dict[str, Any]] = Field(default_factory=list)
    last_active: float = Field(default_factory=time.time)
    onboarding_verified: bool = False
    dialog_pending: bool = False
    dialog_id: Optional[str] = None
    orchestrator_conversation_started: bool = False
    focused_client_id: Optional[str] = None
    focused_client_name: Optional[str] = None

    def mark_active(self):
        self.last_active = time.time()
    
    def set_input_processing_lock(self, locked: bool):
        """Acquire or release input processing lock."""
        self.input_processing_lock = locked
    
    def is_input_recently_processed(self, raw_text: str, tolerance_seconds: float = 1.5) -> bool:
        """Check if same input was recently processed (deduplication)."""
        current_time = time.time()
        input_hash = hashlib.md5(raw_text.strip().encode()).hexdigest()
        
        # If same hash and within tolerance window, it's a duplicate
        if (self.last_processed_input_hash == input_hash and 
            current_time - self.last_input_timestamp < tolerance_seconds):
            return True
        
        # Update for next check
        self.last_processed_input_hash = input_hash
        self.last_input_timestamp = current_time
        return False

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

        self._schedule_conversation_start(session)
            
        return session

    def save_session(self, session: VoiceSession):
        self._sessions[session.session_id] = session
        self._schedule_conversation_start(session)

    def add_turn(self, session_id: str, role: str, content: str, intent: str = None):
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.history.append({
                "role": role,
                "content": content,
                "intent": intent,
                "timestamp": time.time()
            })

            self._schedule_conversation_message(session, role, content, intent)

    def cleanup(self):
        now = time.time()
        expired = [k for k, v in self._sessions.items() if now - v.last_active > self._ttl]
        for k in expired:
            self._sessions.pop(k, None)
    
    def lock_agent_for_session(self, session_id: str, agent_type: str) -> None:
        """Lock session to a specific agent type."""
        if session_id in self._sessions:
            self._sessions[session_id].locked_agent_type = agent_type
    
    def lock_tts_voice_for_session(self, session_id: str, voice_id: str) -> None:
        """Lock session to a specific TTS voice."""
        if session_id in self._sessions:
            self._sessions[session_id].locked_tts_voice = voice_id
    
    def get_locked_agent_type(self, session_id: str) -> Optional[str]:
        """Get the locked agent type for this session."""
        if session_id in self._sessions:
            return self._sessions[session_id].locked_agent_type
        return None
    
    def get_locked_tts_voice(self, session_id: str) -> Optional[str]:
        """Get the locked TTS voice for this session."""
        if session_id in self._sessions:
            return self._sessions[session_id].locked_tts_voice
        return None
    
    def is_processing_locked(self, session_id: str) -> bool:
        """Check if this session's input processing is locked."""
        if session_id in self._sessions:
            return self._sessions[session_id].input_processing_lock
        return False
    
    def acquire_processing_lock(self, session_id: str) -> bool:
        """Attempt to acquire input processing lock (atomic-like)."""
        if session_id not in self._sessions:
            return False
        
        # In production, use Redis or database for true atomicity
        session = self._sessions[session_id]
        if not session.input_processing_lock:
            session.input_processing_lock = True
            return True
        return False
    
    def release_processing_lock(self, session_id: str) -> None:
        """Release input processing lock."""
        if session_id in self._sessions:
            self._sessions[session_id].input_processing_lock = False

    def _should_sync_orchestrator(self, session: VoiceSession) -> bool:
        return bool(session.org_id and not session.org_id.startswith("org_"))

    def _schedule_conversation_start(self, session: VoiceSession) -> None:
        if not self._should_sync_orchestrator(session) or session.orchestrator_conversation_started:
            return

        try:
            from app.adapters.orchestrator_adapter import orchestrator_adapter
            import asyncio

            async def _start() -> None:
                started = await orchestrator_adapter.start_conversation(
                    org_id=session.org_id,
                    user_id=session.user_id,
                    session_id=session.session_id,
                )
                if started and session.session_id in self._sessions:
                    self._sessions[session.session_id].orchestrator_conversation_started = True

            asyncio.create_task(_start())
        except Exception:
            pass

    def _schedule_conversation_message(self, session: VoiceSession, role: str, content: str, intent: Optional[str]) -> None:
        if not self._should_sync_orchestrator(session):
            return

        try:
            from app.adapters.orchestrator_adapter import orchestrator_adapter
            import asyncio

            async def _sync_message() -> None:
                current = self._sessions.get(session.session_id, session)
                if not current.orchestrator_conversation_started:
                    started = await orchestrator_adapter.start_conversation(
                        org_id=current.org_id,
                        user_id=current.user_id,
                        session_id=current.session_id,
                    )
                    if started and current.session_id in self._sessions:
                        self._sessions[current.session_id].orchestrator_conversation_started = True

                await orchestrator_adapter.add_message(
                    org_id=current.org_id,
                    user_id=current.user_id,
                    session_id=current.session_id,
                    role=role,
                    content=content,
                    intent=intent,
                )

            asyncio.create_task(_sync_message())
        except Exception:
            pass

session_manager = SessionManager()
