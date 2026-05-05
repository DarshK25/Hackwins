import pytest

from app.adapters.backend_adapter import normalize_business_id
from app.state.session_manager import SessionManager, session_manager
from app.tools.multi_source_search import MultiSourceSearch
from app.agents.finance_agent import _client_display_name
from app.agents.intelligent_agent import IntelligentAgent
from app.agents.finance_agent import finance_agent
from app.agents.enhanced_finance_agent import EnhancedFinanceAgent
from app.utils.tts_sanitizer import sanitize_for_tts


@pytest.mark.asyncio
async def test_multi_source_search_accepts_legacy_max_results_keyword():
    searcher = MultiSourceSearch()
    searcher.providers = {"duckduckgo": {"weight": 0.5, "type": "general"}}

    async def fake_search_duckduckgo(query: str, max_results: int):
        return {
            "results": [{"title": query, "url": "https://example.com", "snippet": "ok"}],
            "sources": ["https://example.com"],
        }

    searcher._search_duckduckgo = fake_search_duckduckgo

    result = await searcher.search("market news", max_results=3)

    assert result["results"][0]["title"] == "market news"


def test_normalize_business_id_defaults_invalid_values_to_one():
    assert normalize_business_id(None) == "1"
    assert normalize_business_id("default") == "1"
    assert normalize_business_id("undefined") == "1"
    assert normalize_business_id("9") == "9"
    assert normalize_business_id(12) == "12"


def test_session_manager_refreshes_existing_session_context():
    manager = SessionManager()

    manager.get_session("sess-1", "user-a", "org-a", business_id=1)
    session = manager.get_session("sess-1", "user-b", "org-b", business_id=7)

    assert session.user_id == "user-b"
    assert session.org_id == "org-b"
    assert session.business_id == 7


def test_client_display_name_accepts_all_supported_backend_shapes():
    assert _client_display_name({"name": "Arjun Desai"}) == "Arjun Desai"
    assert _client_display_name({"displayName": "Arjun Desai"}) == "Arjun Desai"
    assert _client_display_name({"display_name": "Arjun Desai"}) == "Arjun Desai"


def test_intelligent_agent_continues_locked_invoice_for_short_followup():
    agent = IntelligentAgent()
    manager = SessionManager()
    session = manager.get_session("sess-2", "user-a", "org-a", business_id=1)
    session.locked_intent = "INVOICE_CREATE"
    session.invoice_draft = object()

    tool_name, _ = agent._route_query("36", session)

    assert tool_name == "create_invoice"


def test_intelligent_agent_continues_business_context_followup():
    agent = IntelligentAgent()
    manager = SessionManager()
    session = manager.get_session("sess-3", "user-a", "org-a", business_id=1)
    session.last_tool = "get_business_context"

    tool_name, _ = agent._route_query("and what sector is it", session)

    assert tool_name == "get_business_context"


def test_intelligent_agent_continues_market_followup():
    agent = IntelligentAgent()
    manager = SessionManager()
    session = manager.get_session("sess-4", "user-a", "org-a", business_id=1)
    session.last_tool = "search_market"

    tool_name, args = agent._route_query("how will this affect my business", session)

    assert tool_name == "search_market"
    assert args["followup"] is True


def test_intelligent_agent_continues_invoice_followup_for_short_fragment():
    agent = IntelligentAgent()
    manager = SessionManager()
    session = manager.get_session("sess-4b", "user-a", "org-a", business_id=1)
    session.last_tool = "get_all_invoices"

    tool_name, args = agent._route_query("are there", session)

    assert tool_name == "get_all_invoices"
    assert args["metric"] == "count"


def test_intelligent_agent_routes_paid_invoice_revenue_to_invoice_tool():
    agent = IntelligentAgent()

    tool_name, args = agent._route_query("what is my revenue out of my paid invoices", None)

    assert tool_name == "get_all_invoices"
    assert args["status"] == "PAID"
    assert args["metric"] == "revenue"


