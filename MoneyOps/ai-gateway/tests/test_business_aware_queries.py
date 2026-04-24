from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.agents.general_agent as general_agent_module
from app.agents.general_agent import GeneralAgent
from app.agents.finance_agent import finance_agent
from app.agents.market_agent import market_agent_instance
from app.orchestration.agent_router import AgentRouter
from app.orchestration.intent_classifier import IntentClassifier
from app.schemas.intents import AgentType, Intent


@pytest.mark.asyncio
async def test_general_agent_answers_business_profile_queries_from_account_context():
    agent = GeneralAgent()
    agent._llm_business_response = AsyncMock(return_value="Your website on file is https://moneyops.ai and you're in fintech services.")
    agent.backend.get_my_organization = AsyncMock(return_value=SimpleNamespace(success=True, data={
        "legalName": "MoneyOps Pvt Ltd",
        "website": "https://moneyops.ai",
        "industry": "Fintech Services",
        "businessType": "Private Limited",
    }))
    agent.backend.get_finance_metrics = AsyncMock(return_value=SimpleNamespace(success=True, data={"revenue": 62540, "totalInvoices": 6}))
    agent.backend.get_finance_insights = AsyncMock(return_value=SimpleNamespace(success=True, data={"insights": [{"title": "Cash Flow Alert"}]}))
    agent.backend.get_clients = AsyncMock(return_value=[{"name": "Acme"}])
    agent.backend.get_invoices = AsyncMock(return_value=SimpleNamespace(success=True, data=[{"status": "PAID"}]))
    agent.backend.get_user_by_id = AsyncMock(return_value=SimpleNamespace(success=True, data={
        "id": "user-1",
        "name": "Tanush Jain",
        "email": "tanush@example.com",
        "role": "OWNER",
    }))
    agent.backend.get_org_users = AsyncMock(return_value=SimpleNamespace(success=True, data=[]))

    response = await agent.process(
        Intent.GENERAL_QUERY,
        {},
        {
            "raw_text": "what is my website",
            "user_id": "user-1",
            "org_uuid": "org-1",
            "business_id": 1,
            "conversation_history": [],
        },
    )

    assert response.success is True
    assert "website" in response.message.lower()
    agent._llm_business_response.assert_awaited_once()


@pytest.mark.asyncio
async def test_general_agent_falls_back_cleanly_when_business_llm_fails():
    agent = GeneralAgent()
    agent._llm_business_response = AsyncMock(side_effect=RuntimeError("llm unavailable"))
    general_agent_module.get_market_intelligence_payload = AsyncMock(return_value={
        "success": True,
        "snapshot": {"revenue": 62540, "total_clients": 1},
        "market": {
            "news": {"answer": "Professional services demand remains strong.", "news": ["Services exports rise (Reuters)"]},
            "opportunities": {"opportunities": "Recurring retainer offerings are expanding."},
            "competitors": {"competitors_answer": "Fragmented market."},
        },
        "cached": False,
        "timestamp": "2026-03-28T00:00:00",
    })
    agent.backend.get_my_organization = AsyncMock(return_value=SimpleNamespace(success=True, data={
        "legalName": "MoneyOps Pvt Ltd",
        "website": "https://moneyops.ai",
        "industry": "Fintech Services",
    }))
    agent.backend.get_finance_metrics = AsyncMock(return_value=SimpleNamespace(success=True, data={"revenue": 62540, "overdueCount": 2}))
    agent.backend.get_finance_insights = AsyncMock(return_value=SimpleNamespace(success=True, data={"insights": []}))
    agent.backend.get_clients = AsyncMock(return_value=[{"name": "Acme"}])
    agent.backend.get_invoices = AsyncMock(return_value=SimpleNamespace(success=True, data=[{"status": "PAID"}]))
    agent.backend.get_user_by_id = AsyncMock(return_value=SimpleNamespace(success=True, data={"name": "Tanush Jain", "role": "OWNER"}))
    agent.backend.get_org_users = AsyncMock(return_value=SimpleNamespace(success=True, data=[]))

    response = await agent.process(
        Intent.GENERAL_QUERY,
        {},
        {
            "raw_text": "tell me current growth opportunities for my business",
            "user_id": "user-1",
            "org_uuid": "org-1",
            "business_id": 1,
        },
    )

    assert response.success is True
    assert "growth" in response.message.lower() or "opportunit" in response.message.lower()
    assert "trouble" not in response.message.lower()


