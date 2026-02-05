"""
LiveKit Voice Agent - Main Entrypoint
WORKING VERSION with Groq LLM
"""
import os
from typing import Any
from dotenv import load_dotenv

from livekit.agents import (
    AgentServer,
    AgentSession,
    Agent,
    JobContext,
    room_io,
    llm,
)
from livekit.plugins import silero, groq, cartesia , assemblyai

from app.agent.instructions import get_dynamic_instructions
from app.agent.session import session_manager
from app.agent.adapters import ai_gateway_client
from app.config import settings
from app.utils.logger import setup_logging, get_logger

# Load environment
load_dotenv()

# Setup logging
setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


# ==================== AGENT ====================
class LedgerTalkAgent(Agent):
    """
    Voice-first financial assistant
    
    IMPORTANT: Tools are passed to LLM, not to Agent
    """
    
    def __init__(self, user_context: dict = None):
        self.user_context = user_context or {}
        self.session_id = None
        
        # Get dynamic instructions
        instructions = get_dynamic_instructions(self.user_context)
        
        # Initialize agent WITHOUT tools
        super().__init__(instructions=instructions)
    
    async def on_function_call(self, function_name: str, arguments: dict, call_context: Any) -> str:
        """
        Handle function calls from LLM
        THIS is where we call AI Gateway
        """
        logger.info(
            "function_called",
            function=function_name,
            args=arguments,
        )
        
        if function_name == "process_financial_request":
            # Call AI Gateway
            user_request = arguments.get("user_request", "")
            
            response = await ai_gateway_client.process_voice_input(
                text=user_request,
                user_id=self.user_context.get("user_id", "unknown"),
                org_id=self.user_context.get("org_id", "unknown"),
                session_id=self.session_id or "unknown",
            )
            
            return response.get("response_text", "Done.")
        
        return "I couldn't process that request."


# ==================== SERVER ====================
server = AgentServer()


@server.rtc_session()
async def voice_session(ctx: JobContext):
    """
    Voice session handler
    Called for each new LiveKit room connection
    """
    # Extract user context from room metadata
    user_context = _extract_user_context(ctx)
    
    logger.info(
        "voice_session_starting",
        user_id=user_context.get("user_id"),
        room_name=ctx.room.name,
    )
    
    # Create agent
    agent = LedgerTalkAgent(user_context=user_context)
    
    # Generate session ID
    import uuid
    agent.session_id = str(uuid.uuid4())
    
    # Create agent session
    session = AgentSession(
        # STT: AssemblyAI for speech recognition
        stt=assemblyai.STT(
            api_key=settings.ASSEMBLYAI_API_KEY,
        ),
        
        # LLM: Groq (tools handled via agent.on_function_call)
        llm=groq.LLM(
            model=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=0.3,
        ),
        
        # TTS: Cartesia for voice generation
        tts=cartesia.TTS(api_key=settings.CARTESIA_API_KEY),
        
        # VAD: Silero for voice activity detection
        vad=silero.VAD.load(
            min_speech_duration=settings.VAD_MIN_SPEECH_DURATION,
            min_silence_duration=settings.VAD_MIN_SILENCE_DURATION,
        ),
    )
    
    # Start session
    await session.start(
        room=ctx.room,
        agent=agent,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions()
        ),
    )
    
    # Add STT event logging for debugging
    @session.on("user_speech_committed")
    def on_user_speech(msg):
        logger.info(
            "user_speech_recognized",
            text=msg.text,
            session_id=agent.session_id,
        )
    
    @session.on("agent_speech_committed")
    def on_agent_speech(msg):
        logger.info(
            "agent_response",
            text=msg.text,
            session_id=agent.session_id,
        )
    
    logger.info("voice_session_started", session_id=agent.session_id)


def _extract_user_context(ctx: JobContext) -> dict:
    """Extract user context from LiveKit room metadata"""
    metadata = ctx.room.metadata or {}
    
    if isinstance(metadata, str):
        import json
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    
    return {
        "user_id": metadata.get("user_id", "unknown"),
        "org_id": metadata.get("org_id", "unknown"),
        "user_name": metadata.get("user_name", "User"),
        "business_name": metadata.get("business_name", "your business"),
        "currency": metadata.get("currency", "INR"),
    }


# ==================== MAIN ====================
if __name__ == "__main__":
    from livekit.agents import cli
    
    logger.info(
        "starting_voice_agent",
        app_name=settings.APP_NAME,
        groq_model=settings.GROQ_MODEL,
    )
    
    cli.run_app(server)