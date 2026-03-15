"""
General Agent — Handles conversational, help, and general queries.
Production-ready: never returns placeholder/stub text.
Routes GENERAL_QUERY and HELP to an LLM-backed response that redirects
the user toward supported MoneyOps capabilities.
"""
from typing import Dict, Any, List, Optional

from app.agents.base_agent import BaseAgent, AgentResponse, ToolDefinition
from app.schemas.intents import Intent, AgentType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GeneralAgent(BaseAgent):
    """
    Handles conversational, ambiguous, and out-of-scope queries.
    Does NOT use external tools.
    Uses LLM (or rule-based fallback) to generate a helpful response
    that redirects the user toward supported MoneyOps capabilities.
    """

    CAPABILITY_SUMMARY = (
        "MoneyOps can help you with: "
        "financial operations (invoices, payments), "
        "executive strategy (health scores, SWOT), "
        "market research (growth strategies), "
        "compliance (GST, tax checks), and "
        "process orchestration (efficiency analysis)."
    )

    GREETING_RESPONSE = (
        "Hello! I'm MoneyOps AI, your financial orchestration partner. "
        "I can assist with operations, strategic growth, and regulatory compliance. "
        "What's on your mind today?"
    )

    HELP_RESPONSE = (
        "Here's how I can help: "
        "Finance: 'Create an invoice' or 'Check my balance'. "
        "Strategy: 'How is my business health?' or 'Give me a SWOT analysis'. "
        "Sales & Market: 'Analyze my sales pipeline' or 'Check market expansion opportunities'. "
        "Compliance: 'What are my GST deadlines?' or 'Am I ready for an audit?'. "
        "Which area should we focus on?"
    )

    def get_agent_type(self) -> AgentType:
        return AgentType.GENERAL_AGENT

    def get_supported_intents(self) -> List[Intent]:
        return [
            Intent.GENERAL_QUERY,
            Intent.HELP,
            Intent.GREETING,
            Intent.CLARIFICATION_REQUEST,
            Intent.FOLLOWUP_QUESTION,
            Intent.FEEDBACK,
            Intent.REPEAT_REQUEST,
            Intent.SLOW_DOWN,
            Intent.SPEED_UP,
            Intent.CONFIRMATION,
            Intent.CANCELLATION,
        ]

    def get_tools(self) -> List[ToolDefinition]:
        return []  # General agent uses no external tools

    def is_production_ready(self) -> bool:
        return True

    async def process(
        self,
        intent: Intent,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Handle general/conversational intents with a real, helpful response.
        Never returns placeholder text or developer jokes.
        """
        user_input = ""
        if context:
            history = context.get("conversation_history", [])
            if history:
                last_user = next(
                    (h["content"] for h in reversed(history) if h.get("role") == "user"),
                    ""
                )
                user_input = last_user

        logger.info(
            "general_agent_processing",
            intent=intent.value,
            user_input_preview=str(user_input)[:80]
        )

        # --- Greeting ---
        if intent == Intent.GREETING:
            return self._build_success_response(
                message=self.GREETING_RESPONSE,
                confidence=1.0
            )

        # --- Help ---
        if intent == Intent.HELP:
            return self._build_success_response(
                message=self.HELP_RESPONSE,
                confidence=1.0
            )

        # --- Repeat / Slow Down / Speed Up ---
        if intent == Intent.REPEAT_REQUEST:
            return self._build_success_response(
                message="I'm sorry, could you please rephrase that? I want to make sure I help you correctly.",
                confidence=1.0
            )

        if intent in (Intent.SLOW_DOWN, Intent.SPEED_UP):
            return self._build_success_response(
                message="Understood! How can I assist you today?",
                confidence=1.0
            )

        # --- Confirmation ---
        if intent == Intent.CONFIRMATION:
            return await self._handle_confirmation(context)

        # --- Cancellation ---
        if intent == Intent.CANCELLATION:
            return self._build_success_response(
                message="No problem, I've cancelled that for you. What else can I help with?",
                confidence=1.0
            )

        # --- GENERAL_QUERY / CLARIFICATION / FEEDBACK / FOLLOWUP ---
        # Try LLM-backed response first
        try:
            response_text = await self._llm_redirect_response(user_input)
        except Exception as e:
            logger.warning("general_agent_llm_failed", error=str(e))
            response_text = self._rule_based_redirect(user_input)

        return self._build_success_response(
            message=response_text,
            confidence=0.9
        )

    async def _handle_confirmation(self, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """User said yes/confirmed. Continue the last pending action."""
        if not context:
            return self._build_success_response("Sure! What's next?")

        history = context.get("conversation_history", [])
        if not history:
            return self._build_success_response("Confirmed! What would you like to do?")

        # Find the last user intent that might need confirmation
        # (Looking back through history to find an intent that supports confirmation)
        last_user_turn = next(
            (h for h in reversed(history) if h.get("role") == "user" and h.get("intent") not in (Intent.CONFIRMATION, Intent.GREETING)),
            None
        )

        if last_user_turn:
            prev_intent = last_user_turn.get("intent")
            # If the last action was something that usually needs confirmation (like invoice creation)
            if prev_intent in ("INVOICE_CREATE", "CLIENT_CREATE", "PAYMENT_RECORD"):
                return AgentResponse(
                    success=True,
                    message="Great, I'm proceeding with that now.",
                    intent=Intent.CONFIRMATION,
                    # We signal to the gateway that we should re-trigger the previous intent
                    # but this time with confirmation=True in context
                    action_result={"continue_intent": prev_intent},
                    agent_type=self.get_agent_type()
                )

        return self._build_success_response(
            message="Got it! What would you like to do next?",
            confidence=1.0
        )

    async def _llm_redirect_response(self, user_input: str) -> str:
        """
        Use Groq simple_completion to generate a context-aware redirect response.
        Raises on failure so the caller can fall back to rule-based.
        """
        from app.llm.groq_client import groq_client

        prompt = f"""You are MoneyOps AI, a financial voice assistant for Indian businesses.

The user said: "{user_input}"

Your job is to:
1. Acknowledge what they said briefly and warmly (1 sentence max)
2. Redirect them to what MoneyOps can actually help with (1 sentence max)

MoneyOps capabilities:
- Creating and managing invoices
- Tracking client payments
- Checking account balance
- Recording transactions
- Listing and managing clients

Rules:
- Keep response under 30 words total
- Be friendly and natural, not robotic
- Do NOT say "BEEP BOOP", "Coming in v2.0", or any placeholder text
- Do NOT pretend you can do things you cannot
- Speak in plain conversational English
- If the input seems like noise or testing, respond: "I didn't quite catch that. You can say things like 'Create an invoice' or 'Check my balance'."

Respond with ONLY the response text, nothing else."""

        text = await groq_client.simple_completion(
            prompt=prompt,
            temperature=0.7,
            max_tokens=80
        )

        text = (text or "").strip()
        if not text or len(text) < 5:
            raise ValueError("Empty LLM response")

        # Safety guard: never return placeholder text
        forbidden = ["beep boop", "coming in v2", "not available yet", "placeholder"]
        if any(f in text.lower() for f in forbidden):
            raise ValueError(f"LLM returned forbidden placeholder text: {text[:50]}")

        return text

    def _rule_based_redirect(self, user_input: str) -> str:
        """
        Rule-based fallback when LLM is unavailable.
        Covers common patterns with a helpful, non-robotic response.
        """
        text_lower = (user_input or "").lower().strip()

        # Noise / unintelligible
        if len(text_lower) < 5 or not any(c.isalpha() for c in text_lower):
            return (
                "I didn't quite catch that. "
                "You can say things like 'Create an invoice' or 'Check my balance'."
            )

        # Questions about what the system can do
        if any(w in text_lower for w in ["what can", "what do", "help", "how do i", "what are"]):
            return self.HELP_RESPONSE

        # Acknowledgements / confirmations that slipped through
        if text_lower in ("okay", "ok", "sure", "alright", "fine", "yes", "yeah", "no", "nope"):
            return (
                "Got it! What would you like to do? "
                "I can create invoices, check your balance, or record payments."
            )

        # Noise / test utterances ("just create a noise", "testing", etc.)
        if any(w in text_lower for w in ["noise", "test", "hello", "hey", "hi"]):
            return (
                "Hello! I'm ready to help. "
                "Try saying 'Create an invoice for Acme Technologies for 50,000 rupees'."
            )

        # Default catch-all
        return (
            "I'm not sure how to help with that. "
            "I can create invoices, track payments, or check your balance. "
            "What would you like to do?"
        )


# Singleton instance
general_agent = GeneralAgent()