@pytest.mark.asyncio
async def test_general_agent_fetches_news_in_news_mode():
    agent = GeneralAgent()
    agent._llm_business_response = AsyncMock(return_value="Crude oil prices are rising and that may increase operating costs.")
    market_fetch = AsyncMock(return_value={
        "success": True,
        "snapshot": {},
        "market": {
            "news": {"answer": "Crude oil rose after fresh war concerns.", "news": ["Crude oil jumps on supply risk (Reuters)"]},
            "opportunities": {"opportunities": "No growth summary."},
            "competitors": {"competitors_answer": ""},
        },
        "cached": False,
        "timestamp": "2026-03-28T00:00:00",
    })
    general_agent_module.get_market_intelligence_payload = market_fetch
    agent.backend.get_my_organization = AsyncMock(return_value=SimpleNamespace(success=True, data={}))
    agent.backend.get_finance_metrics = AsyncMock(return_value=SimpleNamespace(success=True, data={}))
    agent.backend.get_finance_insights = AsyncMock(return_value=SimpleNamespace(success=True, data={"insights": []}))
    agent.backend.get_clients = AsyncMock(return_value=[])
    agent.backend.get_invoices = AsyncMock(return_value=SimpleNamespace(success=True, data=[]))
    agent.backend.get_user_by_id = AsyncMock(return_value=SimpleNamespace(success=True, data={}))
    agent.backend.get_org_users = AsyncMock(return_value=SimpleNamespace(success=True, data=[]))

    response = await agent.process(
        Intent.GENERAL_QUERY,
        {},
        {
            "raw_text": "tell me the latest market news",
            "user_id": "user-1",
            "org_uuid": "org-1",
            "business_id": 1,
        },
    )

    assert response.success is True
    assert "crude oil" in response.message.lower()
    assert market_fetch.await_args.kwargs["topic"] == "news"
    assert market_fetch.await_args.kwargs["force_refresh"] is True


@pytest.mark.asyncio
async def test_general_agent_answers_team_member_queries_from_account_context():
    agent = GeneralAgent()
    agent._llm_business_response = AsyncMock(return_value="You currently have 2 team members: Tanush Jain and Sam Altman.")
    agent.backend.get_my_organization = AsyncMock(return_value=SimpleNamespace(success=True, data={
        "legalName": "MoneyOps Pvt Ltd",
        "website": "https://moneyops.ai",
    }))
    agent.backend.get_finance_metrics = AsyncMock(return_value=SimpleNamespace(success=True, data={"revenue": 62540, "totalInvoices": 6}))
    agent.backend.get_finance_insights = AsyncMock(return_value=SimpleNamespace(success=True, data={"insights": []}))
    agent.backend.get_clients = AsyncMock(return_value=[{"name": "Acme"}])
    agent.backend.get_invoices = AsyncMock(return_value=SimpleNamespace(success=True, data=[{"status": "PAID"}]))
    agent.backend.get_user_by_id = AsyncMock(return_value=SimpleNamespace(success=True, data={
        "id": "user-1",
        "name": "Tanush Jain",
        "email": "tanush@example.com",
        "role": "OWNER",
    }))
    agent.backend.get_org_users = AsyncMock(return_value=SimpleNamespace(success=True, data=[
        {"id": "user-1", "name": "Tanush Jain"},
        {"id": "user-2", "name": "Sam Altman"},
    ]))

    response = await agent.process(
        Intent.GENERAL_QUERY,
        {},
        {
            "raw_text": "can you tell me how many team members do i have",
            "user_id": "user-1",
            "org_uuid": "org-1",
            "business_id": 1,
        },
    )

    assert response.success is True
    assert "team members" in response.message.lower()
    agent._llm_business_response.assert_awaited_once()


def test_market_agent_uses_strategy_agent_type():
    assert market_agent_instance.get_agent_type() == AgentType.STRATEGY_AGENT


def test_agent_router_registers_general_and_strategy_agents():
    router = AgentRouter()
    assert router.is_agent_available(AgentType.GENERAL_AGENT) is True
    assert router.is_agent_available(AgentType.STRATEGY_AGENT) is True


def test_intent_classifier_matches_growth_opportunities_pattern():
    classifier = IntentClassifier()
    result = classifier._pattern_classify("can you tell me current growth opportunities for my business")
    assert result is not None
    assert result["intent"] == Intent.GROWTH_STRATEGY


def test_intent_classifier_matches_highest_revenue_client_pattern():
    classifier = IntentClassifier()
    result = classifier._pattern_classify("which client has given me the highest revenue")
    assert result is not None
    assert result["intent"] == Intent.ANALYTICS_QUERY


def test_intent_classifier_matches_invoice_count_pattern():
    classifier = IntentClassifier()
    result = classifier._pattern_classify("how many invoices do i have")
    assert result is not None
    assert result["intent"] == Intent.INVOICE_QUERY


