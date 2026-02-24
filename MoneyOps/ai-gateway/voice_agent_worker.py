"""
MoneyOps Voice Agent Worker
============================
Uses LiveKit AgentSession + Groq STT / LLM / TTS (real audio output).
ACTION: commands from the LLM are intercepted in Agent.on_message,
routed to the backend agent_router, and the result is spoken back.
"""
import os
import logging
import json
from pathlib import Path
from dotenv import load_dotenv

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RoomInputOptions,
    WorkerOptions,
    cli,
)
from livekit.plugins import groq, silero

from app.orchestration.agent_router import agent_router
from app.schemas.intents import Intent

# ── Environment ───────────────────────────────────────────────────────────────
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice_agent_worker")


# ── System Prompt ─────────────────────────────────────────────────────────────
VOICE_SYSTEM_PROMPT = """You are MoneyOps AI, a smart financial voice assistant for Indian businesses.
You help with invoices, payments, clients, and finance strategy.
Speak in a warm, professional, concise style. Keep responses under 3 sentences.
Never repeat the user's question back to them.

=== INVOICE CREATION — CONVERSATIONAL DATA COLLECTION ===

When the user wants to create an invoice, collect these fields one at a time:

  REQUIRED:
  1. client_name  — Who is this invoice for?
  2. description  — What service or product?
  3. quantity     — How many units? (default 1)
  4. unit_price   — Price per unit in INR?
  5. total        — Total amount (quantity x unit_price, include any tax)

  OPTIONAL:
  6. due_date     — Payment due date? (default: 14 days from today)
  7. notes        — Any additional notes?

RULES:
- If the user gives multiple fields upfront, absorb them and only ask for what is MISSING.
- Ask ONE question at a time.
- Before firing the action, ALWAYS confirm:
  "I'll create an invoice for [client_name] for Rs.[total] for [description], due on [due_date]. Shall I go ahead?"
- Fire the ACTION only after the user confirms (yes / okay / proceed / go ahead / sure).
- If the user says no/cancel/stop, say "Okay, invoice creation cancelled." and do nothing.

=== ACTION COMMANDS (only when user has confirmed) ===

When you need to execute an action, respond with ONLY this on the line — nothing else:

ACTION: INVOICE_CREATE {"client_name": "Acme Corp", "items": [{"description": "Website Design", "quantity": 1, "unit_price": 10000, "amount": 10000}], "subtotal": 10000, "tax": 0, "total": 10000, "due_date": "2026-03-08", "notes": ""}

Other supported actions:
ACTION: BALANCE_CHECK {}
ACTION: INVOICE_QUERY {}
ACTION: PAYMENT_RECORD {"invoice_id": "INV-XYZ", "amount": 5000}
ACTION: BUSINESS_HEALTH_CHECK {}

=== SAMPLE CONVERSATION ===

User: "Create an invoice for Rahul Enterprises for consulting, 20000 rupees"
You:  "Got it! Should the due date be 14 days from today, and any special notes to add?"

User: "Due in 30 days, no notes"
You:  "I'll create an invoice for Rahul Enterprises for Rs.20,000 for consulting, due in 30 days. Shall I go ahead?"

User: "Yes"
You:  ACTION: INVOICE_CREATE {"client_name": "Rahul Enterprises", "items": [{"description": "Consulting", "quantity": 1, "unit_price": 20000, "amount": 20000}], "subtotal": 20000, "tax": 0, "total": 20000, "due_date": "2026-03-24", "notes": ""}

For general questions, respond normally — do NOT fire any ACTION command."""


# ── Agent ─────────────────────────────────────────────────────────────────────
class MoneyOpsVoiceAgent(Agent):
    """
    Intercepts ACTION: commands from the LLM before they reach TTS.
    Routes them to the backend agent_router and speaks the result instead.
    """

    def __init__(self, session_context: dict):
        super().__init__(instructions=VOICE_SYSTEM_PROMPT)
        self._session_context = session_context

    async def on_message(self, session: AgentSession, message: str) -> str:
        stripped = message.strip()

        if stripped.startswith("ACTION:"):
            logger.info(f"ACTION intercepted: {stripped}")
            try:
                parts = stripped.split(" ", 2)
                if len(parts) >= 2:
                    intent_str = parts[1]
                    json_str = parts[2] if len(parts) > 2 else "{}"

                    intent = Intent(intent_str)
                    entities = json.loads(json_str)

                    context = {
                        "channel": "voice",
                        "org_id": self._session_context.get("org_id"),
                        "user_id": self._session_context.get("user_id"),
                    }
                    # Allow LLM to override context values
                    context["org_id"] = entities.pop("org_id", None) or context["org_id"]
                    context["user_id"] = entities.pop("user_id", None) or context["user_id"]

                    logger.info(
                        f"Routing -> {intent} | "
                        f"org={context['org_id']} user={context['user_id']}"
                    )
                    response = await agent_router.route(
                        intent=intent,
                        entities=entities,
                        context=context,
                    )

                    result_text = response.message
                    logger.info(f"Action result: {result_text}")
                    return result_text
                else:
                    return "I tried to execute that action but the format was incorrect."
            except Exception as e:
                logger.error(f"Action failed: {e}", exc_info=True)
                return f"I encountered an error while processing that: {str(e)}"

        logger.info(f"Agent says: {stripped}")
        return message


# ── Entrypoint ────────────────────────────────────────────────────────────────
async def entrypoint(ctx: JobContext):
    logger.info(f"Voice agent joining room: {ctx.room.name}")
    await ctx.connect()

    # Read user_id / org_id from participant metadata (set during token generation)
    session_context = {"org_id": None, "user_id": None}

    for identity, participant in ctx.room.remote_participants.items():
        meta_str = participant.metadata or "{}"
        try:
            meta_dict = json.loads(meta_str)
            session_context["org_id"] = meta_dict.get("org_id")
            session_context["user_id"] = meta_dict.get("user_id") or identity
        except Exception:
            session_context["user_id"] = identity
        break  # only care about the first participant

    logger.info(
        f"Session context -> user_id={session_context['user_id']} "
        f"org_id={session_context['org_id']}"
    )

    session = AgentSession(
        stt=groq.STT(model="whisper-large-v3-turbo"),
        llm=groq.LLM(model="llama-3.3-70b-versatile"),
        tts=groq.TTS(),        # Real Groq TTS — actual voice output
        vad=silero.VAD.load(),
    )

    await session.start(
        room=ctx.room,
        agent=MoneyOpsVoiceAgent(session_context=session_context),
        room_input_options=RoomInputOptions(),
    )

    await session.generate_reply(
        instructions="Greet the user warmly in one short sentence. Introduce yourself as MoneyOps AI and mention you can help with invoices, payments, and financial queries."
    )
    logger.info("Voice agent is live — listening for commands")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
