"""
Intent definitions and schemas
"""
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class Intent(str, Enum):
    """All possible user intents"""
    # Invoice operations
    INVOICE_QUERY = "INVOICE_QUERY"
    INVOICE_CREATE = "INVOICE_CREATE"
    INVOICE_UPDATE = "INVOICE_UPDATE"
    INVOICE_DELETE = "INVOICE_DELETE"
    INVOICE_SEND = "INVOICE_SEND"
    INVOICE_STATUS_CHECK = "INVOICE_STATUS_CHECK"
    INVOICE_DOWNLOAD = "INVOICE_DOWNLOAD"

    # Client operations
    CLIENT_QUERY = "CLIENT_QUERY"
    CLIENT_CREATE = "CLIENT_CREATE"
    CLIENT_UPDATE = "CLIENT_UPDATE"
    CLIENT_DELETE = "CLIENT_DELETE"
    CLIENT_HISTORY = "CLIENT_HISTORY"

    # Transaction & Payment operations
    TRANSACTION_QUERY = "TRANSACTION_QUERY"
    TRANSACTION_CREATE = "TRANSACTION_CREATE"
    PAYMENT_RECORD = "PAYMENT_RECORD"
    PAYMENT_QUERY = "PAYMENT_QUERY"
    BALANCE_CHECK = "BALANCE_CHECK"
    ACCOUNT_STATEMENT = "ACCOUNT_STATEMENT"

    # Reminder operations
    REMINDER_CREATE = "REMINDER_CREATE"
    REMINDER_LIST = "REMINDER_LIST"
    REMINDER_CANCEL = "REMINDER_CANCEL"

    # Document operations
    DOCUMENT_UPLOAD = "DOCUMENT_UPLOAD"
    DOCUMENT_QUERY = "DOCUMENT_QUERY"
    DOCUMENT_ANALYZE = "DOCUMENT_ANALYZE"

    # Compliance operations
    COMPLIANCE_QUERY = "COMPLIANCE_QUERY"
    COMPLIANCE_CHECK = "COMPLIANCE_CHECK"
    COMPLIANCE_REPORT = "COMPLIANCE_REPORT"
    GST_QUERY = "GST_QUERY"

    # Strategic / Analytical
    BUSINESS_HEALTH_CHECK = "BUSINESS_HEALTH_CHECK"
    PROBLEM_DIAGNOSIS = "PROBLEM_DIAGNOSIS"
    BUDGET_OPTIMIZATION = "BUDGET_OPTIMIZATION"
    CASH_FLOW_PLANNING = "CASH_FLOW_PLANNING"
    PROFIT_OPTIMIZATION = "PROFIT_OPTIMIZATION"
    INVESTMENT_ADVICE = "INVESTMENT_ADVICE"
    DEBT_MANAGEMENT = "DEBT_MANAGEMENT"

    # Sales & Marketing
    SALES_STRATEGY = "SALES_STRATEGY"
    CUSTOMER_ACQUISITION = "CUSTOMER_ACQUISITION"
    PRICING_STRATEGY = "PRICING_STRATEGY"
    MARKETING_OPTIMIZATION = "MARKETING_OPTIMIZATION"
    CUSTOMER_RETENTION = "CUSTOMER_RETENTION"
    COMPETITIVE_POSITIONING = "COMPETITIVE_POSITIONING"

    # Growth & Expansion
    GROWTH_STRATEGY = "GROWTH_STRATEGY"
    MARKET_EXPANSION = "MARKET_EXPANSION"
    PRODUCT_STRATEGY = "PRODUCT_STRATEGY"
    SCALING_ADVICE = "SCALING_ADVICE"
    PARTNERSHIP_OPPORTUNITIES = "PARTNERSHIP_OPPORTUNITIES"

    # Risk & Compliance (continued)
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    TAX_OPTIMIZATION = "TAX_OPTIMIZATION"
    TAX_CALCULATION = "TAX_CALCULATION"
    AUDIT_READINESS = "AUDIT_READINESS"

    # Customer Intelligence
    CUSTOMER_SEGMENTATION = "CUSTOMER_SEGMENTATION"
    CHURN_PREDICTION = "CHURN_PREDICTION"
    CUSTOMER_LIFETIME_VALUE = "CUSTOMER_LIFETIME_VALUE"
    CUSTOMER_FEEDBACK_ANALYSIS = "CUSTOMER_FEEDBACK_ANALYSIS"

    # Reports & Analytics
    REPORT_GENERATE = "REPORT_GENERATE"
    ANALYTICS_QUERY = "ANALYTICS_QUERY"
    FORECAST_REQUEST = "FORECAST_REQUEST"
    BENCHMARK_COMPARISON = "BENCHMARK_COMPARISON"
    TREND_ANALYSIS = "TREND_ANALYSIS"

    # Strategic Planning
    SWOT_ANALYSIS = "SWOT_ANALYSIS"
    SCENARIO_PLANNING = "SCENARIO_PLANNING"
    GOAL_SETTING = "GOAL_SETTING"

    # Operational Efficiency
    PROCESS_OPTIMIZATION = "PROCESS_OPTIMIZATION"
    INVENTORY_OPTIMIZATION = "INVENTORY_OPTIMIZATION"
    RESOURCE_ALLOCATION = "RESOURCE_ALLOCATION"

    # Conversational & Utility
    GENERAL_QUERY = "GENERAL_QUERY"
    GREETING = "GREETING"
    HELP = "HELP"
    CONFIRMATION = "CONFIRMATION"
    CANCELLATION = "CANCELLATION"
    CLARIFICATION_REQUEST = "CLARIFICATION_REQUEST"
    FOLLOWUP_QUESTION = "FOLLOWUP_QUESTION"
    FEEDBACK = "FEEDBACK"

    # Voice-specific
    REPEAT_REQUEST = "REPEAT_REQUEST"
    SLOW_DOWN = "SLOW_DOWN"
    SPEED_UP = "SPEED_UP"


class LineItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None
    is_service: bool = False


class InvoiceCreatePayload(BaseModel):
    client_name: str
    items: List[LineItem]
    subtotal: float
    tax: Optional[float] = 0.0
    total: float
    due_date: Optional[str] = None
    notes: Optional[str] = None


class IntentCategory(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    STRATEGIC = "STRATEGIC"
    ANALYTICAL = "ANALYTICAL"
    CONVERSATIONAL = "CONVERSATIONAL"
    ADMINISTRATIVE = "ADMINISTRATIVE"


class AgentType(str, Enum):
    FINANCE_AGENT = "FINANCE_AGENT"
    SALES_AGENT = "SALES_AGENT"
    GROWTH_AGENT = "GROWTH_AGENT"
    STRATEGY_AGENT = "STRATEGY_AGENT"
    COMPLIANCE_AGENT = "COMPLIANCE_AGENT"
    CUSTOMER_AGENT = "CUSTOMER_AGENT"
    OPERATIONS_AGENT = "OPERATIONS_AGENT"
    GENERAL_AGENT = "GENERAL_AGENT"


class ComplexityLevel(str, Enum):
    SIMPLE = "SIMPLE"
    MEDIUM = "MEDIUM"
    COMPLEX = "COMPLEX"
    STRATEGIC = "STRATEGIC"


class IntentClassification(BaseModel):
    intent: Intent
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    sub_intent: Optional[str] = None

    # Routing information
    category: IntentCategory
    primary_agent: AgentType
    supporting_agents: List[AgentType] = Field(default_factory=list)
    complexity: ComplexityLevel

    # Requirements
    requires_confirmation: bool = False
    requires_multi_turn: bool = False

    # Context from previous turns
    is_followup: bool = False
    previous_intent: Optional[Intent] = None
    conversation_context: Optional[Dict[str, Any]] = None

    # Metadata
    processing_time_ms: Optional[float] = None
    model_name: Optional[str] = None


class IntentRequirements(BaseModel):
    required_entities: List[str] = Field(default_factory=list)
    optional_entities: List[str] = Field(default_factory=list)
    requires_user_confirmation: bool = False
    minimum_confidence: float = Field(ge=0.0, le=1.0, default=0.7)

    # Agent routing
    primary_agent: AgentType
    supporting_agents: List[AgentType] = Field(default_factory=list)
    complexity: ComplexityLevel = ComplexityLevel.SIMPLE

    # Control
    requires_multi_turn: bool = False
    expected_response_format: str = "text"
    max_response_time_seconds: int = 5

    # Data requirements
    requires_historical_data: bool = False
    requires_external_data: bool = False
    requires_ml_model: bool = False


DEFAULT_OPERATIONAL = IntentRequirements(
    primary_agent=AgentType.OPERATIONS_AGENT,
    complexity=ComplexityLevel.SIMPLE,
)

DEFAULT_ANALYTICAL = IntentRequirements(
    primary_agent=AgentType.FINANCE_AGENT,
    complexity=ComplexityLevel.COMPLEX,
    requires_historical_data=True,
    expected_response_format="chart",
)

DEFAULT_STRATEGIC = IntentRequirements(
    primary_agent=AgentType.STRATEGY_AGENT,
    supporting_agents=[AgentType.FINANCE_AGENT],
    complexity=ComplexityLevel.STRATEGIC,
    requires_historical_data=True,
    requires_ml_model=True,
    expected_response_format="report",
    max_response_time_seconds=15,
)

DEFAULT_CONVERSATIONAL = IntentRequirements(
    primary_agent=AgentType.GENERAL_AGENT,
    minimum_confidence=0.4,
    max_response_time_seconds=2,
)

INTENT_REQUIREMENTS: Dict[Intent, IntentRequirements] = {
    Intent.INVOICE_CREATE: IntentRequirements(
        required_entities=["client_name", "items"],
        optional_entities=["due_date", "notes", "tax"],
        requires_user_confirmation=True,
        minimum_confidence=0.8,
        primary_agent=AgentType.FINANCE_AGENT,
        expected_response_format="json",
    ),
    Intent.INVOICE_QUERY: IntentRequirements(
        optional_entities=["invoice_id", "client_name", "date_range", "status"],
        primary_agent=AgentType.FINANCE_AGENT,
    ),
    Intent.INVOICE_UPDATE: IntentRequirements(
        required_entities=["invoice_id"],
        optional_entities=["items", "due_date", "notes", "tax", "status"],
        requires_user_confirmation=True,
        primary_agent=AgentType.FINANCE_AGENT,
    ),
    Intent.INVOICE_DELETE: IntentRequirements(
        required_entities=["invoice_id"],
        requires_user_confirmation=True,
        primary_agent=AgentType.FINANCE_AGENT,
    ),
    Intent.INVOICE_SEND: IntentRequirements(
        required_entities=["invoice_id"],
        optional_entities=["delivery_method"],
        primary_agent=AgentType.SALES_AGENT,
    ),
    Intent.INVOICE_STATUS_CHECK: IntentRequirements(
        required_entities=["invoice_id"],
        primary_agent=AgentType.FINANCE_AGENT,
    ),
    Intent.INVOICE_DOWNLOAD: IntentRequirements(
        required_entities=["invoice_id"],
        optional_entities=["format"],
        primary_agent=AgentType.FINANCE_AGENT,
        expected_response_format="file",
    ),

    Intent.CLIENT_CREATE: IntentRequirements(
        required_entities=["client_name", "email"],
        optional_entities=["phone", "address", "gst_number"],
        requires_user_confirmation=True,
        primary_agent=AgentType.CUSTOMER_AGENT,
    ),
    Intent.CLIENT_UPDATE: IntentRequirements(
        required_entities=["client_id"],
        optional_entities=["email", "phone", "address"],
        requires_user_confirmation=True,
        primary_agent=AgentType.CUSTOMER_AGENT,
    ),
    Intent.CLIENT_DELETE: IntentRequirements(
        required_entities=["client_id"],
        requires_user_confirmation=True,
        primary_agent=AgentType.CUSTOMER_AGENT,
    ),
    Intent.CLIENT_QUERY: IntentRequirements(
        optional_entities=["client_id", "client_name"],
        primary_agent=AgentType.CUSTOMER_AGENT,
    ),
    Intent.CLIENT_HISTORY: IntentRequirements(
        required_entities=["client_id"],
        primary_agent=AgentType.CUSTOMER_AGENT,
        complexity=ComplexityLevel.MEDIUM,
        requires_historical_data=True,
    ),

    Intent.TRANSACTION_CREATE: IntentRequirements(
        required_entities=["amount", "transaction_type"],
        optional_entities=["date", "notes", "category", "payment_method", "invoice_id"],
        requires_user_confirmation=True,
        primary_agent=AgentType.FINANCE_AGENT,
    ),
    Intent.TRANSACTION_QUERY: IntentRequirements(
        optional_entities=["date_range", "type", "category", "account"],
        primary_agent=AgentType.FINANCE_AGENT,
        requires_historical_data=True,
    ),

    Intent.PAYMENT_RECORD: IntentRequirements(
        required_entities=["invoice_id", "amount"],
        optional_entities=["payment_method", "payment_date", "notes"],
        requires_user_confirmation=True,
        minimum_confidence=0.9,
        primary_agent=AgentType.FINANCE_AGENT,
    ),
    Intent.PAYMENT_QUERY: IntentRequirements(
        optional_entities=["invoice_id", "date_range", "payment_method"],
        primary_agent=AgentType.FINANCE_AGENT,
        requires_historical_data=True,
    ),
    Intent.BALANCE_CHECK: IntentRequirements(
        optional_entities=["client_name", "account"],
        primary_agent=AgentType.FINANCE_AGENT,
    ),
    Intent.ACCOUNT_STATEMENT: IntentRequirements(
        required_entities=["date_range"],
        optional_entities=["account"],
        primary_agent=AgentType.FINANCE_AGENT,
        complexity=ComplexityLevel.MEDIUM,
        requires_historical_data=True,
        expected_response_format="table",
    ),

    Intent.REMINDER_CREATE: DEFAULT_OPERATIONAL,
    Intent.REMINDER_LIST: DEFAULT_OPERATIONAL,
    Intent.REMINDER_CANCEL: DEFAULT_OPERATIONAL,

    Intent.DOCUMENT_UPLOAD: DEFAULT_OPERATIONAL,
    Intent.DOCUMENT_QUERY: DEFAULT_OPERATIONAL,
    Intent.DOCUMENT_ANALYZE: IntentRequirements(
        required_entities=["document_id"],
        primary_agent=AgentType.GENERAL_AGENT,
        complexity=ComplexityLevel.COMPLEX,
        requires_ml_model=True,
    ),

    Intent.COMPLIANCE_QUERY: DEFAULT_STRATEGIC,
    Intent.COMPLIANCE_CHECK: DEFAULT_STRATEGIC,
    Intent.COMPLIANCE_REPORT: DEFAULT_STRATEGIC,
    Intent.GST_QUERY: DEFAULT_STRATEGIC,
    Intent.TAX_OPTIMIZATION: DEFAULT_STRATEGIC,
    Intent.TAX_CALCULATION: DEFAULT_STRATEGIC,
    Intent.AUDIT_READINESS: DEFAULT_STRATEGIC,

    Intent.BUSINESS_HEALTH_CHECK: DEFAULT_STRATEGIC,
    Intent.PROBLEM_DIAGNOSIS: DEFAULT_STRATEGIC,
    Intent.BUDGET_OPTIMIZATION: DEFAULT_STRATEGIC,
    Intent.CASH_FLOW_PLANNING: DEFAULT_STRATEGIC,
    Intent.PROFIT_OPTIMIZATION: DEFAULT_STRATEGIC,
    Intent.INVESTMENT_ADVICE: DEFAULT_STRATEGIC,
    Intent.DEBT_MANAGEMENT: DEFAULT_STRATEGIC,
    Intent.SALES_STRATEGY: DEFAULT_STRATEGIC,
    Intent.CUSTOMER_ACQUISITION: DEFAULT_STRATEGIC,
    Intent.PRICING_STRATEGY: DEFAULT_STRATEGIC,
    Intent.MARKETING_OPTIMIZATION: DEFAULT_STRATEGIC,
    Intent.CUSTOMER_RETENTION: DEFAULT_STRATEGIC,
    Intent.GROWTH_STRATEGY: DEFAULT_STRATEGIC,
    Intent.MARKET_EXPANSION: DEFAULT_STRATEGIC,
    Intent.PRODUCT_STRATEGY: DEFAULT_STRATEGIC,
    Intent.SCALING_ADVICE: DEFAULT_STRATEGIC,
    Intent.PARTNERSHIP_OPPORTUNITIES: DEFAULT_STRATEGIC,
    Intent.RISK_ASSESSMENT: DEFAULT_STRATEGIC,
    Intent.CUSTOMER_SEGMENTATION: DEFAULT_STRATEGIC,
    Intent.CHURN_PREDICTION: DEFAULT_STRATEGIC,
    Intent.CUSTOMER_LIFETIME_VALUE: DEFAULT_STRATEGIC,
    Intent.CUSTOMER_FEEDBACK_ANALYSIS: DEFAULT_STRATEGIC,

    Intent.REPORT_GENERATE: DEFAULT_ANALYTICAL,
    Intent.ANALYTICS_QUERY: DEFAULT_ANALYTICAL,
    Intent.FORECAST_REQUEST: DEFAULT_ANALYTICAL,
    Intent.BENCHMARK_COMPARISON: DEFAULT_ANALYTICAL,
    Intent.TREND_ANALYSIS: DEFAULT_ANALYTICAL,

    Intent.GENERAL_QUERY: DEFAULT_CONVERSATIONAL,
    Intent.GREETING: DEFAULT_CONVERSATIONAL,
    Intent.HELP: DEFAULT_CONVERSATIONAL,
    Intent.CONFIRMATION: DEFAULT_CONVERSATIONAL,
    Intent.CANCELLATION: DEFAULT_CONVERSATIONAL,
    Intent.CLARIFICATION_REQUEST: DEFAULT_CONVERSATIONAL,
    Intent.FOLLOWUP_QUESTION: DEFAULT_CONVERSATIONAL,
    Intent.FEEDBACK: DEFAULT_CONVERSATIONAL,
    Intent.REPEAT_REQUEST: DEFAULT_CONVERSATIONAL,
    Intent.SLOW_DOWN: DEFAULT_CONVERSATIONAL,
    Intent.SPEED_UP: DEFAULT_CONVERSATIONAL,
}

class ConfidenceLevel(str, Enum):
    """
    Confidence level categories
    """
    HIGH = "HIGH"  # >= 0.85
    MEDIUM = "MEDIUM"  # >= 0.7 and < 0.85
    LOW = "LOW"  # >= 0.5 and < 0.7
    VERY_LOW = "VERY_LOW"  # < 0.5

def get_confidence_level(confidence: float) -> ConfidenceLevel:
    """
    Get confidence level category.

    Returns:
        ConfidenceLevel: Enum value representing HIGH, MEDIUM, LOW, VERY_LOW
    """
    if confidence >= 0.85:
        return ConfidenceLevel.HIGH
    elif confidence >= 0.7:
        return ConfidenceLevel.MEDIUM
    elif confidence >= 0.5:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.VERY_LOW
    
def get_intent_requirements(intent: Intent) -> IntentRequirements:
    """
    Return the requirements for a given intent (falls back to DEFAULT_OPERATIONAL).
    """
    return INTENT_REQUIREMENTS.get(intent, DEFAULT_OPERATIONAL)


def get_intent_category(intent: Intent) -> IntentCategory:
    """
    Derive a high-level category for an intent based on its requirements.

    Returns:
        STRATEGIC: Complex/strategic intents requiring deep analysis
        CONVERSATIONAL: Greetings, help, general chat
        ANALYTICAL: Reports, charts, historical data queries
        OPERATIONAL: Basic CRUD operations (default)
    """
    req = get_intent_requirements(intent)

    # Strategic/Complex intents
    if req.complexity in {ComplexityLevel.STRATEGIC, ComplexityLevel.COMPLEX}:
        return IntentCategory.STRATEGIC

    # Conversational intents handled by general agent
    if req.primary_agent == AgentType.GENERAL_AGENT:
        return IntentCategory.CONVERSATIONAL

    # Analytical intents (charts/reports/historical data)
    if req.requires_historical_data or req.expected_response_format in {"chart", "table", "file"}:
        return IntentCategory.ANALYTICAL

    # Default to operational
    return IntentCategory.OPERATIONAL

def requires_multi_agent(intent : Intent) -> bool:
    """
    check if intent requires multi-agent orchestration
    """
    requirements = get_intent_requirements(intent)
    return len(requirements.supporting_agents) > 0 
# or requirements.complexity in {ComplexityLevel.COMPLEX, ComplexityLevel.STRATEGIC}

def get_expected_response_time(intent: Intent) -> int:
    """
    Get expected response time for intent
    """
    requirements = get_intent_requirements(intent)
    return requirements.max_response_time_seconds