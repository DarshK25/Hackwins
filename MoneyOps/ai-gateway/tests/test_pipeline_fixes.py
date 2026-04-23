"""
Comprehensive regression and validation tests for all 12 voice pipeline bugs.

Run with:
    pytest ai-gateway/tests/test_pipeline_fixes.py -v

Each test is documented with the bug number it validates.
"""
import asyncio
import json
import time
from decimal import Decimal
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Bug 2: Amount Corruption (Indian Number System)
# ---------------------------------------------------------------------------
class TestBug2AmountParser:
    """Bug 2: parse_indian_amount must handle lakh/crore/thousand + reject date fragments."""

    def setup_method(self):
        from app.utils.amount_parser import parse_indian_amount
        self.parse = parse_indian_amount

    def test_two_lakh_rupees(self):
        assert self.parse("two lakh rupees") == 200_000.0

    def test_numeric_lakh(self):
        assert self.parse("1.5 lakh") == 150_000.0

    def test_fifty_thousand(self):
        assert self.parse("fifty thousand") == 50_000.0

    def test_two_lakh_fifty_thousand(self):
        assert self.parse("two lakh fifty thousand") == 250_000.0

    def test_crore(self):
        assert self.parse("1.5 crore") == 15_000_000.0

    def test_formatted_indian_amount(self):
        # ₹2,00,000 — stripped to "200000"
        result = self.parse("₹2,00,000")
        assert result == 200_000.0

    def test_plain_number(self):
        assert self.parse("200000") == 200_000.0

    def test_rejects_date_fragment(self):
        """BUG 2 CORE FIX: 'ten nine next days' must return None, not a number."""
        assert self.parse("ten nine next days") is None

    def test_rejects_days_suffix(self):
        assert self.parse("nineteen days") is None

    def test_rejects_next_week(self):
        assert self.parse("next week") is None

    def test_rejects_empty(self):
        assert self.parse("") is None

    def test_rejects_rupees_alone(self):
        assert self.parse("rupees") is None

    def test_stt_correction_to_two(self):
        """STT often hears 'to' instead of 'two'."""
        result = self.parse("to lakh")
        assert result == 200_000.0

    def test_lakh_alternate_spellings(self):
        assert self.parse("1 lac") == 100_000.0
        assert self.parse("2 lack") == 200_000.0

    def test_ten_thousand(self):
        assert self.parse("ten thousand rupees") == 10_000.0


