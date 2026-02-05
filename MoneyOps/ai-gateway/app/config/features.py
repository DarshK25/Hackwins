"""
Feature Flags - Control which features are enabled
Easy toggling between MVP and v2.0 features
"""
from pydantic_settings import BaseSettings


class FeatureFlags(BaseSettings):
    """
    Feature flags for MVP vs Full version
    Toggle these to enable/disable features without code changes
    """
    
    # === MVP FEATURES (Enabled for 3-week deadline) ===
    ENABLE_INVOICE_OPERATIONS: bool = True
    ENABLE_PAYMENT_OPERATIONS: bool = True
    ENABLE_CLIENT_OPERATIONS: bool = True
    ENABLE_TRANSACTION_QUERIES: bool = True
    ENABLE_VOICE_INTERFACE: bool = True
    ENABLE_CHAT_INTERFACE: bool = True
    
    # === STRATEGIC FEATURES (Disabled for MVP, enable in v2.0) ===
    ENABLE_HEALTH_SCORING: bool = False          # Business health /100
    ENABLE_STRATEGIC_RECOMMENDATIONS: bool = False  # AI recommendations
    ENABLE_COMPETITOR_ANALYSIS: bool = False     # Market intelligence
    ENABLE_ML_FORECASTING: bool = False          # Revenue/sales forecasting
    ENABLE_MULTI_AGENT_ORCHESTRATION: bool = False  # Complex multi-agent workflows
    ENABLE_CUSTOMER_CHURN_PREDICTION: bool = False  # ML-based churn
    ENABLE_PRICING_OPTIMIZATION: bool = False    # Dynamic pricing
    
    # === AGENTS (MVP: Only Finance operational) ===
    ENABLE_FINANCE_AGENT: bool = True            # Operational CRUD
    ENABLE_SALES_AGENT: bool = False             # v2.0
    ENABLE_STRATEGY_AGENT: bool = False          # v2.0
    ENABLE_COMPLIANCE_AGENT: bool = False        # v2.0
    ENABLE_CUSTOMER_AGENT: bool = False          # v2.0
    ENABLE_GROWTH_AGENT: bool = False            # v2.0
    ENABLE_OPERATIONS_AGENT: bool = False        # v2.0
    
    # === INFRASTRUCTURE (Add later) ===
    ENABLE_VECTOR_DB: bool = False               # Pinecone for benchmarks
    ENABLE_REDIS_CACHE: bool = False             # Response caching
    ENABLE_KAFKA_EVENTS: bool = False            # Event streaming
    ENABLE_ML_MODELS: bool = False               # Local ML models
    
    # === EXTERNAL SERVICES ===
    ENABLE_WEB_SCRAPING: bool = False            # Competitor data
    ENABLE_INDUSTRY_BENCHMARKS: bool = False     # External benchmark APIs
    
    class Config:
        env_file = ".env"
        env_prefix = "FEATURE_"


# Global singleton
feature_flags = FeatureFlags()