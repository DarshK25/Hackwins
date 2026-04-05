"""
Voice Processor — simplified single entry point for voice commands.
Delegates all reasoning to the IntelligentAgent.
"""

import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from app.agents.intelligent_agent import intelligent_agent
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VoiceContext:
    session_id: str
    user_id: str
    org_uuid: str
    business_id: Optional[int] = 1
    clerk_org_id: Optional[str] = None
    extracted_entities: List[Dict[str, Any]] = field(default_factory=list)
    raw_text: Optional[str] = None


class VoiceProcessor:
    def __init__(self):
        self.agent = intelligent_agent

    async def process(self, text: str, context: VoiceContext) -> dict:
        logger.info(
            {
                "event": "voice_process_start",
                "session_id": context.session_id,
                "user_id": context.user_id,
                "text": text[:100],
            }
        )

        org_id = context.org_uuid
        if org_id.startswith("org_"):
            from app.adapters.backend_adapter import get_backend_adapter

            backend = get_backend_adapter()
            resp = await backend.get_onboarding_status(context.user_id)
            if resp.success and resp.data:
                data = (
                    resp.data.get("data")
                    if isinstance(resp.data, dict) and "data" in resp.data
                    else resp.data
                )
                resolved = (
                    data.get("orgId")
                    or data.get("orgUuid")
                    or data.get("organizationId")
                )
                if resolved:
                    org_id = resolved

        result = await self.agent.process(
            message=text,
            org_id=org_id,
            user_id=context.user_id,
            business_id=str(context.business_id) if context.business_id else "default",
            session_id=context.session_id,
        )

        logger.info(
            {
                "event": "voice_process_complete",
                "session_id": context.session_id,
                "success": result.get("success", False),
            }
        )

        return result


voice_processor = VoiceProcessor()
