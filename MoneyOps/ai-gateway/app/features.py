"""
Feature Flags - Control which features are enabled
All strategic features NOW ENABLED for hackathon demo
"""
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore[import]
except ImportError:  # pragma: no cover
    from pydantic import BaseSettings  # type: ignore[no-redef]
    SettingsConfigDict = dict  # type: ignore[assignment,misc]


class FeatureFlags(BaseSettings):
    """
    Feature flags for MVP vs Full version
    Toggle these to enable/disable features without code changes
    """
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FEATURE_", extra="ignore")
    
    # === MVP FEATURES ===
    ENABLE_INVOICE_OPERATIONS: bool = True
    ENABLE_PAYMENT_OPERATIONS: bool = True
    ENABLE_CLIENT_OPERATIONS: bool = True
    ENABLE_TRANSACTION_QUERIES: bool = True
    ENABLE_VOICE_INTERFACE: bool = True
    ENABLE_CHAT_INTERFACE: bool = True
    
    # === STRATEGIC FEATURES (ALL ENABLED) ===
    ENABLE_HEALTH_SCORING: bool = True          # Business health /100
    ENABLE_STRATEGIC_RECOMMENDATIONS: bool = True  # AI recommendations
    ENABLE_COMPETITOR_ANALYSIS: bool = True     # Market intelligence
    ENABLE_ML_FORECASTING: bool = True          # Revenue/sales forecasting
    ENABLE_MULTI_AGENT_ORCHESTRATION: bool = True  # Complex multi-agent workflows
    ENABLE_CUSTOMER_CHURN_PREDICTION: bool = True  # ML-based churn
    ENABLE_PRICING_OPTIMIZATION: bool = True    # Dynamic pricing
    
    # === AGENTS (ALL ENABLED) ===
    ENABLE_FINANCE_AGENT: bool = True            # Operational CRUD + Strategic
    ENABLE_SALES_AGENT: bool = True              # CAC, LTV, pipeline
    ENABLE_STRATEGY_AGENT: bool = True           # SWOT, growth, synthesis
    ENABLE_COMPLIANCE_AGENT: bool = True         # GST, tax, regulatory
    ENABLE_CUSTOMER_AGENT: bool = True           # Churn, retention, CLV
    ENABLE_GROWTH_AGENT: bool = True             # Market expansion, pricing
    ENABLE_OPERATIONS_AGENT: bool = True         # Process efficiency
    
    # === INFRASTRUCTURE ===
    ENABLE_VECTOR_DB: bool = False               # Pinecone for benchmarks
    ENABLE_REDIS_CACHE: bool = False             # Response caching
    ENABLE_KAFKA_EVENTS: bool = False            # Event streaming
    ENABLE_ML_MODELS: bool = False               # Local ML models
    
    # === EXTERNAL SERVICES ===
    ENABLE_WEB_SCRAPING: bool = False            # Competitor data
    ENABLE_INDUSTRY_BENCHMARKS: bool = True      # Benchmark comparisons (rule-based)




# Global singleton
feature_flags = FeatureFlags()
