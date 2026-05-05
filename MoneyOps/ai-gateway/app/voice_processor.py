"""
Voice processor for the live voice path.
Uses intelligent_orchestrator for processing voice input.
"""
import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.adapters.backend_adapter import get_backend_adapter, normalize_business_id
from app.agents.intelligent_orchestrator import intelligent_agent
from app.state.session_manager import session_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _sanitize_history_messages(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sanitized: List[Dict[str, Any]] = []
    for msg in history or []:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content")
        if role in {"system", "user", "assistant", "tool"} and content is not None:
            clean = {"role": role, "content": content}
            if role == "tool" and msg.get("tool_call_id"):
                clean["tool_call_id"] = msg.get("tool_call_id")
            sanitized.append(clean)
    return sanitized


@dataclass
class VoiceContext:
    session_id: str
    user_id: str
    org_uuid: str
    business_id: Optional[Any] = 1
    clerk_org_id: Optional[str] = None
    extracted_entities: List[Dict[str, Any]] = field(default_factory=list)
    raw_text: Optional[str] = None
    history: List[Dict[str, Any]] = field(default_factory=list)


class VoiceProcessor:
    def __init__(self) -> None:
        self.backend = get_backend_adapter()
        self._session_locks: Dict[str, asyncio.Lock] = {}

    async def process(self, text: str, context: VoiceContext) -> Dict[str, Any]:
        logger.info(
            "voice_process_start",
            session_id=context.session_id,
            user_id=context.user_id,
            text_preview=text[:100],
        )

        lock = self._session_locks.setdefault(context.session_id, asyncio.Lock())
        async with lock:
            session_record = session_manager.get_session(
                session_id=context.session_id,
                user_id=context.user_id,
                org_id=context.org_uuid,
                business_id=int(normalize_business_id(context.business_id)),
            )

            if context.history:
                session_record.history = _sanitize_history_messages(context.history[-20:])

            # Build context for intelligent_agent
            agent_context = {
                "session_id": context.session_id,
                "org_id": context.org_uuid,
                "org_uuid": context.org_uuid,
                "user_id": context.user_id,
                "business_id": normalize_business_id(context.business_id),
            }

            # Get conversation history
            conversation_history = list(session_record.history or [])

            # Process with intelligent_agent
            result = await intelligent_agent.process(
                user_message=text,
                context=agent_context,
                conversation_history=conversation_history,
            )

            # Update session history
            session_record.history.append({"role": "user", "content": text})
            response_text = result.get("message", "")
            session_record.history.append({"role": "assistant", "content": response_text})

            if len(session_record.history) > 20:
                session_record.history = session_record.history[-20:]

            session_manager.save_session(session_record)

        logger.info(
            "voice_process_complete",
            session_id=context.session_id,
            success=result.get("success", False),
            agent_type=result.get("agent_type"),
        )

        return {
            "response_text": response_text,
            "raw_response": response_text,
            "intent": "INTELLIGENT_QUERY",
            "success": result.get("success", True),
            "session_id": context.session_id,
            "agent_type": result.get("agent_type"),
        }


voice_processor = VoiceProcessor()
