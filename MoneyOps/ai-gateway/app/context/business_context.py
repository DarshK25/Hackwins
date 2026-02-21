"""
Business Context Builder
Builds comprehensive business understanding for strategic intelligence
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class BusinessContext:
    org_id: str
    industry: str = "Unknown"
    business_model: str = "Unknown"
    challenges: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    financial_health: float = 0.0
    key_metrics: Dict[str, Any] = field(default_factory=dict)
    insights: List[str] = field(default_factory=list)
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "org_id": self.org_id,
            "industry": self.industry,
            "business_model": self.business_model,
            "challenges": self.challenges,
            "goals": self.goals,
            "financial_health": self.financial_health,
            "key_metrics": self.key_metrics,
            "insights": self.insights,
            "last_updated": self.last_updated,
        }

    def to_prompt_context(self) -> str:
        """Convert context to a string suitable for LLM prompts"""
        lines = [
            f"Industry: {self.industry}",
            f"Business Model: {self.business_model}",
        ]
        if self.challenges:
            lines.append(f"Key Challenges: {', '.join(self.challenges)}")
        if self.goals:
            lines.append(f"Business Goals: {', '.join(self.goals)}")
        if self.financial_health:
            lines.append(f"Financial Health Score: {self.financial_health:.0f}/100")
        if self.key_metrics:
            for k, v in self.key_metrics.items():
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)


class BusinessContextBuilder:
    """
    Builds comprehensive business understanding from onboarding data,
    historical transactions, and provided context.
    """

    def build_context(
        self,
        org_id: str,
        org_data: Optional[Dict[str, Any]] = None,
        financial_summary: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[Dict[str, Any]] = None,
    ) -> BusinessContext:
        """Build a BusinessContext from available data"""

        # Extract org details
        industry = "Unknown"
        business_model = "Unknown"
        challenges = []
        goals = []

        if org_data:
            industry = org_data.get("industry", industry)
            business_model = org_data.get("businessModel", business_model)
            challenges = org_data.get("challenges", challenges)
            goals = org_data.get("goals", goals)

        # Extract financial metrics
        key_metrics = {}
        financial_health = 0.0

        if financial_summary:
            revenue = financial_summary.get("totalRevenue", 0)
            expenses = financial_summary.get("totalExpenses", 0)
            net_profit = financial_summary.get("netProfit", 0)
            invoice_count = financial_summary.get("invoiceCount", 0)
            paid_invoices = financial_summary.get("paidInvoices", 0)
            overdue_invoices = financial_summary.get("overdueInvoices", 0)

            key_metrics = {
                "Monthly Revenue": f"₹{revenue:,.0f}",
                "Monthly Expenses": f"₹{expenses:,.0f}",
                "Net Profit": f"₹{net_profit:,.0f}",
                "Profit Margin": f"{(net_profit/revenue*100):.1f}%" if revenue > 0 else "N/A",
                "Total Invoices": invoice_count,
                "Paid Invoices": paid_invoices,
                "Overdue Invoices": overdue_invoices,
            }

            # Calculate basic health score
            if revenue > 0:
                profit_margin = net_profit / revenue
                collection_rate = paid_invoices / invoice_count if invoice_count > 0 else 0
                financial_health = min(100, max(0, (profit_margin * 50 + collection_rate * 50) * 100))

        # Also check direct conversation_context for metrics
        if conversation_context:
            for k, v in conversation_context.items():
                if k not in ("user_id", "org_id", "session_id", "auth_token", "channel", "conversation_history"):
                    key_metrics[k] = v

        return BusinessContext(
            org_id=org_id,
            industry=industry,
            business_model=business_model,
            challenges=challenges,
            goals=goals,
            financial_health=financial_health,
            key_metrics=key_metrics,
            last_updated=datetime.now().isoformat(),
        )

    def enrich_system_prompt(
        self,
        base_prompt: str,
        context: BusinessContext
    ) -> str:
        """Add business context to a system prompt"""
        context_block = f"""

BUSINESS CONTEXT:
{context.to_prompt_context()}

You have access to this business's real data. When answering strategic questions:
1. Reference specific metrics from the context above
2. Provide quantified insights with numbers
3. Give actionable recommendations with estimated impact
4. Think like a CEO/CFO advising this specific business
"""
        return base_prompt + context_block


# Singleton
business_context_builder = BusinessContextBuilder()
