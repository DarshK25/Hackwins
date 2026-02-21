"""
Customer Agent - Customer intelligence, churn prediction, retention strategy
Handles churn prediction, CLV analysis, satisfaction trends, retention
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.agents.base_agent import BaseAgent, AgentResponse, ToolDefinition
from app.schemas.intents import Intent, AgentType
from app.adapters.backend_adapter import get_backend_adapter
from app.tools.tool_registry import Tool, ToolParameters, tool_registry
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CustomerAgent(BaseAgent):
    """
    Customer Agent handles:
    - Churn prediction and risk scoring
    - Customer Lifetime Value (CLV) analysis
    - Retention strategy recommendations
    - Customer segmentation
    - Satisfaction trend analysis
    """

    def __init__(self):
        super().__init__()
        self.backend = get_backend_adapter()
        self._register_customer_tools()
        logger.info("customer_agent_initialized")

    def get_agent_type(self) -> AgentType:
        return AgentType.CUSTOMER_AGENT

    def get_supported_intents(self) -> List[Intent]:
        return [
            Intent.CLIENT_QUERY,
            Intent.CLIENT_HISTORY,
            Intent.CUSTOMER_RETENTION,
            Intent.CUSTOMER_SEGMENTATION,
            Intent.CHURN_PREDICTION,
            Intent.CUSTOMER_LIFETIME_VALUE,
            Intent.CUSTOMER_FEEDBACK_ANALYSIS,
            Intent.CLIENT_CREATE,
            Intent.CLIENT_UPDATE,
            Intent.CLIENT_DELETE,
        ]

    def get_tools(self) -> List[ToolDefinition]:
        tools = tool_registry.get_tools_by_category("customer")
        return [
            ToolDefinition(
                name=t.name,
                description=t.description,
                parameters={p.name: p.type for p in t.parameters},
                enabled=t.enabled,
                mvp_ready=t.mvp_ready
            )
            for t in tools
        ]

    def _register_customer_tools(self):
        churn_prediction_tool = Tool(
            name="predict_churn",
            description="Predict customer churn risk based on payment patterns",
            category="customer",
            mvp_ready=True,
            parameters=[],
            handler=self._handle_churn_prediction
        )

        clv_tool = Tool(
            name="calculate_clv",
            description="Calculate Customer Lifetime Value for all clients",
            category="customer",
            mvp_ready=True,
            parameters=[],
            handler=self._handle_clv_analysis
        )

        segmentation_tool = Tool(
            name="segment_customers",
            description="Segment customers by value, frequency, and behavior",
            category="customer",
            mvp_ready=True,
            parameters=[],
            handler=self._handle_segmentation
        )

        client_query_tool = Tool(
            name="query_clients",
            description="Query and list clients",
            category="customer",
            mvp_ready=True,
            parameters=[
                ToolParameters(name="search", type="string", description="Search term", required=False),
            ],
            handler=self._handle_client_query
        )

        tool_registry.register_tools([
            churn_prediction_tool,
            clv_tool,
            segmentation_tool,
            client_query_tool,
        ])

    async def _handle_churn_prediction(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Predict churn risk based on invoice/payment patterns"""
        org_id = context.get("org_id", "default_org") if context else "default_org"

        clients_resp = await self.backend.get_clients(org_id=org_id, limit=100)
        invoices_resp = await self.backend.get_invoices(org_id=org_id, limit=200)

        clients = []
        if clients_resp.success and clients_resp.data:
            data = clients_resp.data
            clients = data if isinstance(data, list) else data.get("clients", [])

        invoices = []
        if invoices_resp.success and invoices_resp.data:
            invoices = invoices_resp.data.get("invoices", [])

        # Build client invoice map
        client_invoices = {}
        for inv in invoices:
            cid = inv.get("clientId")
            if cid:
                if cid not in client_invoices:
                    client_invoices[cid] = []
                client_invoices[cid].append(inv)

        # Score churn risk for each client
        high_risk = []
        medium_risk = []
        low_risk = []

        for client in clients:
            cid = client.get("id")
            client_invs = client_invoices.get(cid, [])

            if not client_invs:
                high_risk.append({
                    "client": client.get("name", "Unknown"),
                    "risk": "high",
                    "reason": "No recent invoices — possibly churned",
                    "clv": 0,
                })
                continue

            # Check last activity
            sorted_invs = sorted(client_invs, key=lambda x: x.get("issueDate", ""), reverse=True)
            last_invoice = sorted_invs[0]
            last_date_str = last_invoice.get("issueDate", "")

            overdue_count = sum(1 for i in client_invs if i.get("status") == "OVERDUE")
            total = len(client_invs)
            paid = sum(1 for i in client_invs if i.get("status") == "PAID")
            total_value = sum(i.get("totalAmount", 0) for i in client_invs)

            # Risk scoring
            risk_score = 0
            reasons = []
            if overdue_count > 0:
                risk_score += overdue_count * 20
                reasons.append(f"{overdue_count} overdue invoice(s)")
            if paid / total < 0.5:
                risk_score += 30
                reasons.append("Low payment rate")

            if risk_score >= 50:
                high_risk.append({
                    "client": client.get("name", "Unknown"),
                    "risk": "high",
                    "reasons": reasons,
                    "total_value": round(total_value),
                })
            elif risk_score >= 20:
                medium_risk.append({
                    "client": client.get("name", "Unknown"),
                    "risk": "medium",
                    "reasons": reasons,
                    "total_value": round(total_value),
                })
            else:
                low_risk.append({
                    "client": client.get("name", "Unknown"),
                    "risk": "low",
                    "total_value": round(total_value),
                })

        total_at_risk_value = sum(c.get("total_value", 0) for c in high_risk + medium_risk)

        return {
            "churn_analysis": {
                "high_risk_clients": high_risk,
                "medium_risk_clients": medium_risk,
                "low_risk_clients": low_risk,
                "total_at_risk_value": total_at_risk_value,
                "churn_rate_estimate": f"{len(high_risk) / max(len(clients), 1) * 100:.1f}%",
            },
            "retention_actions": [
                f"🚨 Contact {len(high_risk)} high-risk clients within 24 hours",
                "Offer extension or restructured payment plan to overdue clients",
                "Schedule quarterly business reviews with top 20% by revenue",
                "Implement NPS survey to catch dissatisfaction early",
            ],
            "message": f"Churn Risk: {len(high_risk)} high-risk, {len(medium_risk)} medium-risk clients. ₹{total_at_risk_value:,.0f} at risk."
        }

    async def _handle_clv_analysis(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculate Customer Lifetime Value"""
        org_id = context.get("org_id", "default_org") if context else "default_org"

        clients_resp = await self.backend.get_clients(org_id=org_id, limit=100)
        invoices_resp = await self.backend.get_invoices(org_id=org_id, limit=200)

        clients = []
        if clients_resp.success and clients_resp.data:
            data = clients_resp.data
            clients = data if isinstance(data, list) else data.get("clients", [])

        invoices = []
        if invoices_resp.success and invoices_resp.data:
            invoices = invoices_resp.data.get("invoices", [])

        client_clv = []
        for client in clients:
            cid = client.get("id")
            client_invs = [i for i in invoices if i.get("clientId") == cid]
            paid_invs = [i for i in client_invs if i.get("status") == "PAID"]
            total_paid = sum(i.get("totalAmount", 0) for i in paid_invs)

            # Simple CLV: historical spend * estimated retention multiplier
            frequency = len(client_invs)
            clv = total_paid * (1.5 if frequency > 3 else 1.0)

            client_clv.append({
                "client": client.get("name", "Unknown"),
                "historical_revenue": round(total_paid),
                "estimated_clv": round(clv),
                "invoice_count": frequency,
                "segment": "champion" if clv > 100000 else "loyal" if clv > 50000 else "potential" if clv > 20000 else "new",
            })

        # Sort by CLV
        client_clv.sort(key=lambda x: x["estimated_clv"], reverse=True)
        total_portfolio_clv = sum(c["estimated_clv"] for c in client_clv)

        return {
            "clv_analysis": {
                "clients": client_clv[:10],  # Top 10
                "total_portfolio_clv": round(total_portfolio_clv),
                "average_clv": round(total_portfolio_clv / len(client_clv)) if client_clv else 0,
                "top_client": client_clv[0] if client_clv else None,
            },
            "insights": [
                f"Top client contributes ₹{client_clv[0]['estimated_clv']:,.0f} in estimated CLV" if client_clv else "No client data",
                f"Total customer portfolio value: ₹{total_portfolio_clv:,.0f}",
                "Focus retention efforts on Champions and Loyal segments first",
            ],
            "message": f"CLV Analysis: {len(client_clv)} clients, total portfolio value ₹{total_portfolio_clv:,.0f}"
        }

    async def _handle_segmentation(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Segment customers using RFM (Recency, Frequency, Monetary) model"""
        org_id = context.get("org_id", "default_org") if context else "default_org"

        invoices_resp = await self.backend.get_invoices(org_id=org_id, limit=200)
        invoices = []
        if invoices_resp.success and invoices_resp.data:
            invoices = invoices_resp.data.get("invoices", [])

        # Group by client
        client_data: Dict[str, Dict] = {}
        for inv in invoices:
            cid = inv.get("clientId", "unknown")
            if cid not in client_data:
                client_data[cid] = {"invoices": [], "name": f"Client {cid[:6]}"}
            client_data[cid]["invoices"].append(inv)

        segments = {"Champions": [], "Loyal": [], "At Risk": [], "New": [], "Lost": []}

        for cid, data in client_data.items():
            paid = [i for i in data["invoices"] if i.get("status") == "PAID"]
            overdue = [i for i in data["invoices"] if i.get("status") == "OVERDUE"]
            frequency = len(data["invoices"])
            monetary = sum(i.get("totalAmount", 0) for i in paid)

            if monetary > 100000 and frequency > 5:
                segments["Champions"].append({"id": cid, "value": round(monetary)})
            elif monetary > 50000:
                segments["Loyal"].append({"id": cid, "value": round(monetary)})
            elif overdue:
                segments["At Risk"].append({"id": cid, "value": round(monetary)})
            elif frequency <= 2:
                segments["New"].append({"id": cid, "value": round(monetary)})
            else:
                segments["Lost"].append({"id": cid, "value": round(monetary)})

        return {
            "segments": {
                name: {"count": len(clients), "total_value": sum(c["value"] for c in clients)}
                for name, clients in segments.items()
            },
            "recommendations": {
                "Champions": "Reward and upsell — they are your best advocates",
                "Loyal": "Offer loyalty rewards to convert to Champions",
                "At Risk": "Immediate outreach — risk of losing them",
                "New": "Nurture with onboarding and early success stories",
                "Lost": "Win-back campaign with special offer",
            },
            "message": f"Customer Segmentation: {len(segments['Champions'])} Champions, {len(segments['At Risk'])} At Risk"
        }

    async def _handle_client_query(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query clients"""
        org_id = context.get("org_id", "default_org") if context else "default_org"
        search = params.get("search")

        resp = await self.backend.get_clients(org_id=org_id, search=search, limit=50)
        if resp.success:
            data = resp.data
            clients = data if isinstance(data, list) else data.get("clients", []) if data else []
            return {
                "clients": clients,
                "count": len(clients),
                "message": f"Found {len(clients)} client(s)"
            }
        raise Exception(resp.error or "Failed to get clients")

    async def process(
        self,
        intent: Intent,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        logger.info("customer_agent_processing", intent=intent.value)

        if context and context.get("auth_token"):
            self.backend.set_auth_token(context["auth_token"])

        intent_to_tool = {
            Intent.CLIENT_QUERY: "query_clients",
            Intent.CLIENT_HISTORY: "calculate_clv",
            Intent.CUSTOMER_RETENTION: "predict_churn",
            Intent.CUSTOMER_SEGMENTATION: "segment_customers",
            Intent.CHURN_PREDICTION: "predict_churn",
            Intent.CUSTOMER_LIFETIME_VALUE: "calculate_clv",
            Intent.CUSTOMER_FEEDBACK_ANALYSIS: "segment_customers",
        }

        tool_name = intent_to_tool.get(intent, "query_clients")

        try:
            result = await tool_registry.execute_tool(tool_name=tool_name, parameters=entities, context=context)
            if result.success:
                return self._build_success_response(
                    message=result.result.get("message", "Customer analysis complete"),
                    data=result.result,
                    tool_used=tool_name
                )
            return self._build_error_response(result.error or "Customer tool failed")
        except Exception as e:
            logger.error("customer_agent_error", error=str(e))
            return self._build_error_response(str(e))


# Singleton
customer_agent = CustomerAgent()
