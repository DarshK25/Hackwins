import asyncio
import sys
import types
import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def install_test_stubs():
    rapidfuzz_stub = types.ModuleType("rapidfuzz")
    rapidfuzz_stub.process = types.SimpleNamespace()
    rapidfuzz_stub.fuzz = types.SimpleNamespace()
    sys.modules.setdefault("rapidfuzz", rapidfuzz_stub)

    if "structlog" not in sys.modules:
        structlog_stub = types.ModuleType("structlog")

        class DummyLogger:
            def info(self, *args, **kwargs):
                return None

            def warning(self, *args, **kwargs):
                return None

            def error(self, *args, **kwargs):
                return None

            def debug(self, *args, **kwargs):
                return None

        structlog_stub.configure = lambda *args, **kwargs: None
        structlog_stub.get_logger = lambda *args, **kwargs: DummyLogger()
        structlog_stub.contextvars = types.SimpleNamespace(merge_contextvars=lambda *args, **kwargs: None)
        structlog_stub.processors = types.SimpleNamespace(
            add_log_level=lambda *args, **kwargs: None,
            StackInfoRenderer=lambda *args, **kwargs: object(),
            TimeStamper=lambda *args, **kwargs: object(),
            JSONRenderer=lambda *args, **kwargs: object(),
        )
        structlog_stub.dev = types.SimpleNamespace(
            set_exc_info=lambda *args, **kwargs: None,
            ConsoleRenderer=lambda *args, **kwargs: object(),
        )
        structlog_stub.make_filtering_bound_logger = lambda *args, **kwargs: DummyLogger
        structlog_stub.PrintLoggerFactory = lambda *args, **kwargs: object()
        sys.modules["structlog"] = structlog_stub


def test_parse_relative_date_supports_month_day_phrases_with_future_bias():
    from app.utils.date_parser import parse_relative_date

    today = datetime.now().date()
    parsed = parse_relative_date("fifth march", prefer_future=True)

    assert parsed is not None

    expected_year = today.year
    if (today.month, today.day) > (3, 5):
        expected_year += 1

    assert parsed == f"{expected_year:04d}-03-05"


@pytest.mark.asyncio
async def test_invoice_create_reprompts_when_due_date_is_in_the_past():
    install_test_stubs()

    from app.agents.finance_agent import FinanceAgent
    from app.models.draft import InvoiceDraft
    from app.state.session_manager import session_manager

    session_id = f"session-{uuid.uuid4()}"
    user_id = "user-1"
    org_id = "org-internal-1"
    yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()

    try:
        session = session_manager.get_session(session_id, user_id, org_id)
        session.invoice_draft = InvoiceDraft(
            draft_id=str(uuid.uuid4()),
            session_id=session_id,
            client_id="client-1",
            client_name="Sam Altman",
            item_type="SERVICE",
            item_description="software",
            amount=25_000,
            gst_percent=0,
            gst_applicable=False,
            due_date=yesterday,
        )
        session.locked_intent = "INVOICE_CREATE"
        session_manager.save_session(session)

        agent = FinanceAgent()
        response = await agent.handle_invoice_create(
            SimpleNamespace(
                session_id=session_id,
                user_id=user_id,
                org_uuid=org_id,
                raw_text="yes",
                extracted_entities=[],
            )
        )

        assert response.success is True
        assert "before today" in response.message.lower()

        updated = session_manager.get_session(session_id, user_id, org_id)
        assert updated.invoice_draft is not None
        assert updated.invoice_draft.due_date is None
        assert updated.invoice_draft.last_question_asked == "due_date"
    finally:
        session_manager._sessions.pop(session_id, None)


@pytest.mark.asyncio
async def test_session_manager_starts_orchestrator_conversation_after_org_resolution():
    install_test_stubs()
    import app.adapters.orchestrator_adapter as orchestrator_module
    from app.state.session_manager import SessionManager, VoiceSession

    manager = SessionManager()
    session = VoiceSession(
        session_id="session-1",
        user_id="user-1",
        org_id="resolved-org-1",
    )

    scheduled = []

    def fake_create_task(coro):
        scheduled.append(coro)
        return MagicMock()

    with patch.object(
        orchestrator_module.orchestrator_adapter,
        "start_conversation",
        new=AsyncMock(return_value=True),
    ) as start_mock, patch("asyncio.create_task", side_effect=fake_create_task):
        manager.save_session(session)

        assert len(scheduled) == 1
        await scheduled[0]

    start_mock.assert_awaited_once_with(
        org_id="resolved-org-1",
        user_id="user-1",
        session_id="session-1",
    )
    assert manager._sessions["session-1"].orchestrator_conversation_started is True


@pytest.mark.asyncio
async def test_add_turn_bootstraps_conversation_before_logging_message():
    install_test_stubs()
    import app.adapters.orchestrator_adapter as orchestrator_module
    from app.state.session_manager import SessionManager, VoiceSession

    manager = SessionManager()
    manager._sessions["session-2"] = VoiceSession(
        session_id="session-2",
        user_id="user-2",
        org_id="resolved-org-2",
        orchestrator_conversation_started=False,
    )

    scheduled = []

    def fake_create_task(coro):
        scheduled.append(coro)
        return MagicMock()

    with patch.object(
        orchestrator_module.orchestrator_adapter,
        "start_conversation",
        new=AsyncMock(return_value=True),
    ) as start_mock, patch.object(
        orchestrator_module.orchestrator_adapter,
        "add_message",
        new=AsyncMock(return_value=True),
    ) as add_message_mock, patch("asyncio.create_task", side_effect=fake_create_task):
        manager.add_turn("session-2", "assistant", "Hello", "INVOICE_CREATE")

        assert len(scheduled) == 1
        await scheduled[0]

    start_mock.assert_awaited_once_with(
        org_id="resolved-org-2",
        user_id="user-2",
        session_id="session-2",
    )
    add_message_mock.assert_awaited_once_with(
        org_id="resolved-org-2",
        user_id="user-2",
        session_id="session-2",
        role="assistant",
        content="Hello",
        intent="INVOICE_CREATE",
    )
