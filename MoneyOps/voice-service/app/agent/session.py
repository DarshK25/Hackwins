"""Session management for voice agents."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any , Optional
import uuid
from datetime import datetime, timedelta

from app.utils.logger import get_logger
logger = get_logger(__name__)

@dataclass
class ConversationTurn:
    #single conversation turn
    role : str  # 'user' or 'agent'
    text : str
    timestamp : datetime
    intent : Optional[str] = None

@dataclass
class VoiceSession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id:Optional[str] = None
    ord_id : Optional[str] = None
    started_at:datetime = field(default_factory=datetime.now)
    last_active_at:datetime = field(default_factory=datetime.now)
    conversation_history: List[ConversationTurn] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_turn(self, role: str, text: str, intent: Optional[str] = None):
        """Add a conversation turn with deduplication."""
        if self.conversation_history:
            last_turn = self.conversation_history[-1]
            if last_turn.text == text and last_turn.role == role:
                return
            
        turn = ConversationTurn(
            role=role,
            text=text,
            timestamp=datetime.now(),
            intent=intent
        )

        self.conversation_history.append(turn)
        self.last_active_at = datetime.now()

        from app.config import settings
        max_history = settings.MAX_CONVERSATION_HISTORY
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]

    def get_recent_context(self , max_turns: int = 5)->List[Dict]:
        recent = self.conversation_history[-max_turns:]
        return [
            {
                "role": turn.role,
                "text": turn.text,
                "timestamp": turn.timestamp.isoformat(),
                "intent": turn.intent
            }
            for turn in recent
        ]

    def is_expired(self , timeout_seconds: int = 600)-> bool:
        elapsed = datetime.now() - self.last_active_at
        return elapsed > timedelta(seconds=timeout_seconds)
    
    class SessionManager:
        """Manages voice sessions"""

        def __init__(self):
            self.sessions: Dict[str, VoiceSession] = {}

        def create_session(
                self,
                user_id: Optional[str] = None,
                ord_id: Optional[str] = None,
        )   ->  VoiceSession: 
            session = VoiceSession(user_id=user_id, ord_id=ord_id)
            self.sessions[session.session_id] = session
            
            logger.info(
            "session_created",
            session_id=session.session_id,
            user_id=user_id,
        )
            return session
        
        def get_session(self, session_id: str) -> Optional[VoiceSession]: 
            return self.sessions.get(session_id)
        
        def cleanup_expired_sessions(self, timeout_seconds:int = 600):
            expired = [
                sid for sid , session in self.sessions.items()
                if session.is_expired(timeout_seconds)
            ]
            for sid in expired:
                del self.sessions[sid]
                logger.info("expired_session_removed", session_id=sid)

            return len(expired)
        
session_manager = VoiceSession.SessionManager()