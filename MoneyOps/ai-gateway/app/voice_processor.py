"""
Voice processor for the live voice path.
Builds a persistent AgentSession and delegates reasoning to moneyops_agent.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.adapters.backend_adapter import get_backend_adapter, normalize_business_id
from app.agents.moneyops_agent import AgentSession, process as agent_process
from app.config import settings
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

            session = AgentSession(
                session_id=context.session_id,
                user_id=context.user_id,
                org_uuid=context.org_uuid,
                business_id=normalize_business_id(context.business_id),
                clerk_org_id=context.clerk_org_id,
                history=_sanitize_history_messages(list(session_record.history or [])),
                pending_invoice=(
                    dict(session_record.invoice_draft_data)
                    if session_record.invoice_draft_data is not None
                    else (session_record.invoice_draft.model_dump() if session_record.invoice_draft else None)
                ),
                pending_client=(dict(session_record.client_draft) if session_record.client_draft is not None else None),
                pending_expense=dict(session_record.expense_draft or {}) or None,
                pending_payment=dict(session_record.payment_draft or {}) or None,
                verified_team_code=session_record.verified_team_code,
                team_code_attempts=session_record.team_code_attempts,
                business_snapshot=session_record.last_business_profile,
                client_cache=list(session_record.client_cache or []) or None,
                last_tool_called=session_record.last_tool,
                last_client_mentioned=session_record.last_client_mentioned,
                last_invoice_mentioned=session_record.last_invoice_mentioned,
                last_invoice_results=list(session_record.last_invoice_results or []) or None,
                last_client_results=list(session_record.last_client_results or []) or None,
                last_market_query=session_record.last_market_query,
                last_market_results=list(session_record.last_market_results or []) or None,
                last_response_context=session_record.last_response_context,
            )

            org_context = {
                "org_id": context.org_uuid,
                "business_id": normalize_business_id(context.business_id),
            }
            try:
                org_profile = await self.backend.get_my_organization(context.user_id)
                if org_profile.success and org_profile.data:
                    org_context["business"] = org_profile.data
            except Exception as exc:
                logger.warning("voice_org_context_fetch_failed", session_id=context.session_id, error=str(exc))

            result = await agent_process(
                text=text,
                session=session,
                org_context=org_context,
                groq_key=settings.GROQ_API_KEY,
                backend=self.backend,
                is_voice=True,
            )

            session_record.history = _sanitize_history_messages(session.history[-20:])
            session_record.last_tool = session.last_tool_called
            session_record.last_business_profile = session.business_snapshot
            session_record.invoice_draft_data = (
                dict(session.pending_invoice) if session.pending_invoice is not None else None
            )
            session_record.client_draft = (
                dict(session.pending_client) if session.pending_client is not None else None
            )
            session_record.expense_draft = dict(session.pending_expense or {})
            session_record.payment_draft = dict(session.pending_payment or {})
            session_record.verified_team_code = session.verified_team_code
            session_record.team_code_attempts = session.team_code_attempts
            session_record.client_cache = list(session.client_cache or [])
            session_record.last_client_mentioned = session.last_client_mentioned
            session_record.last_invoice_mentioned = session.last_invoice_mentioned
            session_record.last_invoice_results = list(session.last_invoice_results or [])
            session_record.last_client_results = list(session.last_client_results or [])
            session_record.last_market_query = session.last_market_query
            session_record.last_market_results = list(session.last_market_results or [])
            session_record.last_response_context = session.last_response_context
            session_manager.save_session(session_record)

        logger.info(
            "voice_process_complete",
            session_id=context.session_id,
            success=result.get("success", False),
            tool_called=result.get("tool_called"),
        )
        return result


voice_processor = VoiceProcessor()
