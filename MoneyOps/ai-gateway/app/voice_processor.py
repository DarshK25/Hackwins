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

    async def process(self, text: str, context: VoiceContext) -> dict:
        session = self.state_manager.get_session(context.session_id, context.user_id, context.org_uuid)
        
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
            collected_entities=session.invoice_draft.__dict__ if session.invoice_draft else session.client_draft
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
                
                if result.success:
                    self.state_manager.add_turn(context.session_id, "user", text, "INVOICE_CREATE")
                    self.state_manager.add_turn(context.session_id, "assistant", result.message, "INVOICE_CREATE")
                
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

            confirm_words = {"yes", "yeah", "yep", "sure", "ok", "okay", "correct", "proceed", "go ahead", "save it", "save", "save client"}
            if any(w in text.lower().strip() for w in confirm_words):
                # Finalize!
                result = await self.finalize_client_create(session)
                if result.get("success"):
                    session.locked_intent = None
                    session.client_draft = None
                    session.dialog_pending = False
                    self.state_manager.save_session(session)
                
                return {
                    "response_text": result.get("response_text"),
                    "success": result.get("success"),
                    "intent": "CLIENT_CREATE",
                    "ui_event": result.get("ui_event")
                }

            if intent_val not in (
                Intent.CLIENT_CREATE.value, Intent.CLIENT_UPDATE.value, 
                Intent.CONFIRMATION.value, Intent.CANCELLATION.value, 
                Intent.GENERAL_QUERY.value, Intent.GREETING.value,
                Intent.FOLLOWUP_QUESTION.value, Intent.CLARIFICATION_REQUEST.value
            ):
                session.locked_intent = None
            else:
                result = await self._handle_client_create(text, context)
                return {
                    "response_text": result.message,
                    "success": result.success,
                    "intent": "CLIENT_CREATE",
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
            "BUSINESS_HEALTH_CHECK", "FORECAST_REQUEST", "ANALYTICS_QUERY",
            "BUDGET_OPTIMIZATION", "CASH_FLOW_PLANNING", "PROFIT_OPTIMIZATION",
            "CUSTOMER_RETENTION",
        }

        if intent == "INVOICE_CREATE":
            result = await self.finance_agent.handle_invoice_create(context)
        elif intent == "CLIENT_CREATE":
            session.locked_intent = "CLIENT_CREATE"
            # Keep existing draft if we are just entering context again
            if not session.client_draft:
                session.client_draft = {}
            session.dialog_pending = False 
            self.state_manager.save_session(session)
            result = await self._handle_client_create(text, context)
        elif intent == "CLIENT_QUERY":
            result = await self._handle_client_query(context)
        elif intent in MARKET_INTENTS:
            from app.agents.market_agent import market_agent_instance
            result = await market_agent_instance.handle_market_query(
                text, context, 
                conversation_history=session.history
            )
        elif intent == "GENERAL_QUERY":
            # Check if it's a market/world question
            market_keywords = {
                "market", "sector", "industry", "economy", "world", "global",
                "india", "growth", "competitor", "business", "trend", "situation",
                "geopolitical", "policy", "rate", "inflation", "tariff"
            }
            if any(w in text.lower() for w in market_keywords):
                from app.agents.market_agent import market_agent_instance
                result = await market_agent_instance.handle_market_query(
                    text, context,
                    conversation_history=session.history
                )
            else:
                from app.orchestration.agent_router import agent_router
                agent_resp = await agent_router.route(
                    classification.intent, 
                    {e["type"]: e["value"] for e in context.extracted_entities}, 
                    vars(context) if not isinstance(context, dict) else context
                )
                result = agent_resp
        else:
            # Fallback to general agent or other handlers
            from app.orchestration.agent_router import agent_router
            agent_resp = await agent_router.route(
                classification.intent, 
                {e["type"]: e["value"] for e in context.extracted_entities}, 
                vars(context) if not isinstance(context, dict) else context
            )
            result = agent_resp

        if result.success:
            self.state_manager.add_turn(context.session_id, "user", text, intent)
            self.state_manager.add_turn(context.session_id, "assistant", result.message, intent)

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
        """Finalize client creation after UI dialog submission."""
        from app.agents.base_agent import AgentResponse
        from app.schemas.intents import AgentType

        draft = session.client_draft
        name = draft.get("client_name") or draft.get("company_name")
        city = draft.get("city") or draft.get("address", "an unknown location")
        team_code = draft.get("teamActionCode") or draft.get("team_action_code")

        if not team_code:
            # Avoid backend call; we must have the PIN before creating.
            return {
                "success": False,
                "response_text": "To confirm client creation, please enter your team security code.",
                "ui_event": {
                    "type": "open_input_dialog",
                    "dialog_id": "client_preview_form",
                    "session_id": session.session_id,
                    "title": "Team Code Required",
                    "message": "Please enter your team security code to confirm adding this client.",
                    "fields": [
                        {"id": "teamActionCode", "label": "Team Security Code", "type": "password", "defaultValue": "", "required": True}
                    ],
                    "submit_btn_label": "Submit Code",
                    "submit_endpoint": "/api/v1/voice/dialog-response"
                }
            }
        
        # Recalculate notes/score with any new data
        industry = self._infer_industry(str(draft))
        lead_score = self._calculate_lead_score(str(draft), city)
        smart_notes = self._generate_smart_notes(name, city, industry)

        try:
            resp = await self.backend._request(
                "POST", "/api/clients",
                org_id=session.org_id,
                user_id=session.user_id,
                data={
                    "name": name,
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
                # Trigger dashboard refresh
                ui_event = {
                    "type": "client_created",
                    "client_id": resp.data.get("id") if isinstance(resp.data, dict) else None,
                    "name": name,
                    "toast": {
                        "title": "Client Saved",
                        "variant": "success",
                        "message": f"Added {name} to CRM."
                    }
                }
                
                # We return the response text and ui_event to be published by the caller (voice.py)
                return {
                    "success": True,
                    "response_text": f"Success! I've added {name} to your CRM. {smart_notes.split('.')[0]}.",
                    "ui_event": ui_event
                }
            else:
                err = resp.error if resp else "Unknown"
                if "Invalid team security code" in str(err):
                    return {"success": False, "response_text": "The security code is incorrect. Please try again."}
                if "Team security code is required" in str(err):
                    return {"success": False, "response_text": "The security code is required. Please try again."}
                return {"success": False, "response_text": f"Error saving client: {err}"}
        except Exception as e:
            logger.error("client_finalize_error", error=str(e))
            return {"success": False, "response_text": f"Critical error: {str(e)}"}

    async def _handle_client_create(self, text: str, context: VoiceContext):
        from app.agents.base_agent import AgentResponse
        from app.schemas.intents import AgentType
        
        entities = {e["type"]: e["value"] for e in (context.extracted_entities or [])}
        name = entities.get("client_name") or entities.get("company_name")
        
        logger.info({"event": "client_create_attempt", "name": name, "entities": entities, "org_uuid": context.org_uuid})
        
        # Guard: reject if org_uuid is still in Clerk format
        if context.org_uuid.startswith("org_"):
            logger.warning({"event": "client_create_blocked_unresolved_org", "org_uuid": context.org_uuid})
            return AgentResponse(
                success=False,
                message="I'm having trouble identifying your account. Please try again in a moment.",
                agent_type=AgentType.FINANCE_AGENT,
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
        
        message = f"I've prepared a draft for {name}. "
        if not entities.get("phone") or not entities.get("email"):
            message += "I'm missing some contact details—you can add them in the preview window I've opened. "
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

    async def _handle_client_query(self, context):
        from app.agents.base_agent import AgentResponse
        from app.schemas.intents import AgentType

        try:
            clients = await self.backend.get_clients(context.org_uuid)
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
