# MoneyOps API Endpoints Reference

## 🤖 AI Gateway (FastAPI)
**Base URL:** `http://localhost:8001`
**Prefix:** `/api/v1`

### Health & Diagnostics
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Service health status |
| `GET` | `/api/v1/health/ready` | Readiness probe (Kubernetes) |
| `GET` | `/api/v1/health/live` | Liveness probe (Kubernetes) |

### Testing & Verification
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/test/simple-prompt` | Test LLM connectivity (Simple completion) |
| `POST` | `/api/v1/test/intent-classification` | Test Intent Classifier (Groq) |
| `POST` | `/api/v1/test/entity-extraction` | Test Entity Extractor |
| `GET` | `/api/v1/test/health-llm` | Check LLM provider availability |
| `POST` | `/api/v1/test/agents/execute` | **Main Agent Test Endpoint** (Routes to agents) |

---

## ☕ Backend Core (Spring Boot)
**Base URL:** `http://localhost:8000`
**Prefix:** `/api`

### Authentication
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Register new user. Body: `{name, email, password, orgName}` |
| `POST` | `/api/auth/login` | Login. Returns JWT Token. |

### Organizations
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/org` | Create organization (Requires Auth) |
| `GET` | `/api/org/my` | Get current user's organization |
| `GET` | `/api/org/{id}` | Get organization by ID |
| `PUT` | `/api/org/{id}` | Update organization |
| `DELETE` | `/api/org/{id}` | Delete organization |

### Users
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/users` | List all users in org |
| `GET` | `/api/users/{id}` | Get user details |
| `POST` | `/api/users` | Create user (Admin only) |
| `PUT` | `/api/users/{id}` | Update user |
| `POST` | `/api/users/invite` | Invite user to org |
| `POST` | `/api/users/accept-invite` | Accept invitation |

### Clients (CRM)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/clients` | List clients |
| `GET` | `/api/clients/{id}` | Get client details |
| `POST` | `/api/clients` | Create client |
| `PUT` | `/api/clients/{id}` | Update client |
| `DELETE` | `/api/clients/{id}` | Delete client |
| `GET` | `/api/clients/search?q=...` | Search clients by name |

### Invoices
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/invoices` | Create invoice |
| `GET` | `/api/invoices` | List invoices |
| `GET` | `/api/invoices/{id}` | Get invoice details |
| `PUT` | `/api/invoices/{id}` | Update invoice |
| `PATCH` | `/api/invoices/{id}/send` | Mark invoice as sent |
| `PATCH` | `/api/invoices/{id}/mark-paid` | Mark invoice as paid |
| `GET` | `/api/invoices/overdue` | Get overdue invoices |

### Transactions
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/transactions` | Record income/expense |
| `PUT` | `/api/transactions/{id}` | Update transaction |
| `GET` | `/api/transactions` | List transactions |
| `GET` | `/api/transactions/{id}` | Get transaction details |
| `GET` | `/api/transactions/client/{clientId}` | Get transactions for specific client |
| `GET` | `/api/transactions/range` | Param: `startDate`, `endDate` |
| `GET` | `/api/transactions/summary` | Financial Summary: `{totalIncome, totalExpense, netProfit}` |

### Important Headers
- **Authorization**: `Bearer <JWT_TOKEN>` (Required for most Backend endpoints, passed via Gateway)
- **X-Org-Id**: `<ORG_UUID>` (Often required for multi-tenancy context)
- **X-User-Id**: `<USER_UUID>` (Context for auditing)

---

# 🧪 Detailed API Testing Guide (PowerShell)

## Test 1: Health Check ✅
```powershell
curl -X GET http://localhost:8001/api/v1/health
```
**Expected:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development",
  "checks": {"api": "healthy"}
}
```

## Test 2: Intent Classification
**Using Invoke-WebRequest (PowerShell native):**
```powershell
$body = @{
    user_input = "Create invoice for Acme Corp for 50,000 rupees"
    industry = "IT & Software"
    has_gst = $true
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8001/api/v1/test/intent-classification" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body | Select-Object -Expand Content | ConvertFrom-Json
```

**Expected:**
```json
{
  "success": true,
  "classification": {
    "intent": "INVOICE_CREATE",
    "confidence": 0.9,
    "primary_agent": "FINANCE_AGENT"
  }
}
```

## Test 3: Entity Extraction
```powershell
$body = @{
    user_input = "Create invoice for Acme Corp for 50,000 rupees due next month"
    intent = "INVOICE_CREATE"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8001/api/v1/test/entity-extraction" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body | Select-Object -Expand Content | ConvertFrom-Json
```

**Expected:**
```json
{
  "success": true,
  "extracted_entities": {
    "entities": [
      {"type": "AMOUNT", "value": "50000", "confidence": 0.95},
      {"type": "CLIENT_NAME", "value": "Acme Corp", "confidence": 0.9}
    ]
  }
}
```

## Test 4: Strategic Intent (Problem Diagnosis)
```powershell
$body = @{
    user_input = "Why is my revenue down 15% this quarter?"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8001/api/v1/test/intent-classification" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body | Select-Object -Expand Content | ConvertFrom-Json
```

**Expected:**
```json
{
  "success": true,
  "classification": {
    "intent": "PROBLEM_DIAGNOSIS",
    "category": "STRATEGIC"
  }
}
```

## Test 5: Simple Prompt Test
```powershell
$body = @{
    prompt = "What are the key metrics for a SaaS business?"
    temperature = 0.3
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8001/api/v1/test/simple-prompt" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body | Select-Object -Expand Content | ConvertFrom-Json
```

---

## 🔧 Troubleshooting Tools

### If you get "Not Found" (404):
1. Check server is running: `Get-Process | Where-Object {$_.ProcessName -like "*uvicorn*"}`
2. Restart server from `/MoneyOps/ai-gateway` directory:
   ```powershell
   uvicorn app.main:app --reload --port 8001
   ```

### If you get "Connection refused":
- Server not started. Run: `uvicorn app.main:app --reload --port 8001`
- Check port 8001 is not in use: `Get-NetTCPConnection -LocalPort 8001`
