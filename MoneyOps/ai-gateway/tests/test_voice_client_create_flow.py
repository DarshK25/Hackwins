from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.intents import Intent
from app.state.session_manager import session_manager
from app.voice_processor import VoiceContext, VoiceProcessor


def _context(session_id: str, text: str) -> VoiceContext:
    return VoiceContext(
        session_id=session_id,
        user_id="user-1",
        org_uuid="tenant-1",
        business_id=1,
        raw_text=text,
    )


@pytest.mark.asyncio
async def test_client_create_keeps_collecting_when_name_answer_has_no_entities(monkeypatch):
    processor = VoiceProcessor()
    session_manager._sessions.clear()

    async def fake_classify(text, **kwargs):
        if text == "create client":
            return SimpleNamespace(intent=Intent.CLIENT_CREATE)
        return SimpleNamespace(intent=Intent.INVOICE_QUERY)

    async def fake_extract(text, intent_obj, context, locked_intent=None):
        return SimpleNamespace(entities=[])

    monkeypatch.setattr(processor.intent_classifier, "classify", fake_classify)
    monkeypatch.setattr(processor.entity_extractor, "extract", fake_extract)
    monkeypatch.setattr(processor, "_should_report_activity", lambda result: False)

    import app.agents.market_agent as market_agent_module

    monkeypatch.setattr(market_agent_module.market_agent_instance, "start_market_monitor", lambda **kwargs: None)

    first = await processor.process("create client", _context("client-flow-1", "create client"))
    assert first["response_text"] == "What's the client's name?"

    second = await processor.process("google", _context("client-flow-1", "google"))
    assert second["response_text"] == "What's the client's email address?"

    session = session_manager.get_session("client-flow-1")
    assert session.client_draft["client_name"] == "google"
    assert session.locked_intent == "CLIENT_CREATE"


@pytest.mark.asyncio
async def test_client_create_flow_collects_all_fields_and_saves_client(monkeypatch):
    processor = VoiceProcessor()
    session_manager._sessions.clear()

    async def fake_classify(text, **kwargs):
        if text == "create client":
            return SimpleNamespace(intent=Intent.CLIENT_CREATE)
        return SimpleNamespace(intent=Intent.GENERAL_QUERY)

    async def fake_extract(text, intent_obj, context, locked_intent=None):
        return SimpleNamespace(entities=[])

    backend_request = AsyncMock(return_value=SimpleNamespace(success=True, data={"id": "client-123"}, error=None, status_code=201))

    monkeypatch.setattr(processor.intent_classifier, "classify", fake_classify)
    monkeypatch.setattr(processor.entity_extractor, "extract", fake_extract)
    monkeypatch.setattr(processor.backend, "_request", backend_request)
    monkeypatch.setattr(processor, "_should_report_activity", lambda result: False)

    import app.agents.market_agent as market_agent_module

    monkeypatch.setattr(market_agent_module.market_agent_instance, "start_market_monitor", lambda **kwargs: None)

    await processor.process("create client", _context("client-flow-2", "create client"))
    name_step = await processor.process("Tanush Jain", _context("client-flow-2", "Tanush Jain"))
    email_step = await processor.process("tanush@example.com", _context("client-flow-2", "tanush@example.com"))
    phone_step = await processor.process("9876543210", _context("client-flow-2", "9876543210"))
    company_step = await processor.process("Google", _context("client-flow-2", "Google"))
    final_step = await processor.process("1234", _context("client-flow-2", "1234"))

    assert name_step["response_text"] == "What's the client's email address?"
    assert email_step["response_text"] == "What's the client's phone number?"
    assert phone_step["response_text"] == "What's the company name for this client?"
    assert company_step["response_text"] == "Please tell me the team security code to create this client."
    assert final_step["success"] is True
    assert "Tanush Jain" in final_step["response_text"]

    payload = backend_request.await_args.kwargs["data"]
    assert payload["name"] == "Tanush Jain"
    assert payload["email"] == "tanush@example.com"
    assert payload["phoneNumber"] == "9876543210"
    assert payload["company"] == "Google"
    assert payload["teamActionCode"] == "1234"

    session = session_manager.get_session("client-flow-2")
    assert session.client_draft is None
    assert session.locked_intent is None
    assert session.focused_client_id == "client-123"
    assert session.focused_client_name == "Tanush Jain"


@pytest.mark.asyncio
async def test_client_create_accepts_name_when_extractor_prefills_current_answer(monkeypatch):
    processor = VoiceProcessor()
    session_manager._sessions.clear()

    async def fake_classify(text, **kwargs):
        if text == "create client":
            return SimpleNamespace(intent=Intent.CLIENT_CREATE)
        return SimpleNamespace(intent=Intent.GENERAL_QUERY)

    async def fake_extract(text, intent_obj, context, locked_intent=None):
        if text == "tommy":
            return SimpleNamespace(
                entities=[
                    SimpleNamespace(
                        entity_type=SimpleNamespace(value="client_name"),
                        value="tommy",
                    )
                ]
            )
        return SimpleNamespace(entities=[])

    monkeypatch.setattr(processor.intent_classifier, "classify", fake_classify)
    monkeypatch.setattr(processor.entity_extractor, "extract", fake_extract)
    monkeypatch.setattr(processor, "_should_report_activity", lambda result: False)

    import app.agents.market_agent as market_agent_module

    monkeypatch.setattr(market_agent_module.market_agent_instance, "start_market_monitor", lambda **kwargs: None)

    first = await processor.process("create client", _context("client-flow-3", "create client"))
    second = await processor.process("tommy", _context("client-flow-3", "tommy"))

    assert first["response_text"] == "What's the client's name?"
    assert second["response_text"] == "What's the client's email address?"

    session = session_manager.get_session("client-flow-3")
    assert session.client_draft["client_name"] == "tommy"
