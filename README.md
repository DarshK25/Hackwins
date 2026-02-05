# 💸 MoneyOps: Intelligent Financial Orchestration

> **Status**: Phase 4 Complete (Agent Base & Finance Agent) 🚀
> **Architecture**: Distributed AI Microservices

MoneyOps is a next-generation financial platform that orchestrates **AI Agents** to handle invoicing, payments, and business intelligence via **Voice** and **Chat** interfaces.

---

## 📚 Documentation

- **[Architecture Deep Dive](docs/architecture.md)**: Diagrams and detailed breakdown of the AI Gateway, Agents, and Backend.
- **[Troubleshooting & Tradeoffs](docs/troubleshooting_and_tradeoffs.md)**: Solutions to common issues and architectural decisions.
- **[Testing Results](docs/test_results.md)**: Verification logs.
- **[Endpoints](docs/test_endpoints.md)**: API reference.

---

## 🏗️ System Components

| Service | Tech Stack | Status | Description |
| :--- | :--- | :--- | :--- |
| **Backend Core** | Java 17, Spring Boot | ✅ Stable | REST API, Security, Database (PostgreSQL) |
| **AI Gateway** | Python, FastAPI | ✅ Phase 4 | Agent Orchestration, Tool Registry, LLM Integration |
| **Voice Service** | Python, LiveKit | 🚧 Planned | Real-time Voice I/O |
| **Frontend** | React/Next.js | 🚧 Planned | Web Dashboard |

---

## 🚀 Quick Start

### 1. Prerequisites
- Java 17+ & Maven
- Python 3.9+
- PostgreSQL
- Git

### 2. Setup

**Backend:**
```bash
cd MoneyOps/backend
./mvnw clean install
./mvnw spring-boot:run
```

**AI Gateway:**
```bash
cd MoneyOps/ai-gateway
python -m venv venv
./venv/Scripts/Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### 3. Verification
We have a comprehensive PowerShell script that seeds data and verifies the full pipeline (Auth -> Backend -> Gateway -> Agent).

```powershell
./scripts/seed_and_verify.ps1
```

---

## 🧪 AI Agent Capabilities (Phase 4)

The **Finance Agent** is currently active and supports:
- `BALANCE_CHECK`: "What is my balance?"
- `INVOICE_CREATE`: "Create an invoice for Acme Corp"
- `PAYMENT_RECORD`: "Record a payment of $500"

Example Test:
```bash
curl -X POST http://localhost:8001/api/v1/test/agents/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_JWT>" \
  -d '{"intent":"BALANCE_CHECK","entities":{}}'
```
