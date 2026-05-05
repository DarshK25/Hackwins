# MoneyOps - True Agent-Native SaaS

**Agent-Native Financial Operations Platform** that solves the 90-120 day payment delay problem for Indian SMBs.

## Architecture: True Multi-Agent with Real Execution

```
[Frontend (React)] → [API Gateway (FastAPI)] → [MasterOrchestrator]
                                                    ↓
                            [Executors with REAL API calls]
                              - FinanceExecutor (invoices, payments)
                              - ComplianceExecutor (GST, TDS)
                              - CollectionsExecutor (WhatsApp/SMS reminders)
                              - TReDSExecutor (working capital)
                                                    ↓
                            [Spring Boot Backend] ← gRPC → [PostgreSQL + Mongo]
                                                    ↓
                            [External Services]
                              - Twilio (WhatsApp/SMS)
                              - Pinecone (vector memory)
                              - TReDS (invoice discounting)
```

## Key Differentiators (Research-Backed)

| Feature | What SMBs Actually Pay For | Status |
|---------|---------------------------|--------|
| **Automated Collections** | WhatsApp reminders reduce 90-day delays | ✅ Twilio integrated |
| **TReDS Working Capital** | Get cash now, not in 90 days (8-12% fee) | ✅ TReDSExecutor ready |
| **GST Automation** | Auto-reconciliation GSTR-2A/2B | ✅ ComplianceExecutor + Pinecone RAG |
| **Account Aggregation** | Real-time cash visibility across banks | 🔄 Proto ready |
| **Agent-Native** | True agents that EXECUTE, not just chat | ✅ LangGraph-style executors |

## Tech Stack (Industry Standard)

### Backend
- **Spring Boot** (port 8000) - Core invoicing, payments, clients
- **FastAPI** (port 8001) - AI Gateway with true agent orchestration
- **LiveKit** (port 8003) - Voice agent with STT/TTS

### Agents (True Executors, Not Simulations)
```python
# app/agents/base_executor.py
class FinanceExecutor(BaseExecutor):
    """Executes: create invoice, record payment, check balance"""

class CollectionsExecutor(BaseExecutor):
    """Executes: send WhatsApp/SMS reminders, escalate overdue"""

class TReDSExecutor(BaseExecutor):
    """Executes: discount invoices, get working capital instantly"""
```

### LLM Routing (Task-Based, Not Random)
```python
# app/llm/multi_provider.py
REALTIME → Groq (2800 tok/s) for instant voice
HIGH_VOLUME → Cerebras (14,400/day free) for bulk ops
LONG_CONTEXT → Gemini (1M tokens) for compliance RAG
```

### Data Layer
- **Mongo (Atlas)**: Invoices, clients, transactions (flexible schema)
- **PostgreSQL**: Financial metrics, compliance data (ACID)
- **Pinecone**: Vector memory for GST rules, client patterns (RAG)
- **Redis**: Distributed cache, rate limiting, session store

### Communication
- **Browser ↔ Backend**: REST/JSON (standard)
- **Service-to-Service**: gRPC/Protobuf (low-latency, `protos/moneyops.proto`)
- **Collections**: Twilio WhatsApp/SMS (instant setup, no Meta approval)

## Quick Start

### 1. Environment Setup
```bash
# Copy and fill .env (use your own API keys)
cp MoneyOps/.env.example MoneyOps/.env

# Required keys:
# - MONGODB_URI (Mongo Atlas)
# - GROQ_API_KEY, CEREBRAS_API_KEY, GEMINI_API_KEY
# - TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN (for WhatsApp/SMS)
# - PINECONE_API_KEY (vector memory)
```

### 2. Start Services
```bash
# Terminal 1: Spring Boot Backend (port 8000)
cd MoneyOps/backend && ./mvnw spring-boot:run

# Terminal 2: AI Gateway (port 8001)
cd MoneyOps/ai-gateway && uvicorn app.main:app --reload

# Terminal 3: Voice Service (port 8003)
cd MoneyOps/voice-service && python -m app.main

# Terminal 4: Frontend (port 5173)
cd MoneyOps/Frontend && npm run dev
```