def test_finance_agent_parses_multi_item_invoice_text():
    items = finance_agent.parse_line_items_text(
        "PRODUCT | AC EV Charger Supply & Installation (7.2kW) | 12 | 38500 | 18\n"
        "SERVICE | Site Survey & Electrical Feasibility Report | - | 18000 | 18"
    )

    assert len(items) == 2
    assert items[0]["type"] == "PRODUCT"
    assert items[0]["quantity"] == 12
    assert items[1]["type"] == "SERVICE"
    assert items[1]["quantity"] is None


def test_client_draft_accepts_gstin_skip_and_explicit_override():
    from app.agents.moneyops_agent import _merge_client_draft_from_text

    skipped = _merge_client_draft_from_text(
        "not registered",
        {"name": "J Singh", "company_name": "Solar Nest Infra Private Limited", "_pending_field": "gstin"},
    )
    corrected = _merge_client_draft_from_text(
        "Solar Nestcom Private Limited",
        {"company_name": "Solar Nest Infra Private Limited", "_pending_field": "company_name"},
    )

    assert skipped.get("_gstin_skipped") is True
    assert corrected.get("company_name") == "Solar Nestcom Private Limited"


@pytest.mark.asyncio
async def test_create_client_prompts_for_gstin_before_team_code():
    from app.agents.moneyops_agent import AgentSession, execute_tool

    session = AgentSession(session_id="sess-gstin", user_id="user-1", org_uuid="org-1")
    result = await execute_tool(
        "create_client",
        '{"name":"J Singh","company_name":"Solar Nest Infra Private Limited","email":"j@solarnest.com","phone":"9876543210"}',
        session,
        {"org_id": "org-1", "business_id": "1"},
        backend=None,
    )

    assert result["status"] == "validation_error"
    assert result["missing_field"] == "gstin"


@pytest.mark.asyncio
async def test_create_invoice_ignores_hallucinated_team_code_on_due_date_turn():
    from app.agents.moneyops_agent import AgentSession, execute_tool

    class FakeBackend:
        async def get(self, endpoint, org_id=None, user_id=None, headers=None):
            assert endpoint == "/api/clients?limit=200"
            return [{"id": "client-1", "name": "Ajay Singh"}]

        async def post(self, *args, **kwargs):
            raise AssertionError("create_invoice should not call backend when team code was not actually provided")

    session = AgentSession(
        session_id="sess-team-guard",
        user_id="user-1",
        org_uuid="org-1",
        pending_invoice={
            "client_name": "Ajay Singh",
            "line_items": [{"description": "Solar setup", "unit_price": 29500}],
        },
        current_user_text="20th may",
    )

    result = await execute_tool(
        "create_invoice",
        '{"client_name":"Ajay Singh","due_date":"2026-05-20","line_items":[{"description":"Solar setup","unit_price":29500}],"team_code":"VNES001"}',
        session,
        {"org_id": "org-1", "business_id": "1"},
        backend=FakeBackend(),
    )

    assert result["status"] == "validation_error"
    assert result["missing_field"] == "team_code"


def test_invoice_draft_reuses_last_client_for_same_client_phrase():
    from app.agents.moneyops_agent import _merge_invoice_draft_from_text

    draft = _merge_invoice_draft_from_text(
        "create an invoice for the same client",
        {"_last_client_name": "J Singh"},
    )

    assert draft.get("client_name") == "J Singh"


def test_invoice_draft_keeps_bare_service_description_for_followup_amount():
    from app.agents.moneyops_agent import _merge_invoice_draft_from_text

    draft = _merge_invoice_draft_from_text(
        "solar monitoring system setup",
        {"client_name": "J Singh"},
    )

    assert draft.get("_pending_line_item_description") == "Solar monitoring system setup"


def test_invoice_draft_preserves_pending_description_for_add_this_item_followup():
    from app.agents.moneyops_agent import _merge_invoice_draft_from_text

    draft = _merge_invoice_draft_from_text(
        "add this as item of the invoice",
        {
            "client_name": "J Singh",
            "_pending_line_item_description": "Solar monitoring system setup",
        },
    )

    assert draft.get("_pending_line_item_description") == "Solar monitoring system setup"


