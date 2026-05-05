"""
LangGraph-based Agent for MoneyOps.
Replaces keyword-matching pseudo-agents with proper LLM-driven state machine.
Uses tools for real API calls instead of if/else routing.
"""
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import asyncio
import json
import operator

from app.llm.multi_provider import llm_client
from app.utils.logger import get_logger
from app.adapters.backend_adapter import get_backend_adapter
from app.config import settings

logger = get_logger(__name__)


class AgentState(TypedDict):
    """State for the LangGraph agent."""
    messages: Annotated[List, operator.add]
    user_request: str
    org_id: str
    user_id: Optional[str]
    business_id: str
    thread_id: str
    # Intermediate results
    invoices: Optional[List[Dict]]
    clients: Optional[List[Dict]]
    # Final output
    response: Optional[str]
    error: Optional[str]


# ── Tools (replacing if/else keyword matching) ───────────────────────────────

@tool
async def get_invoices(org_id: str, status: Optional[str] = None, user_id: Optional[str] = None) -> str:
    """Get invoices for an organization. Status can be: DRAFT, SENT, OVERDUE, PAID, CANCELLED."""
    backend = get_backend_adapter()
    resp = await backend.get_invoices(org_id, status=status, user_id=user_id)
    if resp.success and resp.data:
        invoices = resp.data if isinstance(resp.data, list) else resp.data.get("invoices", [])
        return json.dumps({"success": True, "invoices": invoices[:10]})
    return json.dumps({"success": False, "error": resp.error or "Failed to fetch invoices"})


@tool
async def create_invoice(org_id: str, client_id: str, total_amount: float, due_date: str, 
                        description: str = "", user_id: Optional[str] = None) -> str:
    """Create a new invoice. due_date format: YYYY-MM-DD."""
    backend = get_backend_adapter()
    payload = {
        "clientId": client_id,
        "totalAmount": total_amount,
        "dueDate": due_date,
        "description": description,
        "status": "SENT",
    }
    resp = await backend.create_invoice_direct(org_id, user_id or "", payload)
    if resp.success and resp.data:
        return json.dumps({"success": True, "invoice": resp.data})
    return json.dumps({"success": False, "error": resp.error or "Failed to create invoice"})


@tool
async def record_payment(invoice_id: str, org_id: str, amount: float, user_id: Optional[str] = None) -> str:
    """Record a payment for an invoice."""
    backend = get_backend_adapter()
    payload = {
        "amount": amount,
        "transactionType": "PAYMENT",
        "description": "Payment recorded via AI",
    }
    try:
        resp = await backend._request(
            "POST", f"/api/invoices/{invoice_id}/payment",
            data=payload, org_id=org_id, user_id=user_id
        )
        if resp.success:
            return json.dumps({"success": True, "message": "Payment recorded"})
        return json.dumps({"success": False, "error": resp.error})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
async def get_clients(org_id: str, user_id: Optional[str] = None) -> str:
    """Get all clients for an organization."""
    backend = get_backend_adapter()
    clients = await backend.get_clients(org_id, user_id=user_id)
    return json.dumps({"success": True, "clients": clients[:10]})


@tool
async def get_financial_metrics(org_id: str, business_id: str = "1", user_id: Optional[str] = None) -> str:
    """Get financial metrics: revenue, expenses, profit, etc."""
    backend = get_backend_adapter()
    resp = await backend.get_finance_metrics(business_id, org_id, user_id)
    if resp.success and resp.data:
        return json.dumps({"success": True, "metrics": resp.data})
    return json.dumps({"success": False, "error": resp.error or "Failed to fetch metrics"})


@tool
async def send_collection_reminder(invoice_id: str, client_email: str, client_name: str,
                                   invoice_number: str, amount: float, due_date: str,
                                   org_id: Optional[str] = None, user_id: Optional[str] = None) -> str:
    """Send a payment reminder email to a client."""
    backend = get_backend_adapter()
    result = await backend.send_collection_email(
        invoice_id=invoice_id,
        client_email=client_email,
        client_name=client_name,
        invoice_number=invoice_number,
        amount=amount,
        due_date=due_date,
        org_id=org_id,
        user_id=user_id,
    )
    if result.get("sent"):
        return json.dumps({"success": True, "message": f"Reminder sent to {client_email}"})
    return json.dumps({"success": False, "error": result.get("error", "Failed to send")})


# ── System Prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a MoneyOps AI financial assistant for SMB owners.

Your job is to help with:
1. Invoice operations (create, query, track)
2. Payment recording and tracking
3. Client management
4. Financial metrics and insights
5. Automated collections and reminders

Use the available tools to perform operations. Always:
- Extract required parameters from the user's request
- Call the appropriate tool
- Summarize the results in a clear, business-friendly way
- For money amounts, use format: Rs.1,23,456
- Be concise and actionable

If you need to create an invoice but don't have client details, first call get_clients to find or create the client.
"""

# ── LangGraph Agent ────────────────────────────────────────────────────────────

class LangGraphAgent:
    """True LangGraph agent that uses LLM + Tools instead of keyword matching."""

    def __init__(self):
        self.tools = [
            get_invoices,
            create_invoice,
            record_payment,
            get_clients,
            get_financial_metrics,
            send_collection_reminder,
        ]

        # Bind tools to LLM
        self.llm = llm_client.get_langchain_llm()
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Build the graph
        self.graph = self._build_graph()
        logger.info("langgraph_agent_initialized", tools=[t.name for t in self.tools])

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", ToolNode(self.tools))

        # Add edges
        workflow.set_entry_point("agent")

        # Conditional edge: if tools are called, go to tools, else end
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END,
            }
        )

        # After tools, go back to agent
        workflow.add_edge("tools", "agent")

        return workflow.compile()

    async def _call_model(self, state: AgentState) -> Dict[str, Any]:
        """Call the LLM with current state."""
        messages = state.get("messages", [])

        # Add system message if not present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

        try:
            response = await self.llm_with_tools.ainvoke(messages)
            return {"messages": [response]}
        except Exception as e:
            logger.error("langgraph_model_error", error=str(e))
            return {"error": str(e), "messages": [AIMessage(content=f"Error: {str(e)}")]}

    def _should_continue(self, state: AgentState) -> str:
        """Check if we should continue or end."""
        messages = state.get("messages", [])
        if not messages:
            return "end"

        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
        return "end"

    async def run(
        self,
        user_request: str,
        org_id: str,
        user_id: Optional[str] = None,
        business_id: str = "1",
        thread_id: str = "default",
    ) -> Dict[str, Any]:
        """Run the LangGraph agent on a user request."""
        initial_state: AgentState = {
            "messages": [HumanMessage(content=user_request)],
            "user_request": user_request,
            "org_id": org_id,
            "user_id": user_id,
            "business_id": business_id,
            "thread_id": thread_id,
            "invoices": None,
            "clients": None,
            "response": None,
            "error": None,
        }

        try:
            # Run the graph
            result = await self.graph.ainvoke(initial_state)

            # Extract final response
            messages = result.get("messages", [])
            final_message = None
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and not hasattr(msg, "tool_calls"):
                    final_message = msg
                    break

            response_text = final_message.content if final_message else "No response generated"

            return {
                "success": True,
                "result": response_text,
                "messages": [str(m) for m in messages],
                "error": result.get("error"),
            }

        except Exception as e:
            logger.error("langgraph_run_error", error=str(e), org_id=org_id)
            return {
                "success": False,
                "result": f"Error processing request: {str(e)}",
                "error": str(e),
            }


# Singleton instance
langgraph_agent = LangGraphAgent()
