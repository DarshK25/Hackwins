"""
General Agent.
Handles conversational queries plus business-aware questions about the
logged-in user, organization profile, website, and current news.
"""
import asyncio
from typing import Dict, Any, List, Optional

from app.adapters.backend_adapter import get_backend_adapter
from app.agents.base_agent import BaseAgent, AgentResponse, ToolDefinition
from app.services.market_intelligence_service import get_market_intelligence_payload
from app.schemas.intents import Intent, AgentType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GeneralAgent(BaseAgent):
    CAPABILITY_SUMMARY = (
        "MoneyOps can help you with invoices, payments, clients, business health, "
        "growth ideas, compliance, and business context from your account."
    )

    GREETING_RESPONSE = (
        "Hello! I'm MoneyOps AI. I can help with your operations, business context, and growth questions. "
        "What would you like to do?"
    )

    HELP_RESPONSE = (
        "I can create invoices, list clients, check balances, summarize your business profile, "
        "and answer questions about your website, team, users, clients, or current market updates tied to your account."
    )

    def __init__(self):
        self.backend = get_backend_adapter()
        super().__init__()

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
        return []

    def is_production_ready(self) -> bool:
        return True

    async def process(
        self,
        intent: Intent,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        user_input = self._extract_user_input(context)

        logger.info(
            "general_agent_processing",
            intent=intent.value,
            user_input_preview=str(user_input)[:120]
        )

        if intent == Intent.GREETING:
            return self._build_success_response(self.GREETING_RESPONSE, confidence=1.0)

        if intent == Intent.HELP:
            return self._build_success_response(self.HELP_RESPONSE, confidence=1.0)

        if intent == Intent.REPEAT_REQUEST:
            return self._build_success_response(
                "I didn't quite catch that. You can ask about invoices, your business profile, or current growth ideas.",
                confidence=1.0,
            )

        if intent in (Intent.SLOW_DOWN, Intent.SPEED_UP):
            return self._build_success_response(
                "Understood. Ask me about your business, clients, invoices, or growth opportunities.",
                confidence=1.0,
            )

        if intent == Intent.CONFIRMATION:
            return await self._handle_confirmation(context)

        if intent == Intent.CANCELLATION:
            return self._build_success_response(
                "No problem. What would you like to do next?",
                confidence=1.0,
            )

        if self._is_business_aware_query(user_input):
            response_text = await self._answer_business_aware_query(user_input, context or {})
            return self._build_success_response(message=response_text, confidence=0.95)

        try:
            response_text = await self._llm_redirect_response(user_input)
        except Exception as exc:
            logger.warning("general_agent_llm_failed", error=str(exc))
            response_text = self._rule_based_redirect(user_input)

        return self._build_success_response(message=response_text, confidence=0.9)

    async def _handle_confirmation(self, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        if not context:
            return self._build_success_response("Sure. What should we do next?")

        history = context.get("conversation_history", [])
        if not history:
            return self._build_success_response("Confirmed. What would you like to do?")

        last_user_turn = next(
            (
                turn for turn in reversed(history)
                if turn.get("role") == "user" and turn.get("intent") not in (Intent.CONFIRMATION, Intent.GREETING)
            ),
            None,
        )

        if last_user_turn:
            prev_intent = last_user_turn.get("intent")
            if prev_intent in ("INVOICE_CREATE", "CLIENT_CREATE", "PAYMENT_RECORD"):
                return AgentResponse(
                    success=True,
                    message="Great, I'm proceeding with that now.",
                    intent=Intent.CONFIRMATION,
                    action_result={"continue_intent": prev_intent},
                    agent_type=self.get_agent_type(),
                )

        return self._build_success_response("Got it. What would you like to do next?", confidence=1.0)

    def _extract_user_input(self, context: Optional[Dict[str, Any]]) -> str:
        if not context:
            return ""

        for key in ("raw_text", "user_input", "text", "query"):
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        history = context.get("conversation_history", [])
        if history:
            last_user = next(
                (h.get("content", "") for h in reversed(history) if h.get("role") == "user"),
                "",
            )
            return last_user.strip()

        return ""

    def _is_business_aware_query(self, user_input: str) -> bool:
        text_lower = (user_input or "").lower().strip()
        if not text_lower:
            return False

        business_keywords = {
            "my business", "my company", "my organization", "my organisation", "my org",
            "my website", "my site", "my domain", "current domain", "our website",
            "current user", "logged in user", "logged-in user", "who am i", "my profile",
            "my account", "about me", "about my business", "business details",
            "company details", "organization details", "organisation details",
            "team members", "my team", "our team", "team size", "users in my org",
            "how many users", "how many team members", "how many employees", "staff members",
            "who are my team members", "team details", "organization users", "org users",
            "website details", "domain details", "site details", "company profile",
            "growth opportunities", "growth opportunity", "opportunities for my business",
            "live news", "latest news", "current news", "news update", "headlines",
            "industry news", "market news", "business news",
        }

        return any(keyword in text_lower for keyword in business_keywords)

    def _should_fetch_news(self, user_input: str) -> bool:
        text_lower = (user_input or "").lower()
        return any(
            keyword in text_lower for keyword in (
                "news", "headline", "latest", "live", "current update",
                "growth", "opportunit", "market", "trend",
            )
        )

    def _determine_market_topic(self, user_input: str) -> str:
        text_lower = (user_input or "").lower()
        if any(keyword in text_lower for keyword in ("news", "headline", "latest", "live", "market news", "current news")):
            return "news"
        if any(keyword in text_lower for keyword in ("growth", "opportunit", "expand", "scale")):
            return "growth"
        return "overview"

    async def _answer_business_aware_query(self, user_input: str, context: Dict[str, Any]) -> str:
        business_context = await self._load_business_context(context)
        news_context: Dict[str, Any] = {}

        if self._should_fetch_news(user_input):
            try:
                topic = self._determine_market_topic(user_input)
                market_payload = await get_market_intelligence_payload(
                    org_uuid=business_context.get("org_id") or context.get("org_uuid") or context.get("org_id") or "",
                    business_id=int(business_context.get("business_id") or context.get("business_id") or 1),
                    user_id=business_context.get("user_id") or context.get("user_id") or "",
                    user_query=user_input,
                    topic=topic,
                    force_refresh=topic == "news",
                )
                market_data = market_payload.get("market", {})
                news_context = {
                    "answer": market_data.get("news", {}).get("answer", ""),
                    "news": market_data.get("news", {}).get("news", []),
                    "opportunities": market_data.get("opportunities", {}).get("opportunities", ""),
                    "competitors": market_data.get("competitors", {}).get("competitors_answer", ""),
                }
            except Exception as exc:
                logger.warning("general_agent_news_fetch_failed", error=str(exc))
                news_context = {}

        try:
            return await self._llm_business_response(user_input, business_context, news_context)
        except Exception as exc:
            logger.warning("general_agent_business_llm_failed", error=str(exc))
            return self._rule_based_business_response(user_input, business_context, news_context)

    async def _load_business_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        org_id = context.get("org_uuid") or context.get("org_id") or context.get("clerk_org_id")
        user_id = context.get("user_id")
        business_id = context.get("business_id") or 1
        has_user = isinstance(user_id, str) and user_id not in {"", "unknown"}
        has_org = isinstance(org_id, str) and org_id not in {"", "unknown"}

        org_task = self.backend.get_my_organization(user_id) if has_user else None
        metrics_task = self.backend.get_finance_metrics(str(business_id), org_id, user_id) if has_org and has_user else None
        insights_task = self.backend.get_finance_insights(str(business_id), org_id, user_id) if has_org and has_user else None
        clients_task = self.backend.get_clients(org_id, user_id=user_id) if has_org and has_user else None
        invoices_task = self.backend.get_invoices(org_id, user_id=user_id) if has_org and has_user else None
        user_task = self.backend.get_user_by_id(user_id, org_id) if has_org and has_user else None
        users_task = self.backend.get_org_users(org_id, user_id=user_id) if has_org and has_user else None

        tasks = [
            org_task or self._noop_backend_call(),
            metrics_task or self._noop_backend_call(),
            insights_task or self._noop_backend_call(),
            clients_task or self._noop_list_call(),
            invoices_task or self._noop_backend_call(),
            user_task or self._noop_backend_call(),
            users_task or self._noop_backend_call(),
        ]

        org_resp, metrics_resp, insights_resp, clients, invoices_resp, user_resp, users_resp = await asyncio.gather(*tasks)

        org_data = org_resp.data if getattr(org_resp, "success", False) else {}
        metrics_data = metrics_resp.data if getattr(metrics_resp, "success", False) else {}
        insights_data = insights_resp.data if getattr(insights_resp, "success", False) else {}
        invoice_items = invoices_resp.data if getattr(invoices_resp, "success", False) else []
        current_user = user_resp.data if getattr(user_resp, "success", False) else None

        if not current_user and getattr(users_resp, "success", False) and isinstance(users_resp.data, list):
            current_user = next((item for item in users_resp.data if item.get("id") == user_id), None)

        if not isinstance(clients, list):
            clients = []
        if isinstance(invoice_items, dict):
            invoice_items = invoice_items.get("data") or invoice_items.get("invoices") or []
        if not isinstance(invoice_items, list):
            invoice_items = []

        insight_titles: List[str] = []
        if isinstance(insights_data, dict):
            for item in insights_data.get("insights", [])[:3]:
                title = item.get("title")
                if title:
                    insight_titles.append(title)

        org_users = users_resp.data if getattr(users_resp, "success", False) and isinstance(users_resp.data, list) else []
        team_member_names = [item.get("name") for item in org_users if item.get("name")]
        client_names = [item.get("name") for item in clients[:5] if item.get("name")]

        return {
            "org_id": org_id,
            "user_id": user_id,
            "business_id": business_id,
            "organization": org_data or {},
            "current_user": current_user or {},
            "metrics": metrics_data or {},
            "client_count": len(clients),
            "client_names": client_names,
            "invoice_count": len(invoice_items),
            "team_member_count": len(org_users),
            "team_member_names": team_member_names,
            "insights": insight_titles,
        }

    async def _noop_backend_call(self):
        class _EmptyResponse:
            success = False
            data = {}
        return _EmptyResponse()

    async def _noop_list_call(self):
        return []

    def _build_news_query(self, user_input: str, business_context: Dict[str, Any]) -> str:
        organization = business_context.get("organization", {})
        industry = organization.get("industry") or organization.get("primaryActivity") or "business"
        target_market = organization.get("targetMarket") or "India"
        legal_name = organization.get("legalName") or organization.get("tradingName")

        if "news" in user_input.lower():
            return f"{industry} {target_market} business news"
        if "growth" in user_input.lower() or "opportunit" in user_input.lower():
            return f"{industry} {target_market} growth opportunities"
        if legal_name:
            return f"{legal_name} {industry} {target_market}"
        return f"{industry} {target_market} market updates"

    async def _llm_business_response(
        self,
        user_input: str,
        business_context: Dict[str, Any],
        news_context: Dict[str, Any],
    ) -> str:
        from app.llm.groq_client import groq_client

        organization = business_context.get("organization", {})
        current_user = business_context.get("current_user", {})
        metrics = business_context.get("metrics", {})
        news_answer = news_context.get("answer") or "No live news summary available."
        headlines = news_context.get("news") or []
        opportunities = news_context.get("opportunities") or "No growth opportunities summary available."
        competitors = news_context.get("competitors") or "No competitor summary available."

        prompt = f"""You are MoneyOps AI speaking to a logged-in business user.

User question: "{user_input}"

ACCOUNT CONTEXT:
- Organization: {organization.get("legalName") or organization.get("tradingName") or "Unknown"}
- Website: {organization.get("website") or "Not set"}
- Industry: {organization.get("industry") or organization.get("primaryActivity") or "Unknown"}
- Business type: {organization.get("businessType") or "Unknown"}
- Target market: {organization.get("targetMarket") or "Unknown"}
- Current user: {current_user.get("name") or "Unknown"} ({current_user.get("email") or "email unavailable"})
- User role: {current_user.get("role") or "Unknown"}
- Team members: {business_context.get("team_member_count", 0)}
- Team member names: {", ".join(business_context.get("team_member_names", [])) or "None"}
- Clients: {business_context.get("client_count", 0)}
- Client names: {", ".join(business_context.get("client_names", [])) or "None"}

BUSINESS METRICS:
- Revenue: {metrics.get("revenue", 0)}
- Expenses: {metrics.get("expenses", 0)}
- Net profit: {metrics.get("netProfit", 0)}
- Total invoices: {metrics.get("totalInvoices", business_context.get("invoice_count", 0))}
- Overdue invoices: {metrics.get("overdueCount", 0)}
- Overdue amount: {metrics.get("overdueAmount", 0)}
- Insights: {", ".join(business_context.get("insights", [])) or "None"}

NEWS SUMMARY:
{news_answer}

HEADLINES:
{chr(10).join(f"- {headline}" for headline in headlines[:3]) or "- None"}

GROWTH OPPORTUNITIES:
{opportunities}

COMPETITOR SIGNAL:
{competitors}

Instructions:
- Answer the user directly using the account context above.
- If they ask about the website, profile, domain, or current user, answer from the account data.
- If they ask about team members, users, staff, or employees, answer with the team member count and names when available.
- If they ask about clients, answer with the client count and list a few names when available.
- If they ask about business statistics, summarize the core business metrics from the account data.
- If they ask about live/current/latest news, summarize the news block and mention if live headlines are unavailable.
- If they ask about growth opportunities, combine the business metrics, profile, and news into 2 concrete actions.
- Keep it under 4 sentences and voice-friendly.
- Do not invent missing details.

Respond with only the answer text."""

        text = await groq_client.simple_completion(prompt=prompt, temperature=0.2, max_tokens=180)
        text = (text or "").strip()
        if not text:
            raise ValueError("Empty business-aware response")
        return text

    async def _llm_redirect_response(self, user_input: str) -> str:
        from app.llm.groq_client import groq_client

        prompt = f"""You are MoneyOps AI, a financial voice assistant for Indian businesses.

The user said: "{user_input}"

Your job is to:
1. Acknowledge what they said briefly and warmly.
2. Redirect them to what MoneyOps can actually help with.

MoneyOps capabilities:
- Creating and managing invoices
- Tracking client payments
- Checking account balance
- Recording transactions
- Listing and managing clients
- Summarizing the logged-in business profile and business updates

Rules:
- Keep response under 30 words total
- Be friendly and natural
- Do not use placeholder text
- If the input seems like noise, say: "I didn't quite catch that. You can ask about invoices, balances, or your business profile."

Respond with only the response text."""

        text = await groq_client.simple_completion(prompt=prompt, temperature=0.7, max_tokens=80)
        text = (text or "").strip()
        if not text or len(text) < 5:
            raise ValueError("Empty LLM response")

        forbidden = ["beep boop", "coming in v2", "placeholder"]
        if any(word in text.lower() for word in forbidden):
            raise ValueError(f"Forbidden placeholder text returned: {text[:50]}")

        return text

    def _rule_based_business_response(
        self,
        user_input: str,
        business_context: Dict[str, Any],
        news_context: Dict[str, Any],
    ) -> str:
        text_lower = (user_input or "").lower()
        organization = business_context.get("organization", {})
        current_user = business_context.get("current_user", {})
        metrics = business_context.get("metrics", {})
        website = organization.get("website") or "no website is set yet"
        industry = organization.get("industry") or organization.get("primaryActivity") or "your current business domain is not set yet"
        org_name = organization.get("legalName") or organization.get("tradingName") or "your business"
        user_name = current_user.get("name") or "the logged-in user"
        user_role = current_user.get("role") or "role not set"
        revenue = metrics.get("revenue", 0)
        expenses = metrics.get("expenses", 0)
        profit = metrics.get("netProfit", 0)
        overdue_count = metrics.get("overdueCount", 0)
        client_count = business_context.get("client_count", 0)
        client_names = business_context.get("client_names", [])
        team_member_count = business_context.get("team_member_count", 0)
        team_member_names = business_context.get("team_member_names", [])
        headlines = news_context.get("news") or []

        if any(keyword in text_lower for keyword in ("website", "site", "domain")):
            return f"{org_name} is currently listed in MoneyOps under {industry}, and the website on file is {website}."

        if any(keyword in text_lower for keyword in ("current user", "logged in", "logged-in", "who am i", "my profile", "about me")):
            return f"You're signed in as {user_name}. Your role is {user_role}, and the email on file is {current_user.get('email') or 'not available'}."

        if any(keyword in text_lower for keyword in ("team member", "team", "users", "employees", "staff")):
            if team_member_count == 0:
                return f"I couldn't find any team members for {org_name} right now."
            listed_names = ", ".join(team_member_names[:5]) if team_member_names else "names are unavailable"
            return f"You currently have {team_member_count} team members in {org_name}. They are {listed_names}."

        if any(keyword in text_lower for keyword in ("clients", "client list", "who are my clients")):
            if client_count == 0:
                return f"You don't have any clients listed for {org_name} yet."
            listed_clients = ", ".join(client_names[:5]) if client_names else "client names are unavailable"
            return f"You currently have {client_count} clients in {org_name}. Some of them are {listed_clients}."

        if any(keyword in text_lower for keyword in ("statistics", "stats", "metrics", "business performance")):
            return (
                f"For {org_name}, revenue is {self._format_currency(revenue)}, expenses are {self._format_currency(expenses)}, "
                f"net profit is {self._format_currency(profit)}, with {business_context.get('invoice_count', 0)} invoices and {client_count} clients."
            )

        if "news" in text_lower or "headline" in text_lower:
            if headlines:
                return f"Here are the latest updates relevant to {industry}: {headlines[0]}{'; ' + headlines[1] if len(headlines) > 1 else ''}."
            return f"I can identify your business profile, but I couldn't pull live headlines right now. You're currently mapped to {industry}, so we can still review growth opportunities from your account data."

        if "growth" in text_lower or "opportunit" in text_lower:
            return (
                f"For {org_name}, the clearest growth opportunities are to deepen work in {industry} and improve collections before scaling. "
                f"You're at revenue {self._format_currency(revenue)} with {client_count} clients and {overdue_count} overdue invoices, so the fastest win is recovering cash and packaging one repeatable offer around your current domain."
            )

        return (
            f"{org_name} is currently mapped to {industry}. The website on file is {website}, "
            f"and your latest tracked revenue is {self._format_currency(revenue)}."
        )

    def _rule_based_redirect(self, user_input: str) -> str:
        text_lower = (user_input or "").lower().strip()

        if len(text_lower) < 5 or not any(char.isalpha() for char in text_lower):
            return "I didn't quite catch that. You can ask about invoices, balances, or your business profile."

        if any(word in text_lower for word in ["what can", "what do", "help", "how do i", "what are"]):
            return self.HELP_RESPONSE

        if text_lower in ("okay", "ok", "sure", "alright", "fine", "yes", "yeah", "no", "nope"):
            return "What would you like to do? I can help with invoices, balances, clients, or your business profile."

        if any(word in text_lower for word in ["noise", "test", "hello", "hey", "hi"]):
            return "I'm ready to help. Try asking about your invoices, business profile, or current growth opportunities."

        return "I can help with invoices, balances, clients, or questions about your business profile and updates."

    def _format_currency(self, value: Any) -> str:
        try:
            numeric = float(value or 0)
            return f"INR {numeric:,.0f}"
        except Exception:
            return "INR 0"


general_agent = GeneralAgent()