def test_invoice_description_strips_sentence_scaffolding():
    from app.agents.moneyops_agent import _extract_invoice_service_description, _clean_invoice_item_followup_text

    extracted = _extract_invoice_service_description(
        "and invoice item as setup and deployment of solar energy monitoring dashboard"
    )
    cleaned = _clean_invoice_item_followup_text("as iot sensor calibration and site audit")

    assert extracted == "Setup and deployment of solar energy monitoring dashboard"
    assert cleaned == "iot sensor calibration and site audit"


def test_due_date_prompt_fragment_is_not_treated_as_description():
    from app.agents.moneyops_agent import _merge_invoice_draft_from_text

    draft = _merge_invoice_draft_from_text(
        "the payment due date is",
        {"client_name": "Client Alpha"},
    )

    assert draft.get("_pending_line_item_description") is None


def test_create_invoice_query_accepts_a_invoice_grammar_and_trailing_for():
    from app.agents.moneyops_agent import _is_create_invoice_query

    assert _is_create_invoice_query("i'd like to create a invoice for")
    assert _is_create_invoice_query("create a invoice")


def test_session_context_does_not_answer_top_client_for_invoice_request():
    from app.agents.moneyops_agent import AgentSession, _answer_from_session_context

    session = AgentSession(
        session_id="sess-invoice-guard",
        user_id="user-1",
        org_uuid="org-1",
        last_client_results=[
            {
                "name": "Client Alpha",
                "company": "Example Logistics Private Limited",
                "total_revenue_inr": 849600,
            }
        ],
    )

    answer = _answer_from_session_context("i'd like to create a invoice for", session)

    assert answer is None


@pytest.mark.asyncio
async def test_send_invoice_email_uses_invoice_send_endpoint():
    from app.agents.moneyops_agent import AgentSession, execute_tool

    class FakeSendResponse:
        success = True
        error = None

    class FakeBackend:
        def __init__(self):
            self.patch_calls = []

        async def get(self, endpoint, org_id=None, user_id=None, headers=None):
            assert endpoint == "/api/invoices?limit=100"
            return [
                {
                    "id": "inv-1",
                    "invoiceNumber": "INV-001",
                    "clientName": "Ajay Singh",
                    "clientEmail": "ajay@example.com",
                    "status": "DRAFT",
                    "totalAmount": 29500,
                }
            ]

        async def _request(self, method, endpoint, data=None, params=None, headers=None, org_id=None, user_id=None):
            self.patch_calls.append((method, endpoint, headers, org_id, user_id))
            return FakeSendResponse()

    backend = FakeBackend()
    session = AgentSession(
        session_id="sess-send",
        user_id="user-1",
        org_uuid="org-1",
        verified_team_code="1234",
        last_invoice_mentioned="INV-001",
        current_user_text="send the invoice now",
    )

    result = await execute_tool(
        "send_invoice_email",
        '{"client_name":"Ajay Singh","invoice_number":"INV-001"}',
        session,
        {"org_id": "org-1", "business_id": "1"},
        backend=backend,
    )

    assert result["status"] == "sent"
    assert backend.patch_calls == [
        ("PATCH", "/api/invoices/inv-1/send", {"X-Team-Code": "1234", "X-Org-Id": "org-1"}, "org-1", "user-1")
    ]


@pytest.mark.asyncio
async def test_business_context_avoids_not_set_placeholders(monkeypatch):
    agent = IntelligentAgent()

    class FakeResponse:
        success = True
        data = {"businessName": "VoltNest Energy", "orgId": "org-1"}

    async def fake_get_onboarding_status(_clerk_id):
        return FakeResponse()

    monkeypatch.setattr(agent.backend, "get_onboarding_status", fake_get_onboarding_status)

    message = await agent._tool_get_business_context(
        {"user_id": "user-1", "org_id": "org-1"}
    )

    assert "VoltNest Energy" in message
    assert "Not set" not in message
    assert "detailed business profile is still missing" in message


