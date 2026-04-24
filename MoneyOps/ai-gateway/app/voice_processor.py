import re
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from app.orchestration.intent_classifier import intent_classifier
from app.orchestration.entity_extractor import entity_extractor
from app.agents.finance_agent import finance_agent
from app.state.session_manager import session_manager
from app.schemas.intents import Intent
from app.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class VoiceContext:
    session_id: str
    user_id: str
    org_uuid: str
    business_id: Optional[int] = 1
    clerk_org_id: Optional[str] = None
    extracted_entities: List[Dict[str, Any]] = None
    raw_text: Optional[str] = None

class VoiceProcessor:
    def __init__(self):
        self.intent_classifier = intent_classifier
        self.entity_extractor = entity_extractor
        self.finance_agent = finance_agent
        self.state_manager = session_manager
        from app.adapters.backend_adapter import get_backend_adapter
        self.backend = get_backend_adapter()

    async def _publish_ui_event(self, session_id: str, payload: Dict[str, Any]):
        """Publish a UI event to the LiveKit room via the Voice Service."""
        # Note: In this architecture, the Voice Service (Python) can listen for 
        # Redis events or we can return it in the process() response.
        # Since process() is called by Voice Service, we just return it.
        pass # Returning in process() result is cleaner for this request-response flow

    def _should_record_exchange(self, intent: Optional[str], response_text: Optional[str]) -> bool:
        return bool(response_text) and intent not in {"DUPLICATE_INPUT", "PROCESSING_LOCKED"}

    def _record_exchange(self, session_id: str, user_text: str, assistant_text: str, intent: Optional[str]) -> None:
        if not self._should_record_exchange(intent, assistant_text):
            return
        self.state_manager.add_turn(session_id, "user", user_text, intent)
        self.state_manager.add_turn(session_id, "assistant", assistant_text, intent)

    def _should_report_activity(self, result: dict) -> bool:
        if not result or not result.get("response_text"):
            return False

        intent = (result.get("intent") or "").upper()
        if intent in {"DUPLICATE_INPUT", "PROCESSING_LOCKED", "CANCELLATION"}:
            return False

        ui_event = result.get("ui_event") or {}
        ui_event_type = (ui_event.get("type") or "").lower()
        interim_ui_types = {"progress", "open_client_picker", "open_input_dialog"}

        if intent in {"INVOICE_CREATE", "CLIENT_CREATE"} and ui_event_type in interim_ui_types:
            return False

        return True

    def _get_reported_agent_name(self, user_text: str, intent: Optional[str]) -> Optional[str]:
        normalized_intent = (intent or "").upper()
        if normalized_intent in {"MARKET_NEWS", "TREND_ANALYSIS", "GROWTH_STRATEGY"}:
            return "Market Agent"
        if self._is_market_query(user_text) and normalized_intent in {"GENERAL_QUERY", "FOLLOWUP_QUESTION", "ANALYTICS_QUERY"}:
            return "Market Agent"
        return None

    def _build_agent_context(self, context: VoiceContext, session, text: str) -> Dict[str, Any]:
        route_context = vars(context).copy()
        route_context["raw_text"] = text
        route_context["text"] = text
        route_context["user_input"] = text
        route_context["conversation_history"] = list(session.history or [])
        route_context["session_locked_intent"] = session.locked_intent
        route_context["focused_client_id"] = session.focused_client_id
        route_context["focused_client_name"] = session.focused_client_name
        return route_context

    def _format_rupees(self, value: Any) -> str:
        try:
            return f"rupees {float(value or 0):,.0f}"
        except Exception:
            return "rupees 0"

    def _clean_spoken_value(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = cleaned.strip(" \"'`.,:;!?")
        return cleaned or None

    def _strip_client_field_prefix(self, raw_text: str, field_name: str) -> str:
        patterns = {
            "client_name": r"^(?:the\s+client(?:'s)?\s+name\s+is|client(?:'s)?\s+name\s+is|name\s+is|it's|it is)\s+",
            "company": r"^(?:the\s+company(?:\s+name)?\s+is|company(?:\s+name)?\s+is|it's|it is)\s+",
            "email": r"^(?:the\s+email(?:\s+address)?\s+is|email(?:\s+address)?\s+is)\s+",
            "phone": r"^(?:the\s+phone(?:\s+number)?\s+is|phone(?:\s+number)?\s+is|number\s+is)\s+",
            "teamActionCode": r"^(?:the\s+team\s+security\s+code\s+is|team\s+security\s+code\s+is|security\s+code\s+is|team\s+code\s+is|code\s+is|pin\s+is)\s+",
        }
        pattern = patterns.get(field_name)
        if not pattern:
            return raw_text
        return re.sub(pattern, "", raw_text or "", flags=re.IGNORECASE).strip()

    def _extract_email_value(self, raw_text: str) -> Optional[str]:
        if not raw_text:
            return None
        match = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", raw_text)
        if not match:
            return None
        return self._clean_spoken_value(match.group(1))

    def _extract_phone_value(self, raw_text: str) -> Optional[str]:
        if not raw_text:
            return None
        digits = re.sub(r"\D", "", raw_text)
        if 7 <= len(digits) <= 15:
            return digits
        return None

    def _extract_team_code(self, raw_text: str) -> Optional[str]:
        if not raw_text:
            return None
        match = re.search(r"\b(?:code|pin|security code)\s*(?:is\s*)?([A-Za-z0-9-]{4,12})\b", raw_text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
        compact = re.sub(r"\s+", "", raw_text)
        if re.fullmatch(r"[A-Za-z0-9-]{4,12}", compact):
            return compact
        return None

    def _get_client_field_value(self, entities: Dict[str, Any], *keys: str) -> Optional[str]:
        for key in keys:
            value = entities.get(key)
            if value:
                return self._clean_spoken_value(value)
        return None

    def _apply_client_followup_answer(self, draft: Dict[str, Any], raw_text: str, entities: Dict[str, Any]) -> bool:
        field_name = draft.get("last_question_asked")
        if not field_name:
            return False
        if draft.get(field_name):
            return True

        stripped_text = self._strip_client_field_prefix(raw_text, field_name)

        if field_name == "client_name":
            candidate = self._get_client_field_value(entities, "client_name", "entity_name")
            if not candidate:
                candidate = self._clean_spoken_value(stripped_text)
            if candidate and candidate.lower() not in {"create client", "add client", "new client", "client"}:
                draft["client_name"] = candidate
                return True
            return False

        if field_name == "email":
            candidate = self._get_client_field_value(entities, "email") or self._extract_email_value(stripped_text)
            if candidate:
                draft["email"] = candidate
                return True
            return False

        if field_name == "phone":
            candidate = (
                self._get_client_field_value(entities, "phone", "phone_number", "phoneNumber")
                or self._extract_phone_value(stripped_text)
            )
            if candidate:
                draft["phone"] = candidate
                return True
            return False

        if field_name == "company":
            candidate = self._get_client_field_value(entities, "company", "company_name", "entity_name")
            if not candidate:
                candidate = self._clean_spoken_value(stripped_text)
            if candidate:
                draft["company"] = candidate
                return True
            return False

        if field_name == "teamActionCode":
            candidate = self._get_client_field_value(entities, "teamActionCode", "team_action_code") or self._extract_team_code(stripped_text)
            if candidate:
                draft["teamActionCode"] = candidate
                draft.pop("team_action_code", None)
                return True
            return False

        return False

    def _seed_client_draft_from_entities(self, draft: Dict[str, Any], entities: Dict[str, Any]) -> None:
        if not draft.get("client_name"):
            client_name = self._get_client_field_value(entities, "client_name")
            if client_name:
                draft["client_name"] = client_name

        if not draft.get("email"):
            email = self._get_client_field_value(entities, "email")
            if email:
                draft["email"] = email

        if not draft.get("phone"):
            phone = self._get_client_field_value(entities, "phone", "phone_number", "phoneNumber")
            if phone:
                draft["phone"] = phone

        if not draft.get("company"):
            company = self._get_client_field_value(entities, "company", "company_name")
            if company:
                draft["company"] = company

        if not draft.get("teamActionCode"):
            team_code = self._get_client_field_value(entities, "teamActionCode", "team_action_code")
            if team_code:
                draft["teamActionCode"] = team_code

    def _get_next_client_prompt(self, draft: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
        prompts = (
            ("client_name", "What's the client's name?"),
            ("email", "What's the client's email address?"),
            ("phone", "What's the client's phone number?"),
            ("company", "What's the company name for this client?"),
            ("teamActionCode", "Please tell me the team security code to create this client."),
        )
        for field_name, prompt in prompts:
            if not draft.get(field_name):
                return field_name, prompt
        return None, None

    def _get_client_retry_prompt(self, field_name: Optional[str]) -> str:
        prompts = {
            "client_name": "I didn't catch the client's name. Please say the name again.",
            "email": "I didn't catch a valid email address. Please say the email again.",
            "phone": "I didn't catch a valid phone number. Please say the phone number again.",
            "company": "I didn't catch the company name. Please say the company name again.",
            "teamActionCode": "I didn't catch the team security code. Please say the code again.",
        }
        return prompts.get(field_name, "Please say that one more time.")

    def _is_market_query(self, text: str) -> bool:
        lowered = (text or "").lower()
        market_keywords = (
            "market news",
            "market new",
            "market update",
            "market updates",
            "current market",
            "latest market",
            "industry news",
            "business news",
            "headlines",
            "latest news",
            "current news",
            "real market updates",
        )
        return any(keyword in lowered for keyword in market_keywords)

    def _references_previous_client(self, text: str) -> bool:
        lowered = f" {(text or '').lower()} "
        pronouns = (" he ", " she ", " they ", " them ", " that client ", " this client ", " that customer ", " this customer ")
        return any(token in lowered for token in pronouns)

    def _is_top_client_query(self, text: str) -> bool:
        lowered = (text or "").lower()
        phrases = (
            "top paying client",
            "highest paying client",
            "highest revenue client",
            "top revenue client",
            "paying me the most",
            "who pays me the most",
            "best paying client",
        )
        return any(phrase in lowered for phrase in phrases)

    def _is_client_invoice_count_query(self, text: str) -> bool:
        lowered = (text or "").lower()
        count_signals = ("how many", "number of", "count")
        return "invoice" in lowered and any(signal in lowered for signal in count_signals)

    def _is_client_revenue_query(self, text: str) -> bool:
        lowered = (text or "").lower()
        revenue_signals = (
            "how much",
            "revenue",
            "billed",
            "collected",
            "outstanding",
            "paying me",
            "generated",
        )
        return any(signal in lowered for signal in revenue_signals)

    def _should_handle_client_business_query(self, text: str, context: VoiceContext, session) -> bool:
        entity_map = {
            item.get("type"): item.get("value")
            for item in (context.extracted_entities or [])
            if item.get("type") and item.get("value")
        }
        has_explicit_client = bool(entity_map.get("client_name") or entity_map.get("company_name"))
        has_focused_client = bool(session.focused_client_name) and self._references_previous_client(text)
        return self._is_top_client_query(text) or (
            (self._is_client_invoice_count_query(text) or self._is_client_revenue_query(text))
            and (has_explicit_client or has_focused_client)
        )

    def _set_focused_client(self, session, client_id: Optional[str], client_name: Optional[str]) -> None:
        session.focused_client_id = client_id
        session.focused_client_name = client_name
        self.state_manager.save_session(session)

    async def _resolve_client_reference(self, text: str, context: VoiceContext, session) -> Optional[Dict[str, Any]]:
        entity_map = {
            item.get("type"): item.get("value")
            for item in (context.extracted_entities or [])
            if item.get("type") and item.get("value")
        }
        explicit_name = entity_map.get("client_name") or entity_map.get("company_name")
        if explicit_name:
            client = await self.finance_agent._resolve_client(explicit_name, context.org_uuid, context.user_id)
            if client:
                self._set_focused_client(session, client.get("id"), client.get("name"))
                return client

        if session.focused_client_name and self._references_previous_client(text):
            if session.focused_client_id:
                return {
                    "id": session.focused_client_id,
                    "name": session.focused_client_name,
                }

            client = await self.finance_agent._resolve_client(session.focused_client_name, context.org_uuid, context.user_id)
            if client:
                self._set_focused_client(session, client.get("id"), client.get("name"))
                return client

            return {"id": None, "name": session.focused_client_name}

        client = await self.finance_agent._resolve_client(text, context.org_uuid, context.user_id)
        if client:
            self._set_focused_client(session, client.get("id"), client.get("name"))
        return client

    async def process(self, text: str, context: VoiceContext) -> dict:
        session = self.state_manager.get_session(context.session_id, context.user_id, context.org_uuid)

        # ── INPUT DEDUPLICATION ───────────────────────────────────────────────────────
        # Check if this exact input was recently processed (e.g., UI click + voice input)
        if session.is_input_recently_processed(text):
            logger.info({
                "session_id": context.session_id,
                "event": "duplicate_input_rejected",
                "text_preview": str(text)[:50]
            })
            return {
                "response_text": "",  # Silent rejection - don't repeat question
                "success": False,
                "intent": "DUPLICATE_INPUT",
                "is_duplicate": True
            }

        # ── INPUT PROCESSING LOCK ─────────────────────────────────────────────────────
        # Serialize input processing - only one input at a time per session
        if not self.state_manager.acquire_processing_lock(context.session_id):
            logger.warning({
                "session_id": context.session_id,
                "event": "input_processing_lock_failed",
                "text_preview": str(text)[:50]
            })
            return {
                "response_text": "Please wait for the current question to be answered.",
                "success": False,
                "intent": "PROCESSING_LOCKED",
                "is_locked": True
            }

        try:
            result = await self._process_locked(text, context, session)
            result_intent = result.get("intent", "UNKNOWN")
            if self._should_report_activity(result) and context.org_uuid and not context.org_uuid.startswith("org_"):
                try:
                    import asyncio
                    asyncio.create_task(
                        self.backend.report_orchestrator_activity(
                            org_id=context.org_uuid,
                            user_id=context.user_id,
                            intent=result_intent,
                            description=result.get("response_text"),
                            status="COMPLETED" if result.get("success") else "FAILED",
                            session_id=context.session_id,
                            agent_name=self._get_reported_agent_name(text, result_intent),
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to log orchestrator activity: {e}")
            return result
        finally:
            # Always release the lock
            self.state_manager.release_processing_lock(context.session_id)

    async def _process_locked(self, text: str, context: VoiceContext, session) -> dict:
        """Process input after acquiring lock. This is the main processing logic."""

        # 1. RESOLVE IDENTITY (If still Clerk format)
        if context.org_uuid.startswith("org_") and (not session.org_id or session.org_id.startswith("org_")):
            logger.info({"user": context.user_id, "event": "resolving_identity_per_session"})
            onboarding_resp = await self.backend.get_onboarding_status(context.user_id)
            if onboarding_resp.success and onboarding_resp.data:
                data = onboarding_resp.data
                resolved_uuid = data.get("orgId") or data.get("orgUuid") or data.get("organizationId")
                if resolved_uuid:
                    context.org_uuid = resolved_uuid
                    session.org_id = resolved_uuid
                    session.business_id = data.get("businessId") or 1
                    self.state_manager.save_session(session)

        # 2. RESTORE FROM SESSION (If already resolved in previous turns)
        if session.org_id and not session.org_id.startswith("org_"):
            context.org_uuid = session.org_id
            context.business_id = session.business_id
            
        logger.info({
            "session_id": context.session_id,
            "resolved_org_uuid": context.org_uuid,
            "business_id": context.business_id,
            "event": "identity_persistence_check"
        })
        
        # 3. CONTEXT PERSISTENCE (Merge new text with session draft)
        # Classify with session context to avoid classification drifting (Issue 2/3)
        classification = await self.intent_classifier.classify(
            text, 
            conversation_history=session.history,
            locked_intent=session.locked_intent,
            collected_entities=(
                session.invoice_draft.__dict__
                if session.invoice_draft
                else session.client_draft
                if session.client_draft
                else session.expense_draft
            )
        )
        intent_obj = classification.intent

        # State Machine: If LOCKED, we tend to stay locked unless it's a clear cancel
        if session.locked_intent and classification.intent in (Intent.GENERAL_QUERY, Intent.GREETING):
             # Force back to locked intent if we are in the middle of a creation
             intent_obj = Intent[session.locked_intent]
             logger.info("state_machine_forced_locked_intent", intent=session.locked_intent)

        intent_val = intent_obj.value if hasattr(intent_obj, 'value') else str(intent_obj)

        entities_result = await self.entity_extractor.extract(
            text, 
            intent_obj, 
            context, 
            locked_intent=session.locked_intent
        )
        new_entities = {e.entity_type.value.lower(): e.value for e in entities_result.entities} if hasattr(entities_result, 'entities') else {}
        
        if intent_val == "CLIENT_CREATE" or session.locked_intent == "CLIENT_CREATE":
            if session.client_draft is None: session.client_draft = {}
            for k, v in new_entities.items():
                if v: session.client_draft[k] = v
            self.state_manager.save_session(session)
            # Sync context for handlers
            context.extracted_entities = [{"type": k, "value": v} for k, v in session.client_draft.items()]
        else:
            # Standard sync for current turn
            context.extracted_entities = [{"type": k, "value": v} for k, v in new_entities.items()]

        # 4. START MARKET MONITOR (Background job)
        if context.org_uuid and not context.org_uuid.startswith("org_"):
            from app.agents.market_agent import market_agent_instance
            market_agent_instance.start_market_monitor(
                org_uuid=context.org_uuid,
                business_id=context.business_id or 1,
                industry="professional services" 
            )
        
        # INTENT LOCKS
        if (session.locked_intent == "INVOICE_CREATE" 
                and session.invoice_draft is not None):
            
            cancel_words = {"cancel", "stop", "never mind", "forget it", "abort"}
            if any(w in text.lower() for w in cancel_words):
                session.locked_intent = None
                session.invoice_draft = None
                self.state_manager.save_session(session)
                return {"response_text": "Invoice cancelled.", "success": True, "intent": "CANCELLATION"}
            
            # Use already classified intent
            if intent_val not in (
                Intent.INVOICE_CREATE.value, Intent.INVOICE_UPDATE.value, 
                Intent.CONFIRMATION.value, Intent.CANCELLATION.value, 
                Intent.GENERAL_QUERY.value, Intent.GREETING.value, 
                Intent.FOLLOWUP_QUESTION.value, Intent.CLARIFICATION_REQUEST.value
            ):
                session.locked_intent = None
                # Fall through to normal path
            else:
                result = await self.finance_agent.handle_invoice_create(context)

                self._record_exchange(context.session_id, text, result.message, "INVOICE_CREATE")

                return {
                    "response_text": result.message,
                    "success": result.success,
                    "intent": "INVOICE_CREATE",
                    "ui_event": result.ui_event if hasattr(result, 'ui_event') else None,
                }
        
        if (session.locked_intent == "CLIENT_CREATE"
                and session.client_draft is not None):

            cancel_words = {"cancel", "stop", "never mind", "forget it", "abort"}
            if any(w in text.lower().strip() for w in cancel_words):
                session.locked_intent = None
                session.client_draft = None
                self.state_manager.save_session(session)
                return {"response_text": "Client creation cancelled.", "success": True, "intent": "CANCELLATION"}

            result = await self._handle_client_create(text, context)
            self._record_exchange(context.session_id, text, result.message, "CLIENT_CREATE")
            return {
                "response_text": result.message,
                "success": result.success,
                "intent": "CLIENT_CREATE",
                "ui_event": result.ui_event if hasattr(result, "ui_event") else None,
            }

        if session.locked_intent == "EXPENSE_CREATE" and session.expense_draft is not None:
            cancel_words = {"cancel", "stop", "never mind", "forget it", "abort"}
            if any(w in text.lower().strip() for w in cancel_words):
                session.locked_intent = None
                session.expense_draft = None
                self.state_manager.save_session(session)
                return {"response_text": "Expense entry cancelled.", "success": True, "intent": "CANCELLATION"}

            if intent_val not in (
                Intent.EXPENSE_CREATE.value,
                Intent.EXPENSE_QUERY.value,
                Intent.CONFIRMATION.value,
                Intent.CANCELLATION.value,
                Intent.GENERAL_QUERY.value,
                Intent.GREETING.value,
                Intent.FOLLOWUP_QUESTION.value,
                Intent.CLARIFICATION_REQUEST.value,
            ):
                session.locked_intent = None
            else:
                result = await self.finance_agent.handle_expense_create(context)
                self._record_exchange(context.session_id, text, result.message, "EXPENSE_CREATE")
                return {
                    "response_text": result.message,
                    "success": result.success,
                    "intent": "EXPENSE_CREATE",
                    "ui_event": result.ui_event if hasattr(result, "ui_event") else None,
                }


        # NORMAL PATH
        classification = await self.intent_classifier.classify(
            text, 
            conversation_history=session.history,
            business_context={"business_id": context.business_id, "org_uuid": context.org_uuid}
        )
        intent = classification.intent.value if hasattr(classification.intent, 'value') else str(classification.intent)
        
        # 3. MERGE SESSION ENTITIES (Persistence across turns)
        entities_result = await self.entity_extractor.extract(text, classification.intent, context)
        new_entities = {e.entity_type.value.lower(): e.value for e in entities_result.entities} if hasattr(entities_result, 'entities') else {}
        
        # Only merge into client_draft for CLIENT_CREATE intents
        if intent == "CLIENT_CREATE":
            if session.client_draft is None:
                session.client_draft = {}
            for k, v in new_entities.items():
                if v: session.client_draft[k] = v
            self.state_manager.save_session(session)
            context.extracted_entities = [
                {"type": k, "value": v} for k, v in session.client_draft.items()
            ]
        else:
            # Standard sync for non-client intents
            context.extracted_entities = [{"type": k, "value": v} for k, v in new_entities.items()]
        
        MARKET_INTENTS = {
            "GROWTH_STRATEGY", "MARKET_EXPANSION", "SCALING_ADVICE",
            "COMPETITIVE_POSITIONING", "PARTNERSHIP_OPPORTUNITIES",
            "PRODUCT_STRATEGY", "RISK_ASSESSMENT", "SALES_STRATEGY",
            "CUSTOMER_ACQUISITION", "PRICING_STRATEGY", "PROBLEM_DIAGNOSIS",
            "SWOT_ANALYSIS", "TREND_ANALYSIS", "BENCHMARK_COMPARISON",
            "FORECAST_REQUEST",
            "BUDGET_OPTIMIZATION", "CASH_FLOW_PLANNING", "PROFIT_OPTIMIZATION",
            "CUSTOMER_RETENTION",
        }

        if intent == "INVOICE_CREATE":
            result = await self.finance_agent.handle_invoice_create(context)
        elif intent == "EXPENSE_CREATE":
            result = await self.finance_agent.handle_expense_create(context)
        elif intent == "CLIENT_CREATE":
            session.locked_intent = "CLIENT_CREATE"
            # Keep existing draft if we are just entering context again
            if not session.client_draft:
                session.client_draft = {}
            session.dialog_pending = False 
            self.state_manager.save_session(session)
            result = await self._handle_client_create(text, context)
        elif self._is_market_query(text) and intent in {"GENERAL_QUERY", "FOLLOWUP_QUESTION", "ANALYTICS_QUERY"}:
            from app.agents.market_agent import market_agent_instance
            result = await market_agent_instance.handle_market_query(
                text, context,
                conversation_history=session.history
            )
        elif intent in {"CLIENT_QUERY", "INVOICE_QUERY", "ANALYTICS_QUERY", "FOLLOWUP_QUESTION", "GENERAL_QUERY"} and self._should_handle_client_business_query(text, context, session):
            result = await self._handle_client_query(text, context, session)
        elif intent == "CLIENT_QUERY":
            result = await self._handle_client_query(text, context, session)
        elif intent in MARKET_INTENTS:
            from app.agents.market_agent import market_agent_instance
            result = await market_agent_instance.handle_market_query(
                text, context, 
                conversation_history=session.history
            )
        elif intent == "GENERAL_QUERY":
            from app.orchestration.agent_router import agent_router
            agent_resp = await agent_router.route(
                classification.intent,
                {e["type"]: e["value"] for e in context.extracted_entities},
                self._build_agent_context(context, session, text),
                session_id=context.session_id
            )
            result = agent_resp
        else:
            # Fallback to general agent or other handlers
            from app.orchestration.agent_router import agent_router
            agent_resp = await agent_router.route(
                classification.intent, 
                {e["type"]: e["value"] for e in context.extracted_entities}, 
                self._build_agent_context(context, session, text),
                session_id=context.session_id
            )
            result = agent_resp

        self._record_exchange(context.session_id, text, result.message, intent)

        return {
            "response_text": result.message,
            "success": result.success,
            "intent": intent,
            "ui_event": result.ui_event if hasattr(result, 'ui_event') else None,
        }

    def _infer_industry(self, text: str) -> str:
        text = text.lower()
        if any(w in text for w in ["real estate", "park", "builder", "property", "realty"]):
            return "Commercial Real Estate"
        elif any(w in text for w in ["hotel", "resort", "hospitality"]):
            return "Hospitality"
        elif any(w in text for w in ["logistics", "fleet", "transport"]):
            return "Fleet & Logistics"
        elif any(w in text for w in ["tech", "it", "software"]):
            return "IT/Tech Campus"
        return "General Business"

    def _generate_smart_notes(self, name: str, city: str, industry: str) -> str:
        base_notes = f"Potential B2B client in {city}. Industry: {industry}.\n"
        if industry == "Commercial Real Estate" or "tech" in industry.lower():
            base_notes += "Likely needs EV charging infrastructure due to ESG compliance pressure and employee EV adoption.\nRecommended: Pitch FAME III subsidy + fast deployment."
        elif industry == "Fleet & Logistics":
            base_notes += "High utilization expected. Pitch bulk charging rates & depot infrastructure."
        else:
            base_notes += "Initial contact to be established. Assess energy infrastructure needs."
        return base_notes

    def _calculate_lead_score(self, text: str, city: str) -> int:
        score = 50
        text = text.lower()
        if "real estate" in text or "park" in text or "campus" in text:
            score += 20
        if city.lower() in ["pune", "mumbai", "bangalore"]:
            score += 15 # Core markets
        if "private limited" in text or "pvt ltd" in text:
            score += 15
        return min(score, 100)

    async def finalize_client_create(self, session) -> dict:
        """Finalize client creation after collecting voice or UI inputs."""
        draft = session.client_draft
        name = draft.get("client_name") or draft.get("company_name")
        city = draft.get("city") or draft.get("address", "an unknown location")
        team_code = draft.get("teamActionCode") or draft.get("team_action_code")

        if not team_code:
            draft["last_question_asked"] = "teamActionCode"
            session.client_draft = draft
            session.locked_intent = "CLIENT_CREATE"
            session.dialog_pending = False
            session.dialog_id = None
            self.state_manager.save_session(session)
            return {
                "success": True,
                "response_text": "Please tell me the team security code to create this client.",
                "ui_event": {
                    "type": "progress",
                    "variant": "warning",
                    "title": "Team Security Code",
                    "message": "Waiting for team security code"
                }
            }
        
        industry = self._infer_industry(str(draft))
        smart_notes = self._generate_smart_notes(name, city, industry)

        try:
            resp = await self.backend._request(
                "POST", "/api/clients",
                org_id=session.org_id,
                user_id=session.user_id,
                data={
                    "name": name,
                    "company": draft.get("company") or None,
                    "email": draft.get("email") or None,
                    "phoneNumber": draft.get("phone") or draft.get("phoneNumber") or None,
                    "address": draft.get("address") or city or None,
                    "taxId": draft.get("gst_number") or draft.get("taxId") or None,
                    "notes": smart_notes,
                    "teamActionCode": draft.get("teamActionCode") or draft.get("team_action_code") or None,
                    "source": "VOICE"
                }
            )
            
            logger.info({
                "event": "client_finalize_backend_response",
                "success": resp.success if resp else None,
                "data": str(resp.data)[:200] if resp else "None",
                "status": getattr(resp, 'status_code', 'unknown')
            })
            
            if resp and hasattr(resp, 'success') and resp.success:
                client_id = resp.data.get("id") if isinstance(resp.data, dict) else None
                self._set_focused_client(session, client_id, name)
                session.locked_intent = None
                session.client_draft = None
                session.dialog_pending = False
                session.dialog_id = None
                self.state_manager.save_session(session)

                ui_event = {
                    "type": "client_created",
                    "client_id": client_id,
                    "name": name,
                    "toast": {
                        "title": "Client Saved",
                        "variant": "success",
                        "message": f"Added {name} to CRM."
                    }
                }
                
                company_fragment = f" from {draft.get('company')}" if draft.get("company") else ""
                return {
                    "success": True,
                    "response_text": f"Success! I've added {name}{company_fragment} to your CRM.",
                    "ui_event": ui_event
                }
            else:
                err = resp.error if resp else "Unknown"
                if "Invalid team security code" in str(err):
                    attempts = int(draft.get("team_code_attempts") or 0) + 1
                    draft["team_code_attempts"] = attempts
                    draft["last_question_asked"] = "teamActionCode"
                    draft.pop("teamActionCode", None)
                    draft.pop("team_action_code", None)

                    if attempts >= 2:
                        session.locked_intent = None
                        session.client_draft = None
                        session.dialog_pending = False
                        session.dialog_id = None
                        self.state_manager.save_session(session)
                        return {
                            "success": True,
                            "response_text": "The team security code was incorrect again, so I cancelled the client creation.",
                            "ui_event": {
                                "type": "toast",
                                "variant": "error",
                                "title": "Client cancelled",
                                "message": "Two invalid code attempts"
                            }
                        }

                    session.client_draft = draft
                    session.locked_intent = "CLIENT_CREATE"
                    session.dialog_pending = False
                    session.dialog_id = None
                    self.state_manager.save_session(session)
                    return {
                        "success": True,
                        "response_text": "That team security code was incorrect. Please say it one more time.",
                        "ui_event": {
                            "type": "toast",
                            "variant": "warning",
                            "title": "Invalid code",
                            "message": "One attempt remaining"
                        }
                    }
                if "Team security code is required" in str(err):
                    draft["last_question_asked"] = "teamActionCode"
                    session.client_draft = draft
                    session.locked_intent = "CLIENT_CREATE"
                    self.state_manager.save_session(session)
                    return {"success": True, "response_text": "The team security code is required. Please say the code again."}
                return {"success": False, "response_text": f"Error saving client: {err}"}
        except Exception as e:
            logger.error("client_finalize_error", error=str(e))
            return {"success": False, "response_text": f"Critical error: {str(e)}"}

    async def _handle_client_create(self, text: str, context: VoiceContext):
        from app.agents.base_agent import AgentResponse
        from app.schemas.intents import AgentType

        session = self.state_manager.get_session(context.session_id, context.user_id, context.org_uuid)
        raw_text = (getattr(context, "raw_text", None) or text or "").strip()
        draft = dict(session.client_draft or {})
        entities = {
            e["type"]: e["value"]
            for e in (context.extracted_entities or [])
            if e.get("type") and e.get("value") is not None
        }

        logger.info({"event": "client_create_attempt", "draft": draft, "entities": entities, "org_uuid": context.org_uuid})

        # Guard: reject if org_uuid is still in Clerk format
        if context.org_uuid.startswith("org_"):
            logger.warning({"event": "client_create_blocked_unresolved_org", "org_uuid": context.org_uuid})
            return AgentResponse(
                success=False,
                message="I'm having trouble identifying your account. Please try again in a moment.",
                agent_type=AgentType.FINANCE_AGENT,
            )

        session.locked_intent = "CLIENT_CREATE"
        session.dialog_pending = False
        session.dialog_id = None

        self._seed_client_draft_from_entities(draft, entities)

        previous_question = draft.get("last_question_asked")
        if previous_question and raw_text and raw_text != "[UI_form_submission]":
            answered = self._apply_client_followup_answer(draft, raw_text, entities)
            if not answered:
                session.client_draft = draft
                self.state_manager.save_session(session)
                return AgentResponse(
                    success=True,
                    message=self._get_client_retry_prompt(previous_question),
                    agent_type=AgentType.FINANCE_AGENT,
                    needs_clarification=True,
                )

        next_field, next_prompt = self._get_next_client_prompt(draft)
        if next_field:
            draft["last_question_asked"] = next_field
            session.client_draft = draft
            self.state_manager.save_session(session)
            return AgentResponse(
                success=True,
                message=next_prompt,
                agent_type=AgentType.FINANCE_AGENT,
                needs_clarification=True,
            )

        draft["last_question_asked"] = None
        session.client_draft = draft
        self.state_manager.save_session(session)

        result = await self.finalize_client_create(session)
        return AgentResponse(
            success=result.get("success", False),
            message=result.get("response_text", "I couldn't save that client right now."),
            agent_type=AgentType.FINANCE_AGENT,
            ui_event=result.get("ui_event"),
        )
        
        if not name:
            # Problem 1 Fix: SET THE LOCK before returning so next utterance stays in CLIENT_CREATE context
            session = self.state_manager.get_session(context.session_id)
            session.locked_intent = "CLIENT_CREATE"
            if not session.client_draft:
                session.client_draft = {}
            self.state_manager.save_session(session)
            
            return AgentResponse(
                success=False,
                message="Got it. What's the name of the business you'd like to add?",
                agent_type=AgentType.FINANCE_AGENT,
                needs_clarification=True,
            )
        
        # 🧠 Intelligence Layer
        raw_text = text if text else str(entities)
        city = entities.get("address", "an unknown location")
        industry = self._infer_industry(raw_text)
        lead_score = self._calculate_lead_score(raw_text, city)
        smart_notes = self._generate_smart_notes(name, city, industry)

        # 🚀 UI PREVIEW DIALOG
        # Always show preview dialog once we have the name
        dialog_fields = [
            {"id": "name", "label": "Client Name", "type": "text", "defaultValue": name, "required": True},
            {"id": "email", "label": "Email Address", "type": "email", "defaultValue": entities.get("email", ""), "required": False},
            {"id": "phone", "label": "Phone Number", "type": "tel", "defaultValue": entities.get("phone", ""), "required": False},
            {"id": "address", "label": "City / Address", "type": "text", "defaultValue": city if city != "an unknown location" else "", "required": False},
            {"id": "gst_number", "label": "GST / Tax ID", "type": "text", "defaultValue": entities.get("gst_number") or entities.get("tax_id") or "", "required": False},
            {"id": "teamActionCode", "label": "Team Security Code", "type": "password", "defaultValue": "", "required": True},
        ]

        session = self.state_manager.get_session(context.session_id)
        session.dialog_pending = True
        session.dialog_id = "client_preview_form"
        # Update draft with current entities
        if not session.client_draft: session.client_draft = {}
        session.client_draft.update(entities)
        self.state_manager.save_session(session)
        
        needs_contact_details = not entities.get("phone") or not entities.get("email")
        message = f"I've prepared a draft for {name}. "
        if needs_contact_details:
            message += "I'm missing some contact details - you can add them in the preview window I've opened. "
        message += "Does everything look correct, or should I change something?"

        return AgentResponse(
            success=True,
            message=message,
            agent_type=AgentType.FINANCE_AGENT,
            ui_event={
                "type": "open_input_dialog",
                "dialog_id": "client_preview_form",
                "session_id": context.session_id,
                "title": f"Preview: {name}",
                "message": "Review and edit client details below.",
                "fields": dialog_fields,
                "submit_btn_label": "Update Draft",
                "submit_endpoint": "/api/v1/voice/dialog-response"
            }
        )

    async def _handle_client_query(self, text: str, context: VoiceContext, session):
        from app.agents.base_agent import AgentResponse
        from app.schemas.intents import AgentType

        try:
            if self._is_top_client_query(text):
                top_client_response = await self.backend.get_client_revenue_summary(
                    str(context.business_id or 1),
                    context.org_uuid,
                    limit=5,
                    user_id=context.user_id,
                )
                top_clients = top_client_response.data.get("topClients", []) if top_client_response.success and isinstance(top_client_response.data, dict) else []
                if top_clients:
                    leader = top_clients[0]
                    leader_name = leader.get("clientName") or "Unknown Client"
                    leader_id = leader.get("clientId") or leader.get("id")
                    self._set_focused_client(session, leader_id, leader_name)
                    invoice_count = int(leader.get("invoiceCount") or 0)
                    message = (
                        f"Your top paying client is {leader_name}. "
                        f"They've generated billed revenue of {self._format_rupees(leader.get('billedRevenue'))}, "
                        f"with {self._format_rupees(leader.get('collectedRevenue'))} collected"
                    )
                    if invoice_count > 0:
                        message += f" across {invoice_count} invoices"
                    outstanding_amount = float(leader.get("outstandingRevenue") or 0)
                    if outstanding_amount > 0:
                        message += f", and {self._format_rupees(outstanding_amount)} is still outstanding"
                    return AgentResponse(
                        success=True,
                        message=message + ".",
                        agent_type=AgentType.FINANCE_AGENT,
                    )

            if self._should_handle_client_business_query(text, context, session):
                client = await self._resolve_client_reference(text, context, session)
                if client and client.get("id"):
                    client_detail_response = await self.backend.get_client_revenue_detail(
                        str(context.business_id or 1),
                        client.get("id"),
                        context.org_uuid,
                        user_id=context.user_id,
                    )
                    if client_detail_response.success and isinstance(client_detail_response.data, dict):
                        data = client_detail_response.data
                        client_name = data.get("clientName") or client.get("name") or "That client"
                        self._set_focused_client(session, client.get("id"), client_name)
                        invoice_count = int(data.get("invoiceCount") or 0)

                        if self._is_client_invoice_count_query(text):
                            return AgentResponse(
                                success=True,
                                message=f"{client_name} has {invoice_count} invoice{'s' if invoice_count != 1 else ''} in the system.",
                                agent_type=AgentType.FINANCE_AGENT,
                            )

                        return AgentResponse(
                            success=True,
                            message=(
                                f"{client_name} has generated billed revenue of {self._format_rupees(data.get('billedRevenue'))}, "
                                f"with {self._format_rupees(data.get('collectedRevenue'))} collected and "
                                f"{self._format_rupees(data.get('outstandingRevenue'))} outstanding across "
                                f"{invoice_count} invoice{'s' if invoice_count != 1 else ''}."
                            ),
                            agent_type=AgentType.FINANCE_AGENT,
                        )

            clients = await self.backend.get_clients(context.org_uuid, user_id=context.user_id)
            if not clients:
                return AgentResponse(
                    success=True,
                    message="You have no clients yet. Say 'add a client' to get started.",
                    agent_type=AgentType.FINANCE_AGENT,
                )
            names = [c.get("name", "") for c in clients[:5]]
            count = len(clients)
            return AgentResponse(
                success=True,
                message=f"You have {count} client{'s' if count > 1 else ''}. {', '.join(names[:3])}{'and more' if count > 3 else ''}.",
                agent_type=AgentType.FINANCE_AGENT,
            )
        except Exception as e:
            return AgentResponse(
                success=False,
                message="Couldn't fetch clients right now.",
                agent_type=AgentType.FINANCE_AGENT,
                error=str(e),
            )

voice_processor = VoiceProcessor()
