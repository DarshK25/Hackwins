"""
MoneyOps Voice Agent Worker (Integrated)
========================================
Uses LiveKit AgentSession + custom TTS interception to route actions.
"""
import os
import logging
import asyncio
import json
from dotenv import load_dotenv

# Ensure app imports work
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RoomInputOptions,
    WorkerOptions,
    cli,
    tts,
)
from livekit.plugins import groq, silero

# Import Agent Router
from app.orchestration.agent_router import agent_router
from app.schemas.intents import Intent

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice_agent_worker")


# ── Smart TTS Interceptor ─────────────────────────────────────────────────────
class SmartConsoleTTS(tts.TTS):
    def __init__(self):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=16000,
            num_channels=1
        )

    def synthesize(self, text: str):
        # Return an async generator (stream)
        async def stream():
            final_text = text
            
            # 1. Check for ACTION command from LLM
            if text.strip().startswith("ACTION:"):
                logger.info(f"⚡ INTERCEPTED ACTION: {text}")
                try:
                    # Parse command: ACTION: INTENT_NAME {json_entities}
                    # Example: ACTION: INVOICE_CREATE {"amount": 500}
                    parts = text.strip().split(" ", 2)
                    if len(parts) >= 2:
                        intent_str = parts[1]
                        json_str = parts[2] if len(parts) > 2 else "{}"
                        
                        intent = Intent(intent_str)
                        entities = json.loads(json_str)
                        
                        # Execute Action via Router
                        logger.info(f"Routing to Agent: {intent} with {entities}")
                        response = await agent_router.route(
                            intent=intent,
                            entities=entities,
                            context={"channel": "voice"}
                        )
                        
                        final_text = response.message
                        logger.info(f"✅ Action Result: {final_text}")
                    else:
                        final_text = "I tried to execute that action but the command was malformed."
                except Exception as e:
                    logger.error(f"Action failed: {e}")
                    final_text = f"I encountered an error executing that action: {str(e)}"

            # 2. "Speak" the result (Log to console)
            logger.info(f"🗣️ AGENT SAYS: {final_text}")
            
            # Send silent audio frame to keep connection alive
            data = b'\x00' * 1024
            yield tts.SynthesizedAudio(text=final_text, data=data, type=tts.SynthesisEventType.AUDIO)

        return stream()


# ── System Prompt with Action Tools ───────────────────────────────────────────
VOICE_SYSTEM_PROMPT = """You are MoneyOps AI, a financial assistant.
You can help with invoices, payments, and strategy.

CRITICAL INSTRUCTION:
If the user asks to perform a specific action (create invoice, check balance, health check),
you MUST respond in this EXACT format:
ACTION: <INTENT_NAME> <JSON_ENTITIES>

Supported Intents:
- INVOICE_CREATE (requires client_name, amount)
- BUSINESS_HEALTH_CHECK (no entities)
- BALANCE_CHECK (no entities)
- GENERATE_GROWTH_STRATEGIES (intent: GROWTH_STRATEGY)

Example 1:
User: "Create an invoice for Acme Corp for $500"
You: ACTION: INVOICE_CREATE {"client_name": "Acme Corp", "total": 500}

Example 2:
User: "How is my business doing?"
You: ACTION: BUSINESS_HEALTH_CHECK {}

For general chat, just respond normally. KEEP RESPONSES SHORT."""


class MoneyOpsVoiceAgent(Agent):
    def __init__(self):
        super().__init__(instructions=VOICE_SYSTEM_PROMPT)


async def entrypoint(ctx: JobContext):
    logger.info(f"Voice agent joining room: {ctx.room.name}")
    await ctx.connect()

    session = AgentSession(
        stt=groq.STT(model="whisper-large-v3-turbo"),
        llm=groq.LLM(model="llama-3.3-70b-versatile"),
        tts=SmartConsoleTTS(),  # Intercepts actions!
        vad=silero.VAD.load(),
    )

    await session.start(
        room=ctx.room,
        agent=MoneyOpsVoiceAgent(),
        room_input_options=RoomInputOptions(),
    )

    await session.generate_reply(
        instructions="Greet the user short and sweet."
    )
    logger.info("Voice agent active — Listening for 'ACTION:' commands via LLM")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