@pytest.mark.asyncio
async def test_business_context_prefers_org_profile_over_status(monkeypatch):
    agent = IntelligentAgent()

    class FakeOrgResponse:
        success = True
        data = {
            "legalName": "VoltNest Energy Private Limited",
            "industry": "clean energy infrastructure",
            "targetMarket": "B2B",
            "primaryActivity": "EV charging infrastructure design, supply, and installation",
        }

    class FakeStatusResponse:
        success = True
        data = {"orgId": "org-1", "message": "Onboarding complete"}

    async def fake_get_my_organization(_user_id):
        return FakeOrgResponse()

    async def fake_get_onboarding_status(_clerk_id):
        return FakeStatusResponse()

    monkeypatch.setattr(agent.backend, "get_my_organization", fake_get_my_organization)
    monkeypatch.setattr(agent.backend, "get_onboarding_status", fake_get_onboarding_status)

    message = await agent._tool_get_business_context(
        {"user_id": "user-1", "org_id": "org-1"}
    )

    assert "VoltNest Energy Private Limited" in message
    assert "clean energy infrastructure" in message
    assert "EV charging infrastructure design, supply, and installation" in message


@pytest.mark.asyncio
async def test_business_context_followup_uses_cached_profile():
    agent = IntelligentAgent()
    session = session_manager.get_session("sess-5", "user-a", "org-a", business_id=1)
    session.last_tool = "get_business_context"
    session.last_business_profile = {
        "name": "VoltNest Energy Private Limited",
        "industry": "clean energy infrastructure",
        "sector": "B2B commercial EV charging",
        "services": "EV charging infrastructure design and installation",
    }
    session_manager.save_session(session)

    message = await agent._tool_get_business_context(
        {
            "session_id": "sess-5",
            "user_id": "user-a",
            "org_id": "org-a",
            "raw_text": "what sector is it",
        }
    )

    assert message == "VoltNest Energy Private Limited sits in B2B commercial EV charging."


@pytest.mark.asyncio
async def test_market_followup_uses_cached_results():
    agent = IntelligentAgent()
    session = session_manager.get_session("sess-6", "user-a", "org-a", business_id=1)
    session.last_tool = "search_market"
    session.last_business_profile = {
        "name": "VoltNest Energy Private Limited",
        "sector": "B2B commercial EV charging",
        "services": "EV charging infrastructure design and installation",
    }
    session.last_market_results = [
        "New EV infra incentives announced in India",
        "Commercial fleet electrification picks up in hospitality",
    ]
    session_manager.save_session(session)

    message = await agent._tool_search_market(
        {
            "session_id": "sess-6",
            "user_id": "user-a",
            "org_id": "org-a",
            "raw_text": "how will this affect my business",
            "followup": True,
        }
    )

    assert "VoltNest Energy Private Limited" in message
    assert "New EV infra incentives announced in India" in message


def test_tts_sanitizer_keeps_invoice_numbers_and_formats_dates_and_amounts():
    text = (
        "3 overdue invoice(s), total INR 18,90,000.00: "
        "- VN-2026-003 | Sunita Rao | INR 3,42,200.00 | due [2026, 2, 25] | 42 days overdue"
    )

    result = sanitize_for_tts(text)

    assert "VN-2026-003" in result
    assert "2 thousand" not in result
    assert "February 25, 2026" in result
    assert ".00" not in result


@pytest.mark.asyncio
async def test_enhanced_finance_agent_accepts_object_context_without_get(monkeypatch):
    agent = EnhancedFinanceAgent()

    async def fake_generate_financial_summary(org_id, user_id=None):
        return f"summary for {org_id} / {user_id}"

    monkeypatch.setattr(
        agent, "_generate_financial_summary", fake_generate_financial_summary
    )

    class Ctx:
        org_uuid = "org-ctx"
        user_id = "user-ctx"

    result = await agent.handle_balance_check(Ctx())

    assert result.success is True
    assert result.message == "summary for org-ctx / user-ctx"
