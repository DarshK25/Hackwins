"""
Intent Classification System with business logic and agent routing
Supports both operational and strategic intents
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import time
import re

from app.llm.groq_client import groq_client
from app.schemas.intents import (
    Intent,
    IntentClassification,
    IntentCategory,
    AgentType,
    ComplexityLevel,
    get_intent_requirements,
    get_intent_category,
    ConfidenceLevel,
    get_confidence_level,
)

from app.utils.logger import get_logger

logger = get_logger(__name__)

class IntentClassifier:
    """
    Classifies user input into intents using pattern matching + LLM
    Now supports agent routing and complexity assessment
    """

    def __init__(self):
        self.groq = groq_client
        
        # Pattern-based quick classification (for common cases)
        self.intent_patterns = self._build_intent_patterns()

    def _build_intent_patterns(self) -> Dict[Intent, List[str]]:
        """Build regex patterns for fast intent classification"""
        return {
            # Operational intents
            Intent.INVOICE_CREATE: [
                r"create.*invoice",
                r"new invoice",
                r"generate.*invoice",
                r"make.*invoice",
                r"invoice for",
            ],
            Intent.INVOICE_QUERY: [
                r"show.*invoices?",
                r"list.*invoices?",
                r"find.*invoices?",
                r"get.*invoices?",
                r"which invoices?",
                r"what.*invoices?",
            ],
            Intent.PAYMENT_RECORD: [
                r"record.*payment",
                r"payment.*received",
                r"mark.*paid",
                r"received.*payment",
                r"got.*payment",
            ],
            Intent.BALANCE_CHECK: [
                r"what.*balance",
                r"check.*balance",
                r"current.*balance",
                r"show.*balance",
                r"my balance",
            ],
            Intent.CLIENT_CREATE: [
                r"add.*client",
                r"new.*client",
                r"create.*client",
                r"register.*client",
            ],
            Intent.CLIENT_QUERY: [
                r"show.*clients?",
                r"list.*clients?",
                r"who.*clients?",
                r"find.*client",
            ],

            # Strategic intents
            Intent.BUSINESS_HEALTH_CHECK: [
                r"how.*business.*\b(doing|health|performing)",
                r"business.*\b(health|status|score|performance)",
                r"\b(health|performance).*score",
                r"\b(overall|general).*\b(health|performance|status)",
                r"check.*business",
            ],
            Intent.PROBLEM_DIAGNOSIS: [
                r"why.*revenue.*down",
                r"why.*sales.*down",
                r"why.*\b(down|declined|drop|decrease)\b",
                r"\b(why|what).*wrong",
                r"\b(why|reason).*declining",
                r"\b(reason|cause).*drop",
                r"revenue.*\b(down|dropped|declined).*\%",
                r"sales.*\b(down|dropped|declined).*\%",
            ],
            Intent.SALES_STRATEGY: [
                r"increase.*sales",
                r"improve.*sales",
                r"boost.*revenue",
                r"grow.*sales",
                r"sales.*strategy",
            ],
            Intent.BUDGET_OPTIMIZATION: [
                r"reduce.*costs?",
                r"cut.*expenses?",
                r"optimize.*budget",
                r"save.*money",
                r"reduce.*spending",
            ],
            Intent.COMPETITIVE_POSITIONING: [
                r"compete.*with",
                r"vs.*competitor",
                r"against.*competitor",
                r"position.*against",
                r"differentiate.*from",
            ],
            Intent.GROWTH_STRATEGY: [
                r"grow.*business",
                r"expansion.*strategy",
                r"scale.*business",
                r"growth.*plan",
            ],

            # Conversational intents
            Intent.GREETING: [r"^(hi|hello|hey|good morning|good afternoon)$", r"^what's up$", r"^how are you$"],
            Intent.HELP: [r"help", r"what.*can.*do", r"how.*use", r"guide"],
            Intent.CONFIRMATION: [r"^(yes|yeah|yep|sure|ok|okay|correct|right)$", r"^go ahead$", r"^proceed$"],
            Intent.CANCELLATION: [r"^(no|nope|cancel|stop|abort|nevermind)$", r"don't.*do.*that"],
        }

    async def classify(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        business_context: Optional[Dict[str, Any]] = None,
    ) -> IntentClassification:
        """Classify user intent with agent routing information"""
        start_time = time.time()

        # Step 1: Try pattern-based classification (fast)
        pattern_result = self._pattern_classify(user_input)
        logger.info("pattern_classification_result", input=user_input, result=pattern_result)

        # Step 2: If high confidence pattern match, use it
        if pattern_result and pattern_result["confidence"] >= 0.85:
            intent = pattern_result["intent"]
            requirements = get_intent_requirements(intent)
            category = get_intent_category(intent)
            logger.info("using_pattern_match", intent=intent.value, confidence=pattern_result["confidence"])

            return IntentClassification(
                intent=intent,
                confidence=pattern_result["confidence"],
                reasoning=f"Pattern match: {pattern_result['pattern']}",
                category=category,
                primary_agent=requirements.primary_agent,
                supporting_agents=requirements.supporting_agents,
                complexity=requirements.complexity,
                is_followup=False,
                processing_time_ms=int((time.time() - start_time) * 1000),
                model_name="pattern_matching",
            )

        # Step 3: Use LLM for complex classification
        llm_result = await self._llm_classify(user_input, conversation_history, business_context)

        # attach processing time if not already set
        try:
            if getattr(llm_result, "processing_time_ms", None) is None:
                llm_result.processing_time_ms = int((time.time() - start_time) * 1000)
        except Exception:
            pass

        return llm_result

    def _pattern_classify(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Fast pattern-based classification; returns dict or None"""
        user_input_lower = (user_input or "").lower().strip()

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                try:
                    # Use re.search with IGNORECASE for flexibility
                    if re.search(pattern, user_input_lower, re.IGNORECASE):
                        # Higher confidence for longer, more specific patterns
                        confidence = 0.95 if len(pattern) > 20 else 0.9 if len(pattern) > 15 else 0.85
                        return {"intent": intent, "confidence": confidence, "pattern": pattern}
                except Exception:
                    # Skip malformed regex patterns
                    continue

        return None

    async def _llm_classify(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        business_context: Optional[Dict[str, Any]] = None,
    ) -> IntentClassification:
        """LLM-based classification for complex cases"""
        prompt = self._build_classification_prompt(user_input, conversation_history, business_context)

        # Use chat_completion_with_json to get a parsed JSON response from Groq
        messages = [{"role": "user", "content": prompt}]
        response = await self.groq.chat_completion_with_json(messages=messages, temperature=0.1, max_tokens=500)

        return self._parse_llm_response(response, conversation_history)

    def _build_classification_prompt(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict[str, Any]]],
        business_context: Optional[Dict[str, Any]],
    ) -> str:
        """Build classification prompt with strategic intents"""
        prompt = f"""You are an intent classifier for MoneyOps, an AI-powered financial operations assistant.

Classify the following user input into ONE of these intents:

OPERATIONAL INTENTS (Basic CRUD operations):
- INVOICE_CREATE: Create a new invoice
- INVOICE_QUERY: Search/list invoices
- INVOICE_UPDATE: Modify an existing invoice
- INVOICE_STATUS_CHECK: Check status of specific invoice
- CLIENT_CREATE: Add a new client
- CLIENT_QUERY: Search/list clients
- PAYMENT_RECORD: Record a payment received
- PAYMENT_QUERY: Search/list payments
- BALANCE_CHECK: Check account balance
- TRANSACTION_QUERY: Search/list transactions
- ACCOUNT_STATEMENT: Generate account statement

STRATEGIC INTENTS (Business intelligence):
- BUSINESS_HEALTH_CHECK: Overall business health/score inquiry
- PROBLEM_DIAGNOSIS: Why is X metric down/problematic?
- SALES_STRATEGY: How to increase sales/revenue
- BUDGET_OPTIMIZATION: How to reduce costs
- CASH_FLOW_PLANNING: Cash flow forecasting/planning
- PROFIT_OPTIMIZATION: How to improve profit margins
- COMPETITIVE_POSITIONING: How to compete with X
- GROWTH_STRATEGY: How to grow the business
- PRICING_STRATEGY: Pricing recommendations
- CUSTOMER_ACQUISITION: How to get more customers
- CUSTOMER_RETENTION: How to retain customers
- SWOT_ANALYSIS: Strengths/weaknesses analysis
- RISK_ASSESSMENT: Business risk analysis

ANALYTICAL INTENTS:
- ANALYTICS_QUERY: Show trends/charts/insights
- REPORT_GENERATE: Generate financial reports
- FORECAST_REQUEST: Predict future metrics
- BENCHMARK_COMPARISON: Compare to industry/past performance

CONVERSATIONAL INTENTS:
- GREETING: Hello, hi, etc.
- HELP: What can you do?
- CONFIRMATION: Yes, proceed, etc.
- CANCELLATION: No, cancel, stop
- GENERAL_QUERY: General questions

User Input: "{user_input}"
"""

        if conversation_history and len(conversation_history) > 0:
            prompt += f"\n\nPrevious Intent: {conversation_history[-1].get('intent', 'N/A')}"
            prompt += "\nThis might be a follow-up question."

        if business_context:
            prompt += f"\n\nBusiness Context: {business_context}"

        prompt += """

Respond in this EXACT JSON format:
{
    "intent": "INTENT_NAME",
    "confidence": 0.85,
    "reasoning": "Brief explanation of why this intent was chosen",
    "is_followup": false
}

IMPORTANT:
- confidence should be 0.0 to 1.0
- Use EXACT intent names from the list above
- is_followup should be true if referring to previous conversation
- Keep reasoning brief (1-2 sentences)
"""
        return prompt

    def _parse_llm_response(
        self, response: Any, conversation_history: Optional[List[Dict[str, Any]]]
    ) -> IntentClassification:
        """Parse LLM JSON response and create IntentClassification"""
        import json

        try:
            # If Groq returned a dict already, use it
            if isinstance(response, dict):
                data = response
            else:
                # Try to extract JSON substring
                response_str = str(response)
                json_start = response_str.find('{')
                json_end = response_str.rfind('}') + 1
                json_str = response_str[json_start:json_end]
                data = json.loads(json_str)

            intent_str = data.get("intent")
            if not intent_str or intent_str not in Intent.__members__:
                raise ValueError("Invalid intent name from LLM")

            intent = Intent[intent_str]
            requirements = get_intent_requirements(intent)
            category = get_intent_category(intent)

            confidence = self._adjust_confidence(base_confidence=float(data.get("confidence", 0.6)), intent=intent, conversation_history=conversation_history)

            previous_intent = None
            if data.get("is_followup") and conversation_history:
                prev_intent_str = conversation_history[-1].get("intent")
                if prev_intent_str and prev_intent_str in Intent.__members__:
                    previous_intent = Intent[prev_intent_str]

            return IntentClassification(
                intent=intent,
                confidence=confidence,
                reasoning=data.get("reasoning", ""),
                category=category,
                primary_agent=requirements.primary_agent,
                supporting_agents=requirements.supporting_agents,
                complexity=requirements.complexity,
                is_followup=bool(data.get("is_followup", False)),
                previous_intent=previous_intent,
                requires_confirmation=requirements.requires_user_confirmation,
                requires_multi_turn=(
                    len(requirements.required_entities) > 3 or requirements.complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.STRATEGIC]
                ),
                model_name="groq-llm",
            )

        except Exception as e:
            # Fallback to GENERAL_QUERY
            return IntentClassification(
                intent=Intent.GENERAL_QUERY,
                confidence=0.5,
                reasoning=f"Error parsing LLM response: {str(e)}",
                category=IntentCategory.CONVERSATIONAL,
                primary_agent=AgentType.GENERAL_AGENT,
                complexity=ComplexityLevel.SIMPLE,
                model_name="fallback",
            )

    def _adjust_confidence(
        self,
        base_confidence: float,
        intent: Intent,
        conversation_history: Optional[List[Dict[str, Any]]],
    ) -> float:
        """Adjust confidence based on business rules"""
        confidence = float(base_confidence)

        if conversation_history and len(conversation_history) > 0:
            last_intent_str = conversation_history[-1].get("intent")
            if last_intent_str and last_intent_str in Intent.__members__:
                last_intent = Intent[last_intent_str]
                if get_intent_category(last_intent) == get_intent_category(intent):
                    confidence = min(1.0, confidence + 0.1)

        category = get_intent_category(intent)
        if category == IntentCategory.STRATEGIC:
            confidence = confidence * 0.9

        return min(1.0, max(0.0, confidence))


# Singleton instance
intent_classifier = IntentClassifier()