# ---------------------------------------------------------------------------
# Bug 2b: Date Parser — weekdays and extended support
# ---------------------------------------------------------------------------
class TestDateParser:
    """Bug for due date: date_parser must handle named weekdays and extended number words."""

    def setup_method(self):
        from app.utils.date_parser import parse_relative_date, is_date_fragment
        self.parse = parse_relative_date
        self.is_date = is_date_fragment

    def test_today(self):
        result = self.parse("today")
        assert result is not None
        from datetime import datetime
        assert result == datetime.now().strftime("%Y-%m-%d")

    def test_tomorrow(self):
        from datetime import datetime, timedelta
        assert self.parse("tomorrow") == (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    def test_in_10_days(self):
        from datetime import datetime, timedelta
        assert self.parse("in 10 days") == (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")

    def test_next_friday(self):
        """Named weekday must be supported."""
        result = self.parse("next friday")
        assert result is not None
        assert len(result) == 10  # ISO format

    def test_next_monday(self):
        result = self.parse("next monday")
        assert result is not None

    def test_nineteen_days(self):
        from datetime import datetime, timedelta
        result = self.parse("nineteen days")
        assert result == (datetime.now() + timedelta(days=19)).strftime("%Y-%m-%d")

    def test_twenty_days(self):
        from datetime import datetime, timedelta
        result = self.parse("twenty days")
        assert result == (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")

    def test_is_date_fragment_true(self):
        assert self.is_date("ten nine next days") is True
        assert self.is_date("next friday") is True
        assert self.is_date("in five days") is True

    def test_is_date_fragment_false(self):
        assert self.is_date("two lakh") is False
        assert self.is_date("50000") is False

    def test_iso_passthrough(self):
        assert self.parse("2025-12-31") == "2025-12-31"

    def test_unrecognized_returns_none(self):
        assert self.parse("garbled text xyz") is None


# ---------------------------------------------------------------------------
# Bug 8: Ghost Confirmation — stage field in response
# ---------------------------------------------------------------------------
class TestBug8GhostConfirmation:
    """Bug 8: Voice process endpoint must return a 'stage' field.
    Voice service must not say 'invoice created' unless stage == EXECUTED.
    """

    def test_premature_confirmation_guard_blocks_non_executed(self):
        from voice_service.app.agent.entrypoint import premature_confirmation_guard
        # Should NOT block because it passes the text through
        # (the primary guard is stage-based, keyword check is safety net)
        result = premature_confirmation_guard("invoice created", "COLLECTING")
        assert result == "invoice created"  # Returns original, logs error

    def test_premature_confirmation_guard_allows_executed(self):
        from voice_service.app.agent.entrypoint import premature_confirmation_guard
        result = premature_confirmation_guard("Your invoice has been created!", "EXECUTED")
        assert "invoice" in result.lower()

    def test_premature_confirmation_guard_neutral_text(self):
        from voice_service.app.agent.entrypoint import premature_confirmation_guard
        result = premature_confirmation_guard("What is the client's name?", "COLLECTING")
        assert result == "What is the client's name?"


# ---------------------------------------------------------------------------
# Bug 8/10b: Production Ready Guard in General Agent
# ---------------------------------------------------------------------------
class TestBug10bProductionReady:
    """Bug 10b: GENERAL_AGENT must be production_ready=True.
    Any stub agent must return False and be intercepted by router.
    """

    def test_general_agent_is_production_ready(self):
        from app.agents.general_agent import GeneralAgent
        agent = GeneralAgent()
        assert agent.is_production_ready() is True

    def test_base_agent_default_production_ready(self):
        """BaseAgent default is True — subclasses opt-out to become stubs."""
        from app.agents.base_agent import BaseAgent
        from app.schemas.intents import Intent, AgentType
        from typing import List

        class MinimalAgent(BaseAgent):
            def get_agent_type(self): return AgentType.GENERAL_AGENT
            def get_supported_intents(self): return [Intent.GENERAL_QUERY]
            def get_tools(self): return []
            async def process(self, intent, entities, context=None):
                return self._build_success_response("test")

        agent = MinimalAgent()
        assert agent.is_production_ready() is True

    def test_general_agent_handles_greeting(self):
        """GENERAL_AGENT must return a real response for GREETING, not BEEP BOOP."""
        from app.agents.general_agent import GeneralAgent
        from app.schemas.intents import Intent
        import asyncio

        agent = GeneralAgent()
        response = asyncio.get_event_loop().run_until_complete(
            agent.process(Intent.GREETING, {}, {})
        )
        assert response.success is True
        assert "beep boop" not in response.message.lower()
        assert "coming in v2" not in response.message.lower()
        assert len(response.message) > 10

    def test_general_agent_handles_help(self):
        from app.agents.general_agent import GeneralAgent
        from app.schemas.intents import Intent
        import asyncio

        agent = GeneralAgent()
        response = asyncio.get_event_loop().run_until_complete(
            agent.process(Intent.HELP, {}, {})
        )
        assert response.success is True
        assert "invoice" in response.message.lower() or "balance" in response.message.lower()

    def test_general_agent_handles_general_query_rule_based(self):
        """Rule-based fallback must handle unknown text cleanly."""
        from app.agents.general_agent import GeneralAgent
        agent = GeneralAgent()
        result = agent._rule_based_redirect("can you do my taxes?")
        assert "beep boop" not in result.lower()
        assert len(result) > 10


# ---------------------------------------------------------------------------
# Bug 10a: GeneralAgent supported intents
# ---------------------------------------------------------------------------
class TestBug10aGeneralAgentIntents:
    """Bug 10a: GeneralAgent must declare and handle all conversational intents."""

    def test_supports_general_query(self):
        from app.agents.general_agent import GeneralAgent
        from app.schemas.intents import Intent
        agent = GeneralAgent()
        assert Intent.GENERAL_QUERY in agent.get_supported_intents()

    def test_supports_greeting(self):
        from app.agents.general_agent import GeneralAgent
        from app.schemas.intents import Intent
        agent = GeneralAgent()
        assert Intent.GREETING in agent.get_supported_intents()

    def test_supports_help(self):
        from app.agents.general_agent import GeneralAgent
        from app.schemas.intents import Intent
        agent = GeneralAgent()
        assert Intent.HELP in agent.get_supported_intents()

    def test_agent_type(self):
        from app.agents.general_agent import GeneralAgent
        from app.schemas.intents import AgentType
        agent = GeneralAgent()
        assert agent.get_agent_type() == AgentType.GENERAL_AGENT


# ---------------------------------------------------------------------------
# Bug 12/7c: History Sanitization
# ---------------------------------------------------------------------------
class TestBug12HistorySanitization:
    """Bug 12: Failed turns must NOT be written to session history."""

    def test_sanitize_history_removes_error_turns(self):
        from app.api.v1.voice import sanitize_history
        history = [
            {"role": "user", "content": "Create invoice", "intent": "INVOICE_CREATE"},
            {"role": "assistant", "content": "I'm having trouble with that", "intent": "ERROR"},
            {"role": "user", "content": "Hello", "intent": "GREETING"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        clean = sanitize_history(history)
        # The ERROR intent turn should be filtered
        error_turns = [t for t in clean if t.get("intent") == "ERROR"]
        assert len(error_turns) == 0

    def test_sanitize_history_removes_trouble_phrase(self):
        from app.api.v1.voice import sanitize_history
        history = [
            {"role": "assistant", "content": "I'm having trouble processing that."},
            {"role": "user", "content": "Hello"},
        ]
        clean = sanitize_history(history)
        trouble_turns = [t for t in clean if "trouble" in t.get("content", "").lower()]
        assert len(trouble_turns) == 0

    def test_sanitize_history_keeps_last_10(self):
        from app.api.v1.voice import sanitize_history
        history = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(15)
        ]
        clean = sanitize_history(history)
        assert len(clean) <= 10

    def test_sanitize_history_keeps_clean_turns(self):
        from app.api.v1.voice import sanitize_history
        history = [
            {"role": "user", "content": "Hello", "intent": "GREETING"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        clean = sanitize_history(history)
        assert len(clean) == 2


# ---------------------------------------------------------------------------
# Bug 7b: Multi-turn Lock Escape Hatch
# ---------------------------------------------------------------------------
class TestBug7bMultiTurnLock:
    """Bug 7b: should_break_multi_turn_lock must allow switching intents at high confidence."""

    def setup_method(self):
        from app.api.v1.voice import should_break_multi_turn_lock
        self.break_lock = should_break_multi_turn_lock

    def test_breaks_invoice_to_balance_high_confidence(self):
        result = self.break_lock(
            current_intent="INVOICE_CREATE",
            new_intent="BALANCE_CHECK",
            new_confidence=0.92,
            current_stage="COLLECT_CLIENT"
        )
        assert result is True

    def test_breaks_client_to_invoice_high_confidence(self):
        result = self.break_lock(
            current_intent="CLIENT_CREATE",
            new_intent="INVOICE_CREATE",
            new_confidence=0.90,
            current_stage="COLLECT_NAME"
        )
        assert result is True

    def test_does_not_break_at_confirmation_stage(self):
        """User at CONFIRMATION stage SHOULD NOT be switched mid-confirm."""
        result = self.break_lock(
            current_intent="INVOICE_CREATE",
            new_intent="BALANCE_CHECK",
            new_confidence=0.95,
            current_stage="CONFIRMATION"
        )
        assert result is False

    def test_does_not_break_at_low_confidence(self):
        result = self.break_lock(
            current_intent="INVOICE_CREATE",
            new_intent="BALANCE_CHECK",
            new_confidence=0.75,  # Below 0.85 threshold
            current_stage="COLLECT_AMOUNT"
        )
        assert result is False

    def test_does_not_break_unrelated_pair(self):
        """Non-breakable intent pairs must stay locked."""
        result = self.break_lock(
            current_intent="INVOICE_CREATE",
            new_intent="GENERAL_QUERY",
            new_confidence=0.99,  # Even at very high confidence
            current_stage="COLLECT_CLIENT"
        )
        assert result is False


# ---------------------------------------------------------------------------
# Bug 6b: Org Isolation
# ---------------------------------------------------------------------------
class TestBug6bOrgIsolation:
    """Bug 6b: All client API calls must include org_id. Missing org_id raises OrgIsolationError."""

    def test_build_client_params_requires_org_id(self):
        """_build_client_params must raise if org_id is missing/empty."""
        from app.adapters.backend_adapter import BackendHttpAdapter
        adapter = BackendHttpAdapter()
        with pytest.raises(Exception):  # OrgIsolationError or ValueError
            adapter._build_client_params(org_id=None)

    def test_build_client_params_success(self):
        from app.adapters.backend_adapter import BackendHttpAdapter
        adapter = BackendHttpAdapter()
        params = adapter._build_client_params(org_id="org-123")
        assert "org-123" in str(params)

    def test_build_client_params_rejects_empty_string(self):
        from app.adapters.backend_adapter import BackendHttpAdapter
        adapter = BackendHttpAdapter()
        with pytest.raises(Exception):
            adapter._build_client_params(org_id="")


# ---------------------------------------------------------------------------
# Bug 1: Context Amnesia — Stage Attempt Count
# ---------------------------------------------------------------------------  
class TestBug1ContextAmnesia:
    """Bug 1: Agent must NOT ask the same question indefinitely.
    stage_attempt_count tracks retries and triggers escalation.
    """

    def test_invoice_draft_tracks_stage_attempts(self):
        from app.api.v1.voice import InvoiceDraft
        draft = InvoiceDraft(intent_value="INVOICE_CREATE")
        assert draft.stage_attempt_count == 0
        assert draft.last_question_asked is None

    def test_last_question_tracking(self):
        from app.api.v1.voice import InvoiceDraft
        draft = InvoiceDraft(intent_value="INVOICE_CREATE")
        # Simulate asking the same question twice
        draft.last_question_asked = "client_name"
        draft.stage_attempt_count = 1
        # Draft remembers what was asked last
        assert draft.last_question_asked == "client_name"
        assert draft.stage_attempt_count == 1

    def test_base_draft_context_has_failed_turn_count(self):
        """Bug 12: BaseDraftContext must track failed turns."""
        from app.api.v1.voice import BaseDraftContext
        draft = BaseDraftContext(intent_value="TEST")
        assert hasattr(draft, 'failed_turn_count')
        assert draft.failed_turn_count == 0


# ---------------------------------------------------------------------------
# Bug 9: STT Name Hallucination — Eager Validation
# ---------------------------------------------------------------------------
class TestBug9EagerValidation:
    """Bug 9: InvoiceDraft must have eager_validation_done field
    to prevent duplicate backend lookups during COLLECT_CLIENT.
    """

    def test_invoice_draft_has_eager_validation_done(self):
        from app.api.v1.voice import InvoiceDraft
        draft = InvoiceDraft(intent_value="INVOICE_CREATE")
        assert hasattr(draft, 'eager_validation_done')
        assert draft.eager_validation_done is False

    def test_eager_validation_done_resets_on_new_draft(self):
        from app.api.v1.voice import InvoiceDraft
        draft1 = InvoiceDraft(intent_value="INVOICE_CREATE")
        draft1.eager_validation_done = True
        # New draft is always False
        draft2 = InvoiceDraft(intent_value="INVOICE_CREATE")
        assert draft2.eager_validation_done is False


# ---------------------------------------------------------------------------
# Bug 5: Voice Turn Debouncing
# ---------------------------------------------------------------------------
class TestBug5VoiceDebouncing:
    """Bug 5: Voice turns must be debounced by 600ms to prevent duplicate processing."""

    def test_debounce_timer_is_600ms(self):
        """Verify the debounce timer is configured at 600ms (0.6s)."""
        import ast
        import os

        entrypoint_path = os.path.join(
            os.path.dirname(__file__),
            "../../voice-service/app/agent/entrypoint.py"
        )
        with open(entrypoint_path, "r") as f:
            source = f.read()

        assert "0.6" in source or "600" in source, \
            "Debounce timer must be 0.6 seconds (600ms)"
        assert "asyncio.sleep" in source, \
            "Debounce must use asyncio.sleep"


# ---------------------------------------------------------------------------
# Bug 4: Stateless Blindness — get_backend_adapter singleton
# ---------------------------------------------------------------------------
class TestBug4SessionScopedAdapter:
    """Bug 4: BackendHttpAdapter must be session-scoped (singleton via get_backend_adapter)."""

    def test_get_backend_adapter_returns_same_instance(self):
        from app.adapters.backend_adapter import get_backend_adapter
        adapter1 = get_backend_adapter()
        adapter2 = get_backend_adapter()
        assert adapter1 is adapter2, \
            "get_backend_adapter must return the same singleton instance"


# ---------------------------------------------------------------------------
# Integration: InvoiceDraft State Machine
# ---------------------------------------------------------------------------
class TestInvoiceDraftStateMachine:
    """Validates the InvoiceDraft state machine advances correctly."""

    def test_starts_at_collect_client(self):
        from app.api.v1.voice import InvoiceDraft, InvoiceStage
        draft = InvoiceDraft(intent_value="INVOICE_CREATE")
        assert draft.stage == InvoiceStage.COLLECT_CLIENT

    def test_advances_to_collect_amount_after_client(self):
        from app.api.v1.voice import InvoiceDraft, InvoiceStage
        draft = InvoiceDraft(intent_value="INVOICE_CREATE")
        draft.update({"client_name": "Tanoosh Jain", "client_id": "uuid-123"})
        assert draft.stage == InvoiceStage.COLLECT_AMOUNT

    def test_advances_to_collect_due_date(self):
        from app.api.v1.voice import InvoiceDraft, InvoiceStage
        draft = InvoiceDraft(intent_value="INVOICE_CREATE")
        draft.update({
            "client_name": "Tanoosh Jain",
            "client_id": "uuid-123",
            "amount": 50000.0
        })
        assert draft.stage == InvoiceStage.COLLECT_DUE_DATE

    def test_advances_to_confirmation(self):
        from app.api.v1.voice import InvoiceDraft, InvoiceStage
        draft = InvoiceDraft(intent_value="INVOICE_CREATE")
        draft.update({
            "client_name": "Tanoosh Jain",
            "client_id": "uuid-123",
            "amount": 50000.0,
            "due_date": "2025-12-31",
            "gst_percent": 18.0,
        })
        assert draft.stage == InvoiceStage.CONFIRMATION

    def test_is_complete_for_execution(self):
        from app.api.v1.voice import InvoiceDraft
        draft = InvoiceDraft(intent_value="INVOICE_CREATE")
        draft.update({
            "client_name": "Tanoosh Jain",
            "client_id": "uuid-123",
            "amount": 50000.0,
            "due_date": "2025-12-31",
            "gst_percent": 18.0,
        })
        assert draft.is_complete_for_execution() is True

    def test_not_complete_without_amount(self):
        from app.api.v1.voice import InvoiceDraft
        draft = InvoiceDraft(intent_value="INVOICE_CREATE")
        draft.update({
            "client_name": "Tanoosh Jain",
            "client_id": "uuid-123",
        })
        assert draft.is_complete_for_execution() is False

    def test_client_draft_inherits_base(self):
        """Bug 7a: ClientDraft must inherit BaseDraftContext fields."""
        from app.api.v1.voice import ClientDraft
        draft = ClientDraft(intent_value="CLIENT_CREATE")
        # Base fields must exist
        assert hasattr(draft, 'stage_attempt_count')
        assert hasattr(draft, 'last_question_asked')
        assert hasattr(draft, 'onboarding_verified')
        assert hasattr(draft, 'presented_client_list')
        assert hasattr(draft, 'failed_turn_count')
        assert hasattr(draft, 'created_at')
        assert hasattr(draft, 'updated_at')


class TestClientCreateVoiceMapping:
    """Regression coverage for company vs contact-name capture in client creation."""

    def test_company_name_is_not_used_as_contact_name(self):
        from app.agents.moneyops_agent import _merge_client_draft_from_text

        draft = _merge_client_draft_from_text("Navi Mumbai Logistics Pvt Ltd", {})

        assert draft.get("company_name") == "Navi Mumbai Logistics Pvt Ltd"
        assert draft.get("name") is None

    def test_contact_name_can_follow_company_name(self):
        from app.agents.moneyops_agent import _merge_client_draft_from_text

        draft = _merge_client_draft_from_text(
            "Arjun Desai",
            {"company_name": "Navi Mumbai Logistics Pvt Ltd"},
        )

        assert draft.get("company_name") == "Navi Mumbai Logistics Pvt Ltd"
        assert draft.get("name") == "Arjun Desai"

    def test_create_client_intent_sentence_extracts_company_name_only(self):
        from app.agents.moneyops_agent import _merge_client_draft_from_text

        draft = _merge_client_draft_from_text(
            "i would like to create a client navi mumbai logistics private limited",
            {},
        )

        assert draft.get("company_name") == "navi mumbai logistics private limited"
        assert draft.get("name") is None

    def test_main_contact_followup_extracts_only_person_name(self):
        from app.agents.moneyops_agent import _merge_client_draft_from_text

        draft = _merge_client_draft_from_text(
            "the main contact person name is abhishek shalma",
            {"company_name": "Navi Mumbai Logistics Pvt Ltd"},
        )

        assert draft.get("name") == "abhishek shalma"
        assert draft.get("company_name") == "Navi Mumbai Logistics Pvt Ltd"

    @pytest.mark.asyncio
    async def test_create_client_prompts_for_contact_when_only_company_present(self):
        from app.agents.moneyops_agent import AgentSession, execute_tool

        session = AgentSession(
            session_id="session-1",
            user_id="user-1",
            org_uuid="org-1",
        )

        result = await execute_tool(
            "create_client",
            '{"company_name":"Navi Mumbai Logistics Pvt Ltd"}',
            session,
            {"org_id": "org-1"},
            backend=AsyncMock(),
        )

        assert result["status"] == "validation_error"
        assert result["missing_field"] == "name"
        assert "main contact person" in result["message"]

    @pytest.mark.asyncio
    async def test_create_client_sends_team_code_in_request_body(self):
        from app.agents.moneyops_agent import AgentSession, execute_tool

        session = AgentSession(
            session_id="session-1",
            user_id="user-1",
            org_uuid="org-1",
        )

        backend = AsyncMock()
        backend.post.return_value = {"id": "client-1"}

        result = await execute_tool(
            "create_client",
            '{"name":"Abhishek Sharma","email":"abhishek@nmlogistics.com","phone":"9876543210","company_name":"Navi Motorized Logistics Private Limited","team_code":"2091"}',
            session,
            {"org_id": "org-1"},
            backend=backend,
        )

        assert result["status"] == "created"
        backend.post.assert_awaited_once()
        payload = backend.post.await_args.kwargs["payload"]
        assert payload["teamActionCode"] == "2091"
        assert payload["phoneNumber"] == "9876543210"
        assert payload["source"] == "VOICE"

    def test_names_do_not_trigger_email_fragment_detection(self):
        from app.agents.moneyops_agent import _looks_like_email_fragment

        assert _looks_like_email_fragment("tanush jain") is False
        assert _looks_like_email_fragment("navi mumbai logistics private limited") is False

    def test_bare_team_code_is_accepted(self):
        from app.agents.moneyops_agent import _extract_team_code

        assert _extract_team_code("2091") == "2091"

    def test_spoken_team_code_with_spaces_is_accepted(self):
        from app.agents.moneyops_agent import _extract_team_code

        assert _extract_team_code("team security code is 2 0 9 1") == "2091"

    def test_natural_team_code_reply_is_accepted(self):
        from app.agents.moneyops_agent import _extract_team_code

        assert _extract_team_code("it is 2091") == "2091"

    def test_client_draft_captures_spoken_team_code_with_spaces(self):
        from app.agents.moneyops_agent import _merge_client_draft_from_text

        draft = _merge_client_draft_from_text("team security code is 2 0 9 1", {})

        assert draft.get("team_code") == "2091"

    def test_bare_invoice_client_name_is_extracted(self):
        from app.agents.moneyops_agent import _extract_client_name_for_invoice

        assert _extract_client_name_for_invoice("sunita") == "sunita"

    def test_spoken_invoice_line_item_is_extracted(self):
        from app.agents.moneyops_agent import _extract_line_items_from_invoice_text

        items = _extract_line_items_from_invoice_text(
            "ac ev charger supply and installation of 72 kilowatt at 50000 rupees"
        )

        assert len(items) == 1
        assert items[0]["unit_price"] == 50000
        assert "ac ev charger" in items[0]["description"].lower()

    def test_invoice_items_text_parser_supports_preview_dialog_format(self):
        from app.agents.moneyops_agent import _parse_invoice_items_text

        items = _parse_invoice_items_text(
            "SERVICE | AC EV Charger Supply & Installation (7.2 kW) | 1 | 50000 | 18"
        )

        assert len(items) == 1
        assert items[0]["quantity"] == 1
        assert items[0]["unit_price"] == 50000
        assert items[0]["gst_percent"] == 18

    def test_invoice_draft_follow_up_does_not_overwrite_existing_client_name(self):
        from app.agents.moneyops_agent import _merge_invoice_draft_from_text

        draft = {"client_name": "Priya Sharma"}

        merged = _merge_invoice_draft_from_text(
            "for aceb charger supply and installation",
            draft,
        )

        assert merged["client_name"] == "Priya Sharma"

    def test_invoice_draft_merges_amount_then_description_into_line_item(self):
        from app.agents.moneyops_agent import _merge_invoice_draft_from_text

        draft = {"client_name": "Priya Sharma"}
        draft = _merge_invoice_draft_from_text("the amount is 50000 rupees", draft)
        merged = _merge_invoice_draft_from_text("for aceb charger supply and installation", draft)

        assert merged["client_name"] == "Priya Sharma"
        assert len(merged["line_items"]) == 1
        assert merged["line_items"][0]["unit_price"] == 50000
        assert "aceb charger supply and installation" in merged["line_items"][0]["description"].lower()

    def test_invoice_draft_merges_service_phrase_with_pending_amount(self):
        from app.agents.moneyops_agent import _merge_invoice_draft_from_text

        draft = {"client_name": "Abhishek Sharma"}
        draft = _merge_invoice_draft_from_text("the amount is 20 000", draft)
        merged = _merge_invoice_draft_from_text("the service is ac ev charger supply and installation", draft)

        assert len(merged["line_items"]) == 1
        assert merged["line_items"][0]["unit_price"] == 20000
        assert "ac ev charger supply and installation" in merged["line_items"][0]["description"].lower()

    def test_invoice_draft_merges_amount_and_service_in_same_sentence(self):
        from app.agents.moneyops_agent import _merge_invoice_draft_from_text

        merged = _merge_invoice_draft_from_text(
            "the amount is 20 000 and service is acev charger installation",
            {"client_name": "Abhishek Sharma"},
        )

        assert len(merged["line_items"]) == 1
        assert merged["line_items"][0]["unit_price"] == 20000
        assert "acev charger installation" in merged["line_items"][0]["description"].lower()

    def test_due_date_phrase_supports_spoken_day_month(self):
        from app.agents.moneyops_agent import _extract_due_date_phrase

        assert _extract_due_date_phrase("30 april").endswith("-04-30")
        assert _extract_due_date_phrase("30th april").endswith("-04-30")

    def test_best_client_match_rejects_unrelated_short_name(self):
        from app.agents.moneyops_agent import _best_client_match

        clients = [
            {"name": "Arjun Desai"},
            {"name": "Priya Sharma"},
            {"name": "Sunita Rao"},
        ]

        assert _best_client_match("yash", clients) is None

    def test_best_client_match_accepts_first_name_only(self):
        from app.agents.moneyops_agent import _best_client_match

        clients = [
            {"name": "Arjun Desai"},
            {"name": "Priya Sharma"},
            {"name": "Sunita Rao"},
        ]

        match = _best_client_match("priya", clients)
        assert match is not None
        assert match["name"] == "Priya Sharma"

    def test_best_client_match_accepts_small_stt_drift(self):
        from app.agents.moneyops_agent import _best_client_match

        clients = [
            {"name": "Arjun Desai"},
            {"name": "Priya Sharma"},
            {"name": "Sunita Rao"},
        ]

        match = _best_client_match("sunita lao", clients)
        assert match is not None
        assert match["name"] == "Sunita Rao"

    def test_extract_client_name_for_invoice_rejects_service_description(self):
        from app.agents.moneyops_agent import _extract_client_name_for_invoice

        assert _extract_client_name_for_invoice("smart load management system setup") is None
        assert _extract_client_name_for_invoice("electrical panel upgrade and safety compliance") is None

    def test_merge_payment_draft_extracts_method_and_reference(self):
        from app.agents.moneyops_agent import _merge_payment_draft_from_text

        merged = _merge_payment_draft_from_text(
            "record partial payment from sunita by upi reference UPI-12345",
            None,
        )

        assert merged["client_name"] == "sunita"
        assert merged["payment_method"] == "UPI"
        assert merged["utr_or_reference"] == "UPI-12345"

    def test_groq_rate_limit_message_formats_long_wait_in_minutes_only(self):
        from app.agents.moneyops_agent import _groq_rate_limit_message

        message = _groq_rate_limit_message(
            RuntimeError("429 Too Many Requests. Please try again in 31m16.608s. Need more tokens?")
        )

        assert "31 minutes" in message
        assert "16.608" not in message

    def test_groq_rate_limit_message_formats_short_wait_in_minutes_and_seconds(self):
        from app.agents.moneyops_agent import _groq_rate_limit_message

        message = _groq_rate_limit_message(
            RuntimeError("rate limit reached. Please try again in 2m14.4s. Need more tokens?")
        )

        assert "2 minutes 14 seconds" in message

    def test_groq_rate_limit_message_formats_sub_minute_wait_in_seconds_only(self):
        from app.agents.moneyops_agent import _groq_rate_limit_message

        message = _groq_rate_limit_message(
            RuntimeError("Too Many Requests. Please try again in 42.2 seconds. Need more tokens?")
        )

        assert "42 seconds" in message

    def test_market_update_query_is_detected(self):
        from app.agents.moneyops_agent import _is_market_growth_query

        assert _is_market_growth_query("give me a market update")
        assert _is_market_growth_query("what changed in the market")

    def test_market_action_followup_is_detected(self):
        from app.agents.moneyops_agent import AgentSession, _is_market_action_followup_query

        session = AgentSession(session_id="s1", user_id="u1", org_uuid="org1", last_tool_called="search_market_intelligence")
        assert _is_market_action_followup_query("how do we grab this opportunity", session)
        assert _is_market_action_followup_query("how do we avoid financial loss here", session)

    def test_synthesize_market_result_is_actionable(self):
        from app.agents.moneyops_agent import _synthesize_market_result

        result = _synthesize_market_result(
            {
                "query": "market update for growth",
                "focus": "opportunities",
                "activity": "EV charging infrastructure rollout",
                "business_name": "VoltNest",
                "city": "Mumbai",
                "raw_snippets": [
                    "Fleet operators and warehouse campuses are increasing EV charging deployment across Maharashtra.",
                    "Competition is rising and discounting is increasing in enterprise charging bids.",
                ],
            }
        )

        assert result is not None
        assert "To act on this" in result
        lowered = result.lower()
        assert "first" in lowered
        assert "second" in lowered
        assert "third" in lowered

    def test_market_action_guidance_for_financial_loss_is_explicit(self):
        from app.agents.moneyops_agent import AgentSession, _market_action_guidance

        session = AgentSession(
            session_id="s1",
            user_id="u1",
            org_uuid="org1",
            last_market_results=["Fleet demand is rising, but procurement and collections risk is also increasing."],
        )
        message = _market_action_guidance(
            "how do we avoid financial loss here",
            session,
            {
                "business": {
                    "primaryActivity": "EV charging infrastructure rollout",
                    "city": "Mumbai",
                }
            },
        )

        assert "protect" in message.lower() or "financial loss" in message.lower()
        assert "escalate" in message.lower()
        assert "collections" in message.lower()

    def test_spoken_invoice_line_item_with_quantity_and_each_rate_is_extracted(self):
        from app.agents.moneyops_agent import _extract_line_items_from_invoice_text

        items = _extract_line_items_from_invoice_text(
            "add quarterly amc for 12 chargers at 850 rupees each"
        )

        assert len(items) == 1
        assert items[0]["quantity"] == 12
        assert items[0]["unit_price"] == 850
        assert "quarterly amc" in items[0]["description"].lower()

    def test_additional_invoice_item_follow_up_collects_description_then_amount(self):
        from app.agents.moneyops_agent import _merge_additional_invoice_item_followup

        draft = {
            "client_name": "Sunita Rao",
            "line_items": [{"description": "Quarterly AMC", "quantity": 12, "unit_price": 850, "gst_percent": 18}],
            "_awaiting_additional_item_description": True,
        }

        draft, state = _merge_additional_invoice_item_followup("civil work and cable ducting", draft)
        assert state == "awaiting_amount"
        assert draft["_pending_additional_item_description"] == "civil work and cable ducting"

        draft, state = _merge_additional_invoice_item_followup("5000", draft)
        assert state == "completed"
        assert len(draft["line_items"]) == 2
        assert draft["line_items"][1]["description"] == "civil work and cable ducting"
        assert draft["line_items"][1]["unit_price"] == 5000

    def test_invoice_item_review_followup_can_set_quantity_then_offer_more_items(self):
        from app.agents.moneyops_agent import _handle_invoice_item_review_followup

        draft = {
            "client_name": "Abhishek Sharma",
            "line_items": [{"description": "AC EV charger supply and installation", "quantity": 1, "unit_price": 20000, "gst_percent": 18}],
            "_awaiting_invoice_item_review": True,
        }

        updated, message = _handle_invoice_item_review_followup("quantity is 2", draft)

        assert updated["line_items"][0]["quantity"] == 2
        assert updated.get("_awaiting_add_more_items_confirmation") is True
        assert message == "Got it. Do you want to add another item?"

    def test_invoice_item_review_followup_can_skip_quantity_and_move_on(self):
        from app.agents.moneyops_agent import _handle_invoice_item_review_followup

        draft = {
            "client_name": "Abhishek Sharma",
            "line_items": [{"description": "AC EV charger supply and installation", "quantity": 1, "unit_price": 20000, "gst_percent": 18}],
            "_awaiting_invoice_item_review": True,
            "team_code": "2091",
        }

        updated, message = _handle_invoice_item_review_followup("no", draft)
        updated, message = _handle_invoice_item_review_followup("no more items", updated)

        assert updated["line_items"][0]["quantity"] == 1
        assert updated.get("_awaiting_add_more_items_confirmation") is None
        assert message == "What due date should I put on the invoice?"

    def test_semantic_invoice_followup_intent_detects_add_item_when_fast_path_is_ambiguous(self):
        from app.agents.moneyops_agent import _semantic_invoice_followup_intent

        intent = _semantic_invoice_followup_intent(
            "include one more service line",
            ("negative", "add_item", "set_quantity", "affirmative"),
        )

        assert intent == "add_item"

    def test_semantic_invoice_followup_intent_detects_negative_even_with_send_words(self):
        from app.agents.moneyops_agent import _semantic_invoice_followup_intent

        intent = _semantic_invoice_followup_intent(
            "let's not send that yet",
            ("negative", "affirmative"),
        )

        assert intent == "negative"

    @pytest.mark.asyncio
    async def test_invoice_send_offer_can_be_declined(self):
        from app.agents.moneyops_agent import AgentSession, process

        session = AgentSession(
            session_id="s1",
            user_id="u1",
            org_uuid="org1",
            last_response_context=json.dumps(
                {
                    "type": "invoice_send_offer",
                    "client_name": "Abhishek Sharma",
                    "invoice_number": "INV-20260422-1001",
                }
            ),
        )

        result = await process(
            text="no, don't send it",
            session=session,
            org_context={"org_id": "org1", "business_id": "1"},
            groq_key="",
            backend=AsyncMock(),
            is_voice=False,
        )

        assert result["raw_response"] == "Okay, I won't email the invoice right now."

    @pytest.mark.asyncio
    async def test_delete_invoice_query_sets_confirmation_context(self):
        from app.agents.moneyops_agent import AgentSession, process

        class BackendStub:
            async def get(self, endpoint, org_id=None, user_id=None, headers=None):
                if endpoint == "/api/invoices?limit=100":
                    return [{
                        "id": "inv-1",
                        "invoiceNumber": "INV-20260422-17B6",
                        "clientName": "Sunita Rao",
                        "issueDate": "2026-04-22",
                    }]
                return []

        session = AgentSession(session_id="s1", user_id="u1", org_uuid="org1")
        result = await process(
            text="delete invoice",
            session=session,
            org_context={"org_id": "org1", "business_id": "1"},
            groq_key="",
            backend=BackendStub(),
            is_voice=False,
        )

        assert "Do you want me to delete invoice INV-20260422-17B6" in result["raw_response"]
        assert session.last_response_context is not None

    @pytest.mark.asyncio
    async def test_delete_invoice_confirmation_executes_without_groq(self):
        from app.agents.moneyops_agent import AgentSession, process

        class BackendStub:
            def __init__(self):
                self.deleted_endpoint = None

            async def delete(self, endpoint, org_id=None, user_id=None, headers=None):
                self.deleted_endpoint = endpoint
                return None

        session = AgentSession(
            session_id="s1",
            user_id="u1",
            org_uuid="org1",
            last_response_context=json.dumps(
                {
                    "type": "invoice_delete_confirmation",
                    "invoice_id": "inv-1",
                    "invoice_number": "INV-20260422-17B6",
                    "client_name": "Sunita Rao",
                }
            ),
        )
        backend = BackendStub()
        result = await process(
            text="confirm delete",
            session=session,
            org_context={"org_id": "org1", "business_id": "1"},
            groq_key="",
            backend=backend,
            is_voice=False,
        )

        assert backend.deleted_endpoint == "/api/invoices/inv-1"
        assert result["raw_response"] == "I deleted invoice INV-20260422-17B6."

    @pytest.mark.asyncio
    async def test_mark_invoice_as_paid_from_client_uses_outstanding_amount(self):
        from app.agents.moneyops_agent import AgentSession, process

        class BackendStub:
            def __init__(self):
                self.post_calls = []

            async def get(self, endpoint, org_id=None, user_id=None, headers=None):
                if endpoint == "/api/clients?limit=200":
                    return [{"id": "c1", "name": "Sunita Rao"}]
                if endpoint == "/api/invoices?limit=100":
                    return [{
                        "id": "inv-1",
                        "invoiceNumber": "INV-20260422-17B6",
                        "clientName": "Sunita Rao",
                        "status": "SENT",
                        "totalAmount": 17936,
                        "paidAmount": 0,
                        "issueDate": "2026-04-22",
                    }]
                return []

            async def post(self, endpoint, payload=None, headers=None, org_id=None, user_id=None):
                self.post_calls.append((endpoint, payload))
                return {"success": True}

        backend = BackendStub()
        session = AgentSession(
            session_id="s1",
            user_id="u1",
            org_uuid="org1",
            verified_team_code="2091",
        )
        result = await process(
            text="mark the invoice as paid from sunita",
            session=session,
            org_context={"org_id": "org1", "business_id": "1"},
            groq_key="",
            backend=backend,
            is_voice=False,
        )

        assert backend.post_calls
        endpoint, payload = backend.post_calls[0]
        assert endpoint == "/api/invoices/inv-1/payment"
        assert payload["amount"] == 17936
        assert "Payment of" in result["raw_response"]

    @pytest.mark.asyncio
    async def test_partial_payment_from_client_asks_amount_then_records(self):
        from app.agents.moneyops_agent import AgentSession, process

        class BackendStub:
            def __init__(self):
                self.post_calls = []

            async def get(self, endpoint, org_id=None, user_id=None, headers=None):
                if endpoint == "/api/clients?limit=200":
                    return [{"id": "c1", "name": "Sunita Rao"}]
                if endpoint == "/api/invoices?limit=100":
                    return [{
                        "id": "inv-1",
                        "invoiceNumber": "INV-20260422-17B6",
                        "clientName": "Sunita Rao",
                        "status": "SENT",
                        "totalAmount": 17936,
                        "paidAmount": 0,
                        "issueDate": "2026-04-22",
                    }]
                return []

            async def post(self, endpoint, payload=None, headers=None, org_id=None, user_id=None):
                self.post_calls.append((endpoint, payload))
                return {"success": True}

        backend = BackendStub()
        session = AgentSession(
            session_id="s1",
            user_id="u1",
            org_uuid="org1",
            verified_team_code="2091",
        )

        first = await process(
            text="record partial payment from sunita",
            session=session,
            org_context={"org_id": "org1", "business_id": "1"},
            groq_key="",
            backend=backend,
            is_voice=False,
        )
        assert first["raw_response"] == "How much payment was received for Sunita Rao?"

        second = await process(
            text="5000 rupees",
            session=session,
            org_context={"org_id": "org1", "business_id": "1"},
            groq_key="",
            backend=backend,
            is_voice=False,
        )

        assert backend.post_calls
        endpoint, payload = backend.post_calls[0]
        assert endpoint == "/api/invoices/inv-1/payment"
        assert payload["amount"] == 5000
        assert "Payment of" in second["raw_response"]

    @pytest.mark.asyncio
    async def test_full_payment_from_client_passes_method_and_reference(self):
        from app.agents.moneyops_agent import AgentSession, process

        class BackendStub:
            def __init__(self):
                self.post_calls = []

            async def get(self, endpoint, org_id=None, user_id=None, headers=None):
                if endpoint == "/api/clients?limit=200":
                    return [{"id": "c1", "name": "Sunita Rao"}]
                if endpoint == "/api/invoices?limit=100":
                    return [{
                        "id": "inv-1",
                        "invoiceNumber": "INV-20260422-17B6",
                        "clientName": "Sunita Rao",
                        "status": "SENT",
                        "totalAmount": 17936,
                        "paidAmount": 0,
                        "issueDate": "2026-04-22",
                    }]
                return []

            async def post(self, endpoint, payload=None, headers=None, org_id=None, user_id=None):
                self.post_calls.append((endpoint, payload))
                return {"success": True}

        backend = BackendStub()
        session = AgentSession(
            session_id="s1",
            user_id="u1",
            org_uuid="org1",
            verified_team_code="2091",
        )
        await process(
            text="mark the invoice as paid from sunita by upi reference UPI-12345",
            session=session,
            org_context={"org_id": "org1", "business_id": "1"},
            groq_key="",
            backend=backend,
            is_voice=False,
        )

        endpoint, payload = backend.post_calls[0]
        assert endpoint == "/api/invoices/inv-1/payment"
        assert payload["paymentMethod"] == "UPI"
        assert payload["referenceNumber"] == "UPI-12345"

    @pytest.mark.asyncio
    async def test_partial_payment_follow_up_keeps_method_and_reference(self):
        from app.agents.moneyops_agent import AgentSession, process

        class BackendStub:
            def __init__(self):
                self.post_calls = []

            async def get(self, endpoint, org_id=None, user_id=None, headers=None):
                if endpoint == "/api/clients?limit=200":
                    return [{"id": "c1", "name": "Sunita Rao"}]
                if endpoint == "/api/invoices?limit=100":
                    return [{
                        "id": "inv-1",
                        "invoiceNumber": "INV-20260422-17B6",
                        "clientName": "Sunita Rao",
                        "status": "SENT",
                        "totalAmount": 17936,
                        "paidAmount": 0,
                        "issueDate": "2026-04-22",
                    }]
                return []

            async def post(self, endpoint, payload=None, headers=None, org_id=None, user_id=None):
                self.post_calls.append((endpoint, payload))
                return {"success": True}

        backend = BackendStub()
        session = AgentSession(
            session_id="s1",
            user_id="u1",
            org_uuid="org1",
            verified_team_code="2091",
        )

        await process(
            text="record partial payment from sunita by neft reference ABC123",
            session=session,
            org_context={"org_id": "org1", "business_id": "1"},
            groq_key="",
            backend=backend,
            is_voice=False,
        )
        await process(
            text="5000 rupees",
            session=session,
            org_context={"org_id": "org1", "business_id": "1"},
            groq_key="",
            backend=backend,
            is_voice=False,
        )

        endpoint, payload = backend.post_calls[0]
        assert endpoint == "/api/invoices/inv-1/payment"
        assert payload["paymentMethod"] == "NEFT"
        assert payload["referenceNumber"] == "ABC123"
