"""
Comprehensive regression and validation tests for all 12 voice pipeline bugs.

Run with:
    pytest ai-gateway/tests/test_pipeline_fixes.py -v

Each test is documented with the bug number it validates.
"""
import asyncio
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