def test_intent_classifier_matches_client_invoice_count_pattern():
    classifier = IntentClassifier()
    result = classifier._pattern_classify("how many invoices does sam altman have")
    assert result is not None
    assert result["intent"] == Intent.INVOICE_QUERY


def test_intent_classifier_matches_collection_pattern():
    classifier = IntentClassifier()
    result = classifier._pattern_classify("how much total money is remained to collect")
    assert result is not None
    assert result["intent"] == Intent.ANALYTICS_QUERY


@pytest.mark.asyncio
async def test_finance_agent_answers_highest_revenue_client_query():
    finance_agent.backend.get_client_revenue_summary = AsyncMock(return_value=SimpleNamespace(success=True, data={
        "topClients": [
            {
                "clientName": "Acme Corp",
                "billedRevenue": 240000,
                "collectedRevenue": 190000,
                "outstandingRevenue": 50000,
            }
        ]
    }))

    result = await finance_agent._handle_analytics_query(
        {},
        {
            "raw_text": "which client has given me the highest revenue",
            "org_uuid": "org-1",
            "business_id": 1,
            "user_id": "user-1",
        },
    )

    assert "Acme Corp" in result["message"]
    assert "billed revenue" in result["message"]


@pytest.mark.asyncio
async def test_finance_agent_answers_specific_client_revenue_query():
    finance_agent._resolve_client = AsyncMock(return_value={"id": "client-1", "name": "Acme Corp"})
    finance_agent.backend.get_client_revenue_detail = AsyncMock(return_value=SimpleNamespace(success=True, data={
        "clientName": "Acme Corp",
        "billedRevenue": 240000,
        "collectedRevenue": 190000,
        "outstandingRevenue": 50000,
        "invoiceCount": 4,
    }))

    result = await finance_agent._handle_analytics_query(
        {},
        {
            "raw_text": "how much revenue has Acme Corp given me",
            "org_uuid": "org-1",
            "business_id": 1,
            "user_id": "user-1",
        },
    )

    assert "Acme Corp" in result["message"]
    assert "collected revenue" in result["message"]


@pytest.mark.asyncio
async def test_finance_agent_answers_total_outstanding_collection_query():
    finance_agent.backend.get_invoices = AsyncMock(return_value=SimpleNamespace(success=True, data=[
        {"status": "OVERDUE", "balanceDue": 12000},
        {"status": "SENT", "balanceDue": 8000},
        {"status": "PAID", "balanceDue": 0},
    ]))

    result = await finance_agent._handle_analytics_query(
        {},
        {
            "raw_text": "how much total money is remained to collect",
            "org_uuid": "org-1",
            "business_id": 1,
            "user_id": "user-1",
        },
    )

    assert "20,000" in result["message"]
    assert "unpaid invoices" in result["message"]


@pytest.mark.asyncio
async def test_finance_agent_processes_invoice_query_instead_of_fallback():
    finance_agent.backend.get_invoices = AsyncMock(return_value=SimpleNamespace(success=True, data=[{"id": "inv-1"}, {"id": "inv-2"}]))

    response = await finance_agent.process(
        Intent.INVOICE_QUERY,
        {},
        {"org_uuid": "org-1", "user_id": "user-1"},
    )

    assert response.success is True
    assert "2 total invoices" in response.message


@pytest.mark.asyncio
async def test_finance_agent_answers_client_specific_invoice_count():
    finance_agent.backend.get_invoices = AsyncMock(return_value=SimpleNamespace(success=True, data=[
        {"id": "inv-1", "clientId": "client-1", "clientName": "Sam Altman"},
        {"id": "inv-2", "clientId": "client-1", "clientName": "Sam Altman"},
        {"id": "inv-3", "clientId": "client-2", "clientName": "Tanush Jain"},
    ]))
    finance_agent._resolve_client = AsyncMock(return_value={"id": "client-1", "name": "Sam Altman"})

    result = await finance_agent._handle_query_invoices(
        {},
        {
            "raw_text": "how many invoices does sam altman have",
            "org_uuid": "org-1",
            "user_id": "user-1",
        },
    )

    assert "Sam Altman has 2 invoices" in result["message"]


@pytest.mark.asyncio
async def test_finance_agent_keeps_business_statistics_on_metrics_path():
    finance_agent.backend.get_finance_metrics = AsyncMock(return_value=SimpleNamespace(success=True, data={
        "revenue": 62540,
        "expenses": 12000,
        "netProfit": 50540,
    }))

    result = await finance_agent._handle_analytics_query(
        {"entity_name": "my business"},
        {
            "raw_text": "tell me about the statistics of my business",
            "org_uuid": "org-1",
            "business_id": 1,
            "user_id": "user-1",
        },
    )

    assert "Revenue for this period" in result["message"]
