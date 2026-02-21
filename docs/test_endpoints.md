# MoneyOps API Endpoints Reference

## AI Gateway (FastAPI)
Base URL: `http://localhost:8001`
Prefix: `/api/v1`

### Health
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Service health status |
| `GET` | `/api/v1/health/ready` | Readiness probe |
| `GET` | `/api/v1/health/live` | Liveness probe |

### Voice Pipeline
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/voice/process` | End-to-end intent -> entities -> agent routing for voice |

### Diagnostics / Test
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/test/simple-prompt` | Direct LLM completion test |
| `GET` | `/api/v1/test/health-llm` | LLM connectivity health check |
| `POST` | `/api/v1/test/intent-classification` | Intent classifier test |
| `POST` | `/api/v1/test/entity-extraction` | Entity extractor test |
| `POST` | `/api/v1/test/agents/execute` | Agent router execution test |

---

## Backend Core (Spring Boot)
Base URL: `http://localhost:8000`
Prefix: `/api`

### Authentication
| Method | Endpoint |
| :--- | :--- |
| `POST` | `/api/auth/register` |
| `POST` | `/api/auth/login` |

### Core Domain
| Method | Endpoint |
| :--- | :--- |
| `GET` | `/api/users` |
| `GET` | `/api/clients` |
| `POST` | `/api/clients` |
| `GET` | `/api/invoices` |
| `POST` | `/api/invoices` |
| `GET` | `/api/transactions` |
| `POST` | `/api/transactions` |
| `GET` | `/api/transactions/summary` |

### Required Headers (secured endpoints)
- `Authorization: Bearer <JWT_TOKEN>`
- `X-Org-Id: <ORG_UUID>`
- `X-User-Id: <USER_UUID>`

---

## Quick Checks (PowerShell)

```powershell
# AI Gateway health
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/health"

# LLM health
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/test/health-llm"

# Intent classification
$intentBody = @{
  user_input = "Create invoice for Acme Corp for 50000 rupees"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/test/intent-classification" -Method POST -ContentType "application/json" -Body $intentBody

# Voice processing
$voiceBody = @{
  text = "What is my current balance?"
  user_id = "user-test"
  org_id = "org-test"
  session_id = "session-test"
  context = @{}
  conversation_history = @()
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/voice/process" -Method POST -ContentType "application/json" -Body $voiceBody
```