### 3. Test True Agent-Native Execution
```bash
# Create invoice (REAL API call, not simulation)
curl -X POST http://localhost:8001/api/v1/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "create invoice for Acme Corp for 50000", "org_id": "test_org"}'

# Send WhatsApp reminders (Twilio)
curl -X POST http://localhost:8001/api/v1/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "send reminders to overdue clients", "org_id": "test_org"}'

# TReDS working capital
curl -X POST http://localhost:8001/api/v1/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "discount invoice to get cash now", "org_id": "test_org"}'
```

## Repository Cleanup (Done)

### Deleted Vanity Features (14,909 lines removed)
- `enhanced_finance_agent.py` (867 lines) - ported real API calls to FinanceExecutor
- `enhanced_market_agent.py` (417 lines) - nice-to-have, not critical
- `function_calling_agent.py` (727 lines) - vanity feature
- `intelligent_orchestrator.py` (400 lines) - keyword matching replaced
- `moneyops_agent.py` (5676 lines) - monolithic, replaced by modular executors
- 7 unused frontend pages (AlertAgentPage, GrowthAgentPage, etc.)

### Added True Agent-Native Features
- `base_executor.py` (754 lines) - 4 executors with REAL API calls
- `pinecone_manager.py` - vector memory for GST rules + client patterns
- `twilio_manager.py` - instant WhatsApp/SMS (no Meta approval)
- `grpc_client.py` - ready for gRPC service-to-service
- `protos/moneyops.proto` - complete service definitions

## WhatsApp Business API Alternative

Since Meta requires "established business" for official API:

### ✅ Solution: Twilio WhatsApp (Instant)
1. Sign up at [twilio.com](https://www.twilio.com) (free trial)
2. Get `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN`
3. Request WhatsApp Sender (24-48 hours, faster than Meta)
4. Set in `.env`:
   ```
   TWILIO_ACCOUNT_SID=ACxxxxxxxx
   TWILIO_AUTH_TOKEN=your_token
   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
   ```

### Fallback: SMS (100% Instant)
```python
# Works immediately, $0.01/message, 98% open rate
TWILIO_SMS_FROM=+1234567890
```

## gRPC Migration (Next Step)

Replace HTTP/JSON in `backend_adapter.py` with gRPC:

```bash
# Generate Python stubs from proto
pip install grpcio-tools
python -m grpc_tools.protoc -I protos --python_out=. --grpc_python_out=. protos/moneyops.proto
```

Then update `grpc_client.py` to use generated stubs for 10x faster service communication.

## TReDS Integration (Ready to Deploy)

```python
# In TReDSExecutor, connect to RXIL/M1xchange APIs
# Discount invoice at 8-12% fee → Get cash in 24 hours
# Solves: "Waiting 90 days for payment" problem
```

Register at:
- [RXIL](https://www.rxil.in)
- [M1xchange](https://www.m1xchange.com)
- [InvoiceMart](https://www.invoicemart.com)

## Rate Limiting & Scale (10k Users)

```python
# Redis-based token bucket (already in .env)
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# Middleware ready for:
# - 100 requests/minute per org
# - Connection pooling for DB/gRPC
# - Circuit breakers for cascading failure protection
```

## Commit History (Cleaned Up)

```
99929af feat: implement true agent-native architecture with real API execution
9cd55f2 feat: enhance market intelligence and compliance agents
40d008d Updating AI response loader
176eac9 Hide internal UI details and show chat loader
6bfedec Fix invoice backend tests
488fbe3 feat: expand agent-driven voice and workspace actions
```

## Contributing

1. **True Agents Only**: No simulations, no "LLM says X" - agents must EXECUTE
2. **Real APIs**: Always use `backend_adapter.py` for backend calls
3. **No Vanity Features**: If it doesn't solve 90-day payment delays, don't build it
4. **WhatsApp > Market Analysis**: Collections engine > competitor intelligence

## License

MIT - Built for Indian SMBs who need cash flow, not dashboards.

---

**Built by DarshK25 & Team** | **Research-backed**: LedgerCat, Acctos AI, ProcIndex patterns
