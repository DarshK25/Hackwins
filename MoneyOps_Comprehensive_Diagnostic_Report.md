# MoneyOps Comprehensive Diagnostic Report

Date: 2026-04-22  
Audience: AI system handoff / maintenance agent  
Scope: Current repository state in `C:\Projects\MoneyOps`  
Primary artifact goal: one-file operational and architectural handoff

---

## 1. Executive Summary

MoneyOps is a multi-service financial operations platform built around:

- a Java Spring Boot backend for core business logic and MongoDB persistence
- a Spring Cloud API gateway for routing, rate limiting, and JWT enforcement
- a Python FastAPI AI gateway for intent classification, agent orchestration, and backend tool calls
- a Python LiveKit voice service for STT/TTS-driven voice interactions
- a React + Vite frontend for dashboard, CRM, invoicing, and voice UX

The repository is not a simple CRUD app. It is a partially integrated orchestration platform with strong tenant-isolation concepts, agent-driven workflows, and a growing set of orchestration artifacts for voice and strategic assistance.

### 1.1 Current Overall Status

As observed during this pass on 2026-04-22:

| Component | Expected Port | Evidence | Current Status |
| --- | --- | --- | --- |
| Backend Core | `8000` | `GET http://127.0.0.1:8000/actuator/health` returned `401 Unauthorized`; approved out-of-sandbox `mvn.cmd -o -DskipTests compile` succeeded | Running, secured; build verified |
| AI Gateway | `8001` | `GET http://127.0.0.1:8001/api/v1/health` returned healthy JSON | Running |
| Voice Service | `8003` | Local probe could not connect | Not running at time of check |
| API Gateway | `8080` by config | Local probe could not connect; approved out-of-sandbox `mvn.cmd -o -DskipTests compile` succeeded | Not running at time of check; build verified |
| Frontend dev server | `3000` by Vite config | Local probe could not connect; approved out-of-sandbox `npm.cmd run build` succeeded | Not running at time of check; production build verified |
| Redis | `6379` | Configured in compose and service configs; not directly health-checked in this pass | Configured, runtime unverified in this pass |
| MongoDB Atlas | cloud | Root `.env` contains Atlas URI, backend logs show Atlas connectivity attempts and successful monitor connections | Configured and previously connected |

### 1.2 Corrective Note on Earlier Draft Assumptions

Several assumptions from the earlier planning draft are not accurate for the current workspace:

- `GROQ_API_KEY` is not missing in the shared `.env`; it is present.
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` are not missing in the shared `.env`; they are present.
- The AI Gateway is not currently blocked by missing Groq configuration; it responded healthy at `http://127.0.0.1:8001/api/v1/health`.
- The current implemented MongoDB model is not limited to the 9 collections described in the older schema document. The backend code currently defines 12 MongoDB document collections.
- The current frontend dev port is `3000` in `MoneyOps/Frontend/vite.config.js`, not Vite's default `5173`.
- The current API gateway port in `MoneyOps/api-gateway/src/main/resources/application.yml` is `8080`, not `8002`.

### 1.3 What This Means

The project is best described as:

`Partially operational, with backend + AI gateway live, and other services/configurations present but not all currently running in the checked environment.`

The most important handoff insight is that the codebase contains both:

- active production-facing paths that work now
- forward-looking design documents that describe schema and architecture not fully materialized in code yet

Any maintenance AI should treat documentation as informative, not authoritative, unless it matches the code.

---

## 2. Methodology And Evidence Base

This report was assembled from:

- top-level docs: `README.md`, `docs/architecture.md`, `docs/MoneyOps_Database_Schema.md`, `docs/troubleshooting_and_tradeoffs.md`, `docs/test_results.md`, `docs/test_endpoints.md`
- backend configs and code: `MoneyOps/backend/pom.xml`, `MoneyOps/backend/src/main/resources/application.yml`, entity classes, controllers, services
- API gateway configs: `MoneyOps/api-gateway/pom.xml`, `MoneyOps/api-gateway/src/main/resources/application.yml`
- AI gateway configs and runtime code: `MoneyOps/ai-gateway/pyproject.toml`, `MoneyOps/ai-gateway/app/config.py`, `MoneyOps/ai-gateway/app/main.py`, voice/agent/router/session files
- voice service configs and entrypoint: `MoneyOps/voice-service/app/config.py`, `MoneyOps/voice-service/app/agent/entrypoint.py`, `MoneyOps/voice-service/EVENT_HANDLER_FIX.md`, `MoneyOps/voice-service/TEST_GUIDE.md`
- frontend configs: `MoneyOps/Frontend/package.json`, `MoneyOps/Frontend/vite.config.js`
- operational assets: `MoneyOps/docker-compose.yml`, backend logs, local process and health probes

### 2.1 Verification Caveats

Initial sandboxed attempts limited some verification:

- Maven commands failed before compile because Maven tried to use the sandboxed user repository path under `C:\Users\CodexSandboxOffline\.m2\repository`.
- Frontend `npm.cmd run build` initially failed at `esbuild` process spawn time with `EPERM`.
- After approval to rerun those commands outside the sandbox, verification succeeded:
  - backend `mvn.cmd -o -DskipTests compile`: `BUILD SUCCESS` in `7.824s`
  - API gateway `mvn.cmd -o -DskipTests compile`: `BUILD SUCCESS` in `4.867s`
  - frontend `npm.cmd run build`: success in `8.98s`, with a chunk-size warning for the main JS bundle
- Therefore, compile/build status below distinguishes between:
  - `observed live`
  - `build verified`
  - `configured but not running in this environment`

---

## 3. Repository Structure

### 3.1 Top-Level Layout

| Path | Purpose |
| --- | --- |
| `docs/` | Architecture, schema, troubleshooting, test notes |
| `MoneyOps/backend/` | Java Spring Boot core backend |
| `MoneyOps/api-gateway/` | Spring Cloud Gateway edge service |
| `MoneyOps/ai-gateway/` | Python FastAPI AI orchestration service |
| `MoneyOps/voice-service/` | Python LiveKit voice agent |
| `MoneyOps/Frontend/` | React frontend |
| `scripts/` | Utilities and seed/test scripts |
| `tests/` | Miscellaneous project-level tests |

### 3.2 Architectural Theme

The architecture follows a "controller/edge -> orchestration -> domain backend -> persistence" pattern:

1. Frontend talks to backend and AI/voice routes through proxied `/api` and `/api/v1`.
2. API gateway is intended to front backend, AI gateway, and voice service.
3. AI gateway classifies intent, extracts entities, and routes to specialized agents.
4. Finance and other agents use an HTTP adapter to call the backend.
5. Backend persists business data in MongoDB Atlas and optionally interacts with Redis and Kafka.
6. Voice service captures speech, delegates all reasoning to AI gateway, and only owns audio I/O.

---

## 4. Service Inventory And Architecture

## 4.1 Backend Core

Path: `MoneyOps/backend/`  
Language: Java 17  
Framework: Spring Boot `3.2.1`  
Artifact: `moneyops-backend`

### Responsibilities

- authentication and onboarding
- organizations and team security code
- clients
- invoices and invoice items
- transactions and summary metrics
- audit logging
- documents
- compliance surfaces
- finance intelligence endpoints
- orchestrator persistence endpoints

### Core dependencies

- `spring-boot-starter-web`
- `spring-boot-starter-data-mongodb`
- `spring-boot-starter-security`
- `spring-boot-starter-oauth2-client`
- `spring-kafka`
- `jjwt-*`
- `springdoc-openapi`
- `openpdf`
- `resend-java`

### Runtime observations

- backend health endpoint is protected enough to return `401` to unauthenticated probe, which is a good sign that the service is up and the security layer is active
- approved out-of-sandbox `mvn.cmd -o -DskipTests compile` completed successfully, compiling `164` source files in `7.824s`
- backend logs show MongoDB Atlas monitor connectivity and authenticated app traffic on 2026-02-24

### Risks

- Spring Boot `3.2.1` is old and should be reviewed for upgrade
- some historical docs still mention H2 lock issues even though the current backend is MongoDB-centric
- some classes show duplicate imports and signs of merge churn, so code hygiene deserves attention

## 4.2 API Gateway

Path: `MoneyOps/api-gateway/`  
Language: Java 17  
Framework: Spring Boot `3.2.0` + Spring Cloud Gateway `2023.0.0`

### Responsibilities

- request routing
- JWT validation
- rate limiting via Redis
- tenant-aware endpoint shaping
- actuator health

### Important config facts

- configured server port is `${PORT:8080}`
- routes exist for backend core, AI gateway, and voice service
- rate limiting is configured per route class

### Runtime observations

- no process responded on `http://127.0.0.1:8080/actuator/health` during this pass
- approved out-of-sandbox `mvn.cmd -o -DskipTests compile` completed successfully, compiling `15` source files in `4.867s`
- service is configured, but not confirmed live at time of report

## 4.3 AI Gateway

Path: `MoneyOps/ai-gateway/`  
Language: Python 3.11  
Framework: FastAPI `0.109.x`  
Package manager: Poetry

### Responsibilities

- health and test routes
- voice request processing
- intent classification
- entity extraction
- agent routing
- backend adapter mediation
- session tracking
- compliance and market intelligence routes

### Key dependencies

- `fastapi`
- `uvicorn`
- `groq`
- `anthropic`
- `redis`
- `httpx`
- `pydantic-settings`
- `structlog`

### Important config facts

- `GROQ_API_KEY` is required by settings
- shared root `.env` is loaded explicitly before settings resolution
- Redis connection is attempted at startup but gateway tolerates Redis failure and logs a warning
- LiveKit credentials are optional for `/voice/token`, but required to generate tokens

### Runtime observations

- `GET /api/v1/health` returned healthy JSON with version `1.0.0` and `environment` set to `development`

- AI Gateway is live and reachable in development mode

## 4.4 Voice Service

Path: `MoneyOps/voice-service/`  
Language: Python  
Primary libraries: `livekit-agents`, `silero`, `groq`, optional AssemblyAI and Cartesia plugins

### Responsibilities

- connect to LiveKit rooms
- run VAD
- transcribe user speech
- send text to AI gateway
- play response text via TTS
- publish UI events and gateway results back into the room

### Architectural note

The service intentionally does not own business reasoning. The entrypoint comments are explicit: the AI Gateway is the brain; voice-service handles audio I/O and event choreography.

### Runtime observations

- no process responded on port `8003` during this pass

### Known improvement history

- event handler fix changed LiveKit `.on()` callbacks from async to sync
- STT guidance docs indicate AssemblyAI support was enabled and tested

## 4.5 Frontend

Path: `MoneyOps/Frontend/`  
Language: JavaScript / React 18  
Build tool: Vite `7.3.1`

### Responsibilities

- invoicing UI
- client management
- analytics and settings
- voice agent UI
- Clerk-driven auth UX

### Important config facts

- dev server port is `3000`
- `/api` proxies to backend target `http://127.0.0.1:8002` by default
- `/api/v1` proxies to AI gateway target `http://127.0.0.1:8001`
- compatibility rewrite exists for an older compliance route

### Runtime observations

- no frontend server was reachable on `http://127.0.0.1:3000` at time of probe
- approved out-of-sandbox `npm.cmd run build` succeeded in `8.98s`
- Vite emitted a bundle-size warning because `dist/assets/index-DA2cCuWi.js` was about `1.89 MB` after build; the app is buildable, but chunking should be improved

## 4.6 Supporting Infrastructure

### Redis

- port `6379` in compose
- used by API gateway rate limiting
- used by AI gateway cache/session integrations

### MongoDB Atlas

- backend `application.yml` reads `MONGODB_URI`
- root `.env` contains an Atlas URI
- backend logs show successful monitor connections to Atlas nodes

### Kafka

- backend contains Kafka listener stubs in `events/consumer/NotificationConsumer.java`
- runtime is feature-flagged / env-driven
- not verified active during this pass

---

## 5. Technology Matrix

| Layer | Stack | Versions / Notes |
| --- | --- | --- |
| Frontend | React, Vite, Clerk, LiveKit client, Tailwind ecosystem | React `18.3.1`, Vite `7.3.1` |
| Backend Core | Spring Boot, Spring Data MongoDB, Spring Security, OpenAPI | Spring Boot `3.2.1`, Java `17` |
| API Gateway | Spring Cloud Gateway, Redis Reactive, JWT | Spring Boot `3.2.0`, Spring Cloud `2023.0.0` |
| AI Gateway | FastAPI, Uvicorn, Groq, Anthropic, Redis | Python `^3.11` |
| Voice Service | LiveKit Agents, Silero VAD, Groq, AssemblyAI, Cartesia | LiveKit plugin-driven |
| Data | MongoDB Atlas, Redis | MongoDB UUID representation explicitly set to `STANDARD` |
| Messaging | Kafka | Optional / env-controlled |

---

## 6. Database Model: Current Implemented Schema

This section documents the schema implemented in the backend code, not just the intended schema in the older docs.

### 6.1 Implemented MongoDB Collections In Code

Current `@Document` collections found under backend source:

1. `users`
2. `business_organizations`
3. `clients`
4. `invoices`
5. `transactions`
6. `audit_logs`
7. `documents`
8. `regulatory_profiles`
9. `invites`
10. `team_invites`
11. `voice_conversations`
12. `orchestrator_activities`

### 6.2 Important Drift From Older Schema Document

`docs/MoneyOps_Database_Schema.md` describes a 9-collection core with `voice_sessions` and `idempotency_keys` as new v2 collections. In the current backend code:

- `voice_sessions` is not implemented as a backend `@Document`
- `idempotency_keys` is not implemented as a separate backend `@Document`
- session state currently lives in AI gateway in-memory `SessionManager`, with comments saying Redis or DB should be used for true atomicity
- idempotency is implemented as fields on client/invoice/transaction documents rather than a dedicated collection
- new orchestrator collections exist in code but are not covered by the older schema doc

### 6.3 Global Schema Rules Observed In Code

- IDs are `String` UUIDs across entities.
- MongoDB UUID representation is set to `STANDARD` in backend config.
- Most business collections include `orgId` for tenant isolation.
- Most business collections use soft delete via `deletedAt`.
- Many entities use Spring Data auditing fields (`@CreatedDate`, `@LastModifiedDate`, `@CreatedBy`, `@LastModifiedBy`).
- Invoice, client, and transaction entities each include an `idempotencyKey` field with a unique partial index.

### 6.4 Relationship Overview

```text
business_organizations
  -> users
  -> clients
  -> invoices
  -> transactions
  -> documents
  -> regulatory_profiles
  -> invites
  -> team_invites
  -> voice_conversations
  -> orchestrator_activities

clients
  -> invoices.clientId
  -> transactions.clientId

invoices
  -> transactions.invoiceId
  -> embedded invoice.items[]

audit_logs
  -> polymorphic entityType/entityId references

documents
  -> polymorphic linkedEntityType/linkedEntityId references
```

---

## 7. Collection Reference

The tables below reflect current Java entity definitions.

## 7.1 `users`

Source: `MoneyOps/backend/src/main/java/com/moneyops/users/entity/User.java`

| Field | Type | Constraints / defaults | Notes |
| --- | --- | --- | --- |
| `id` | `String` | generated UUID | primary key |
| `orgId` | `String` | indexed | tenant pointer |
| `name` | `String` | none | display name |
| `email` | `String` | unique index | global uniqueness in current code |
| `phone` | `String` | none | optional |
| `role` | `enum User.Role` | default `STAFF` | `OWNER`, `ADMIN`, `MANAGER`, `STAFF`, `VIEWER` |
| `status` | `enum User.Status` | default `ACTIVE` | `ACTIVE`, `INVITED`, `DISABLED` |
| `clerkId` | `String` | unique index | auth-system identity |
| `onboardingComplete` | `boolean` | default `false` | onboarding state |
| `lastLoginAt` | `LocalDateTime` | optional | login audit |
| `createdAt` | `LocalDateTime` | audited | creation timestamp |
| `updatedAt` | `LocalDateTime` | audited | update timestamp |
| `createdBy` | `String` | audited | creator user id |
| `updatedBy` | `String` | audited | updater user id |
| `deletedAt` | `LocalDateTime` | nullable | soft delete |

Indexes observed:

- `orgId`
- unique `email`
- unique `clerkId`

Sample document:

```json
{
  "id": "uuid-string",
  "orgId": "org-uuid",
  "name": "Tanush Jain",
  "email": "owner@example.com",
  "phone": "+91-9999999999",
  "role": "OWNER",
  "status": "ACTIVE",
  "clerkId": "user_abc123",
  "onboardingComplete": true,
  "lastLoginAt": "2026-04-22T12:00:00",
  "createdAt": "2026-04-01T10:00:00",
  "updatedAt": "2026-04-22T12:00:00",
  "createdBy": "system",
  "updatedBy": "user_abc123",
  "deletedAt": null
}
```

## 7.2 `business_organizations`

Source: `MoneyOps/backend/src/main/java/com/moneyops/organizations/entity/BusinessOrganization.java`

| Field | Type | Constraints / defaults | Notes |
| --- | --- | --- | --- |
| `id` | `String` | generated UUID | primary key |
| `teamActionCodeHash` | `String` | nullable | bcrypt hash for sensitive actions |
| `legalName` | `String` | none | legal business name |
| `tradingName` | `String` | none | public-facing name |
| `businessType` | `String` | none | freeform string, not enum |
| `industry` | `String` | none | freeform |
| `registrationDate` | `LocalDate` | optional | registration date |
| `annualTurnover` | `String` | none | stored as string |
| `primaryEmail` | `String` | none | business contact |
| `primaryPhone` | `String` | none | business contact |
| `website` | `String` | none | optional |
| `employeeCount` | `Integer` | optional | team size |
| `registeredAddress` | `String` | none | flat string field |
| `pincode` | `String` | none | postal code |
| `panNumber` | `String` | none | compliance data |
| `stateOfRegistration` | `String` | none | compliance data |
| `gstRegistered` | `Boolean` | optional | compliance data |
| `gstin` | `String` | none | compliance data |
| `gstFilingFrequency` | `String` | none | compliance data |
| `tanNumber` | `String` | none | compliance data |
| `cin` | `String` | none | compliance data |
| `llpin` | `String` | none | compliance data |
| `msmeNumber` | `String` | none | compliance data |
| `iecCode` | `String` | none | compliance data |
| `professionalTaxReg` | `String` | none | compliance data |
| `primaryActivity` | `String` | none | business context |
| `targetMarket` | `String` | none | business context |
| `keyProducts` | `List<String>` | optional | business context |
| `currentChallenges` | `List<String>` | optional | business context |
| `accountingMethod` | `String` | none | accounting mode |
| `fyStartMonth` | `Integer` | optional | fiscal year start |
| `preferredLanguage` | `String` | none | UI/business locale |
| `createdAt` | `LocalDateTime` | audited | timestamp |
| `updatedAt` | `LocalDateTime` | audited | timestamp |
| `createdBy` | `String` | audited | owning user |
| `updatedBy` | `String` | audited | updater |
| `deletedAt` | `LocalDateTime` | nullable | soft delete |

Sample document:

```json
{
  "id": "org-uuid",
  "teamActionCodeHash": "$2a$...",
  "legalName": "MoneyOps Private Limited",
  "tradingName": "MoneyOps",
  "businessType": "SERVICES",
  "industry": "Fintech",
  "primaryEmail": "ops@example.com",
  "primaryPhone": "+91-9999999999",
  "website": "https://moneyops.ai",
  "employeeCount": 12,
  "registeredAddress": "Bengaluru, Karnataka",
  "pincode": "560001",
  "gstRegistered": true,
  "gstin": "29ABCDE1234F1Z5",
  "primaryActivity": "Financial operations automation",
  "targetMarket": "SMBs",
  "keyProducts": ["AI finance assistant"],
  "currentChallenges": ["cash flow visibility"],
  "accountingMethod": "accrual",
  "fyStartMonth": 4,
  "preferredLanguage": "en",
  "createdAt": "2026-04-01T10:00:00",
  "updatedAt": "2026-04-22T12:00:00",
  "createdBy": "user-uuid",
  "updatedBy": "user-uuid",
  "deletedAt": null
}
```

## 7.3 `clients`

Source: `MoneyOps/backend/src/main/java/com/moneyops/clients/entity/Client.java`

| Field | Type | Constraints / defaults | Notes |
| --- | --- | --- | --- |
| `id` | `String` | generated UUID | primary key |
| `orgId` | `String` | indexed | tenant isolation |
| `name` | `String` | required by validator/service flows | client display name |
| `gstin` | `String` | optional | compliance identifier |
| `email` | `String` | service enforces uniqueness globally when creating client | contact email |
| `phoneNumber` | `String` | optional | contact number |
| `billingAddress` | `Client.Address` | optional | line1, line2, city, state, country, pincode |
| `shippingAddress` | `Client.Address` | optional | same shape as billing |
| `paymentTerms` | `Integer` | optional | invoice terms in days |
| `currency` | `String` | default `INR` | preferred currency |
| `company` | `String` | optional | organization/company name |
| `notes` | `String` | optional | internal notes |
| `status` | `enum Client.Status` | default `ACTIVE` | `ACTIVE`, `INACTIVE`, `SUSPENDED` |
| `createdAt` | `LocalDateTime` | audited | timestamp |
| `updatedAt` | `LocalDateTime` | audited | timestamp |
| `createdBy` | `String` | audited | creator id |
| `createdByEmail` | `String` | optional | sensitive-action metadata |
| `createdByRole` | `String` | optional | sensitive-action metadata |
| `source` | `String` | optional | `MANUAL`, `AI`, `VOICE` |
| `updatedBy` | `String` | audited | updater id |
| `deletedAt` | `LocalDateTime` | nullable | soft delete |
| `idempotencyKey` | `String` | unique partial index when present | duplicate prevention |

Indexes observed:

- `orgId`
- unique partial `idempotencyKey`

Sample document:

```json
{
  "id": "client-uuid",
  "orgId": "org-uuid",
  "name": "Acme Corp",
  "gstin": "29ABCDE1234F1Z5",
  "email": "client@example.com",
  "phoneNumber": "+91-9876543210",
  "billingAddress": {"line1": "123 MG Road", "city": "Bengaluru", "state": "Karnataka", "country": "India", "pincode": "560001"},
  "shippingAddress": null,
  "paymentTerms": 15,
  "currency": "INR",
  "company": "Acme Corp",
  "notes": "Priority client",
  "status": "ACTIVE",
  "createdBy": "user-uuid",
  "createdByEmail": "owner@example.com",
  "createdByRole": "OWNER",
  "source": "MANUAL",
  "deletedAt": null,
  "idempotencyKey": null
}
```

## 7.4 `invoices`

Source: `MoneyOps/backend/src/main/java/com/moneyops/invoices/entity/Invoice.java`

| Field | Type | Constraints / defaults | Notes |
| --- | --- | --- | --- |
| `id` | `String` | generated UUID | primary key |
| `orgId` | `String` | indexed | tenant isolation |
| `invoiceNumber` | `String` | indexed | generated automatically if missing |
| `clientId` | `String` | indexed | references `clients.id` |
| `clientName` | `String` | optional snapshot | denormalized client snapshot |
| `clientEmail` | `String` | optional snapshot | used for send/resend |
| `clientCompany` | `String` | optional snapshot | denormalized |
| `clientPhone` | `String` | optional snapshot | denormalized |
| `issueDate` | `LocalDate` | required for normal flows | invoice issue date |
| `dueDate` | `LocalDate` | required in create flows | payment due date |
| `status` | `enum InvoiceStatus` | default `DRAFT` | `DRAFT`, `SENT`, `PAID`, `OVERDUE` |
| `subtotal` | `BigDecimal` | recalculated server-side | line subtotal |
| `gstTotal` | `BigDecimal` | recalculated server-side | GST total |
| `totalAmount` | `BigDecimal` | recalculated server-side | invoice total |
| `amountPaid` | `BigDecimal` | default `0` | denormalized payment total |
| `balanceDue` | `BigDecimal` | computed | outstanding amount |
| `currency` | `String` | default `INR` | invoice currency |
| `paymentDate` | `LocalDate` | optional | set when paid |
| `notes` | `String` | optional | internal or generated notes |
| `termsAndConditions` | `String` | optional | invoice footer content |
| `items` | `List<InvoiceItem>` | embedded | line items |
| `voiceContext` | `Invoice.VoiceContext` | optional | `sessionId`, `createdViaVoice`, `transcript` |
| `createdAt` | `LocalDateTime` | audited | timestamp |
| `updatedAt` | `LocalDateTime` | audited | timestamp |
| `createdBy` | `String` | audited | creator id |
| `createdByEmail` | `String` | optional | sensitive-action metadata |
| `createdByRole` | `String` | optional | sensitive-action metadata |
| `source` | `String` | optional | `MANUAL`, `AI`, `VOICE` |
| `updatedBy` | `String` | audited | updater id |
| `deletedAt` | `LocalDateTime` | nullable | soft delete |
| `idempotencyKey` | `String` | unique partial index when present | duplicate prevention |

Embedded `InvoiceItem` shape:

| Field | Type | Notes |
| --- | --- | --- |
| `id` | `String` | generated UUID |
| `type` | `enum` | `PRODUCT` or `SERVICE` |
| `description` | `String` | required by validator |
| `quantity` | `Integer` | optional for services |
| `rate` | `BigDecimal` | line rate |
| `gstPercent` | `BigDecimal` | percent |
| `lineSubtotal` | `BigDecimal` | computed |
| `lineGst` | `BigDecimal` | computed |
| `lineTotal` | `BigDecimal` | computed |

Sample document:

```json
{
  "id": "invoice-uuid",
  "orgId": "org-uuid",
  "invoiceNumber": "INV-20260422-ABCD",
  "clientId": "client-uuid",
  "clientName": "Acme Corp",
  "clientEmail": "client@example.com",
  "issueDate": "2026-04-22",
  "dueDate": "2026-05-07",
  "status": "DRAFT",
  "subtotal": 50000,
  "gstTotal": 9000,
  "totalAmount": 59000,
  "amountPaid": 0,
  "balanceDue": 59000,
  "currency": "INR",
  "items": [
    {
      "id": "item-uuid",
      "type": "SERVICE",
      "description": "Consulting retainer",
      "quantity": null,
      "rate": 50000,
      "gstPercent": 18,
      "lineSubtotal": 50000,
      "lineGst": 9000,
      "lineTotal": 59000
    }
  ],
  "source": "VOICE",
  "voiceContext": {"sessionId": "session-uuid", "createdViaVoice": true, "transcript": "Create invoice for Acme"}
}
```

## 7.5 `transactions`

Source: `MoneyOps/backend/src/main/java/com/moneyops/transactions/entity/Transaction.java`

| Field | Type | Constraints / defaults | Notes |
| --- | --- | --- | --- |
| `id` | `String` | generated UUID | primary key |
| `orgId` | `String` | indexed | tenant isolation |
| `clientId` | `String` | indexed | references client |
| `invoiceId` | `String` | indexed | references invoice |
| `type` | `enum TransactionType` | required | `INCOME` or `EXPENSE` |
| `amount` | `BigDecimal` | required in normal flows | amount |
| `currency` | `String` | default `INR` | currency |
| `transactionDate` | `LocalDate` | optional in entity, often set by service | payment/expense date |
| `category` | `String` | optional | domain category |
| `description` | `String` | optional | freeform description |
| `paymentMethod` | `String` | optional | payment medium |
| `referenceNumber` | `String` | optional | external reference |
| `aiCategory` | `String` | optional | AI classification |
| `aiConfidence` | `Float` | optional | AI confidence |
| `voiceContext` | `Transaction.VoiceContext` | optional | `sessionId`, `recordedViaVoice`, `transcript` |
| `createdAt` | `LocalDateTime` | audited | timestamp |
| `updatedAt` | `LocalDateTime` | audited | timestamp |
| `createdBy` | `String` | audited | creator |
| `updatedBy` | `String` | audited | updater |
| `deletedAt` | `LocalDateTime` | nullable | soft delete |
| `idempotencyKey` | `String` | unique partial index when present | duplicate prevention |

Indexes observed:

- `orgId`
- `clientId`
- `invoiceId`
- compound index `{orgId, type, deletedAt}`
- unique partial `idempotencyKey`

Sample document:

```json
{
  "id": "txn-uuid",
  "orgId": "org-uuid",
  "clientId": "client-uuid",
  "invoiceId": "invoice-uuid",
  "type": "INCOME",
  "amount": 59000,
  "currency": "INR",
  "transactionDate": "2026-04-25",
  "category": "Sales",
  "description": "Invoice payment",
  "paymentMethod": "BANK_TRANSFER",
  "referenceNumber": "UTR123456",
  "voiceContext": {"sessionId": "session-uuid", "recordedViaVoice": true, "transcript": "Record payment for invoice"},
  "deletedAt": null
}
```

## 7.6 `audit_logs`

Source: `MoneyOps/backend/src/main/java/com/moneyops/audit/entity/AuditLog.java`

| Field | Type | Constraints / defaults | Notes |
| --- | --- | --- | --- |
| `id` | `String` | generated UUID | primary key |
| `orgId` | `String` | indexed | tenant isolation |
| `userId` | `String` | indexed | actor |
| `entityType` | `String` | required by log service flows | target type |
| `entityId` | `String` | indexed | target id |
| `operation` | `enum AuditLog.Operation` | `CREATE`, `UPDATE`, `DELETE` | operation kind |
| `oldValues` | `String` | optional | serialized JSON snapshot |
| `newValues` | `String` | optional | serialized JSON snapshot |
| `changes` | `String` | optional | diff payload |
| `ipAddress` | `String` | optional | currently a TODO area in broader docs |
| `userAgent` | `String` | optional | currently a TODO area in broader docs |
| `timestamp` | `LocalDateTime` | indexed, auto-filled if null | event time |

Sample document:

```json
{
  "id": "audit-uuid",
  "orgId": "org-uuid",
  "userId": "user-uuid",
  "entityType": "INVOICE",
  "entityId": "invoice-uuid",
  "operation": "CREATE",
  "oldValues": null,
  "newValues": "{\"invoiceNumber\":\"INV-20260422-ABCD\"}",
  "changes": "{\"status\":\"DRAFT\"}",
  "ipAddress": null,
  "userAgent": null,
  "timestamp": "2026-04-22T14:00:00"
}
```

## 7.7 `documents`

Source: `MoneyOps/backend/src/main/java/com/moneyops/documents/entity/MoneyOpsDocument.java`

| Field | Type | Constraints / defaults | Notes |
| --- | --- | --- | --- |
| `id` | `String` | generated UUID | primary key |
| `orgId` | `String` | indexed | tenant isolation |
| `name` | `String` | none | human filename/title |
| `type` | `String` | none | domain type |
| `size` | `Long` | none | file size |
| `firebasePath` | `String` | none | storage path |
| `downloadUrl` | `String` | none | retrieval URL |
| `mimeType` | `String` | none | MIME type |
| `uploadedBy` | `String` | none | uploader user id |
| `linkedEntityType` | `String` | none | polymorphic reference type |
| `linkedEntityId` | `String` | none | polymorphic reference id |
| `createdAt` | `LocalDateTime` | audited | timestamp |
| `updatedAt` | `LocalDateTime` | audited | timestamp |
| `createdBy` | `String` | audited | creator |
| `updatedBy` | `String` | audited | updater |
| `deletedAt` | `LocalDateTime` | nullable | soft delete |
| `isConfidential` | `boolean` | default `false` | sensitivity flag |
| `category` | `String` | optional | doc category |
| `contentSummary` | `String` | optional | summary/ocr-like output |
| `detectedDeadlines` | `List<String>` | optional | extracted deadlines |

Sample document:

```json
{
  "id": "doc-uuid",
  "orgId": "org-uuid",
  "name": "invoice-INV-20260422-ABCD.pdf",
  "type": "INVOICE",
  "size": 245678,
  "firebasePath": "documents/invoice-uuid.pdf",
  "downloadUrl": "https://storage.example.com/file.pdf",
  "mimeType": "application/pdf",
  "uploadedBy": "user-uuid",
  "linkedEntityType": "INVOICE",
  "linkedEntityId": "invoice-uuid",
  "isConfidential": true,
  "category": "billing",
  "contentSummary": "Invoice PDF for Acme Corp",
  "detectedDeadlines": ["2026-05-07"]
}
```

## 7.8 `regulatory_profiles`

Source: `MoneyOps/backend/src/main/java/com/moneyops/organizations/entity/RegulatoryProfile.java`

| Field | Type | Constraints / defaults | Notes |
| --- | --- | --- | --- |
| `id` | `String` | generated UUID | primary key |
| `orgId` | `String` | indexed | tenant isolation |
| `panNumber` | `String` | optional | compliance |
| `stateOfRegistration` | `String` | optional | compliance |
| `gstRegistered` | `Boolean` | optional | compliance |
| `gstNumber` | `String` | optional | compliance |
| `tanNumber` | `String` | optional | compliance |
| `cinOrLlpIn` | `String` | optional | compliance |
| `msmeNumber` | `String` | optional | compliance |
| `iecCode` | `String` | optional | compliance |
| `deletedAt` | `LocalDateTime` | nullable | soft delete |

Sample document:

```json
{
  "id": "reg-uuid",
  "orgId": "org-uuid",
  "panNumber": "ABCDE1234F",
  "stateOfRegistration": "Karnataka",
  "gstRegistered": true,
  "gstNumber": "29ABCDE1234F1Z5",
  "tanNumber": "BLRA12345B",
  "cinOrLlpIn": "U12345KA2025PTC123456",
  "msmeNumber": "UDYAM-KR-01-0000001",
  "iecCode": "1234567890",
  "deletedAt": null
}
```

## 7.9 `invites`

Source: `MoneyOps/backend/src/main/java/com/moneyops/users/entity/Invite.java`

| Field | Type | Constraints / defaults | Notes |
| --- | --- | --- | --- |
| `id` | `String` | generated UUID | primary key |
| `orgId` | `String` | indexed | tenant isolation |
| `email` | `String` | indexed | invited email |
| `role` | `User.Role` | optional | invited role |
| `token` | `String` | none in entity, used operationally | invite code/token |
| `expiresAt` | `LocalDateTime` | optional | expiry |
| `status` | `Invite.InviteStatus` | default `PENDING` | `PENDING`, `ACCEPTED`, `EXPIRED` |
| `createdAt` | `LocalDateTime` | optional | timestamp |
| `updatedAt` | `LocalDateTime` | optional | timestamp |
| `createdBy` | `String` | optional | inviter |
| `deletedAt` | `LocalDateTime` | nullable | soft delete |

Sample document:

```json
{
  "id": "invite-uuid",
  "orgId": "org-uuid",
  "email": "teammate@example.com",
  "role": "STAFF",
  "token": "invite-token",
  "expiresAt": "2026-04-29T12:00:00",
  "status": "PENDING",
  "createdAt": "2026-04-22T12:00:00",
  "updatedAt": "2026-04-22T12:00:00",
  "createdBy": "owner-user-uuid",
  "deletedAt": null
}
```

## 7.10 `team_invites`

Source: `MoneyOps/backend/src/main/java/com/moneyops/invites/TeamInvite.java`

| Field | Type | Constraints / defaults | Notes |
| --- | --- | --- | --- |
| `id` | `String` | primary key | custom or generated upstream |
| `email` | `String` | none | invitee |
| `orgId` | `String` | none | organization |
| `role` | `String` | none | role string |
| `token` | `String` | unique index | invite token |
| `status` | `String` | none | `PENDING`, `ACCEPTED`, `EXPIRED` by convention |
| `expiresAt` | `Instant` | TTL index | auto-expiry collection behavior |
| `createdAt` | `Instant` | optional | creation time |

Sample document:

```json
{
  "id": "team-invite-uuid",
  "email": "teammate@example.com",
  "orgId": "org-uuid",
  "role": "STAFF",
  "token": "team-token",
  "status": "PENDING",
  "expiresAt": "2026-04-29T12:00:00Z",
  "createdAt": "2026-04-22T12:00:00Z"
}
```

## 7.11 `voice_conversations`

Source: `MoneyOps/backend/src/main/java/com/moneyops/orchestrator/entity/VoiceConversation.java`

| Field | Type | Constraints / defaults | Notes |
| --- | --- | --- | --- |
| `id` | `String` | generated UUID | primary key |
| `orgId` | `String` | indexed | tenant isolation |
| `userId` | `String` | none | actor |
| `sessionId` | `String` | none | voice session identifier |
| `summary` | `String` | optional | conversation summary |
| `status` | `String` | default `active` | active/completed/failed by convention |
| `startedAt` | `LocalDateTime` | auto if null | session start |
| `endedAt` | `LocalDateTime` | optional | session end |
| `duration` | `Integer` | optional | seconds |
| `messages` | `List<Message>` | default empty | embedded conversation history |
| `tasksGenerated` | `List<String>` | default empty | outputs/tasks |
| `totalTurns` | `Integer` | default `0` | turn count |

Embedded `Message` shape:

| Field | Type | Notes |
| --- | --- | --- |
| `role` | `String` | `user` or `assistant` by convention |
| `content` | `String` | utterance text |
| `timestamp` | `LocalDateTime` | per-turn time |
| `intent` | `String` | optional user intent |

Sample document:

```json
{
  "id": "voice-conv-uuid",
  "orgId": "org-uuid",
  "userId": "user-uuid",
  "sessionId": "session-uuid",
  "summary": "Invoice creation flow for Acme Corp",
  "status": "completed",
  "startedAt": "2026-04-22T12:00:00",
  "endedAt": "2026-04-22T12:05:00",
  "duration": 300,
  "messages": [
    {"role": "user", "content": "Create invoice for Acme", "timestamp": "2026-04-22T12:00:05", "intent": "INVOICE_CREATE"},
    {"role": "assistant", "content": "What amount should I use?", "timestamp": "2026-04-22T12:00:07", "intent": null}
  ],
  "tasksGenerated": ["invoice_created"],
  "totalTurns": 6
}
```

## 7.12 `orchestrator_activities`

Source: `MoneyOps/backend/src/main/java/com/moneyops/orchestrator/entity/OrchestratorActivity.java`

| Field | Type | Constraints / defaults | Notes |
| --- | --- | --- | --- |
| `id` | `String` | generated UUID | primary key |
| `orgId` | `String` | indexed | tenant isolation |
| `userId` | `String` | none | actor |
| `type` | `String` | none | `task_assigned`, `decision_made`, etc. by convention |
| `description` | `String` | none | human-readable summary |
| `agent` | `String` | optional | agent name |
| `status` | `String` | optional | completed/in_progress/failed/pending |
| `intent` | `String` | optional | source intent |
| `sessionId` | `String` | optional | related voice session |
| `timestamp` | `LocalDateTime` | indexed, auto if null | activity time |

Sample document:

```json
{
  "id": "orch-act-uuid",
  "orgId": "org-uuid",
  "userId": "user-uuid",
  "type": "voice_action",
  "description": "Finance agent created an invoice draft",
  "agent": "Finance Agent",
  "status": "completed",
  "intent": "INVOICE_CREATE",
  "sessionId": "session-uuid",
  "timestamp": "2026-04-22T12:00:10"
}
```

---

## 8. Planned But Not Implemented As Separate Collections

These are important because older docs describe them as core schema:

### 8.1 `voice_sessions`

Status: not implemented as a backend `@Document`

Current reality:

- AI Gateway `SessionManager` stores `VoiceSession` objects in an in-memory Python dictionary
- TTL is in-process only (`600` seconds)
- locking is in-process only
- comments explicitly state Redis or DB should be used in production for true atomicity

Implication:

- voice session durability is weaker than the schema doc suggests
- a restart of the AI gateway can lose active conversational state unless some external sync path preserves enough context elsewhere

### 8.2 `idempotency_keys`

Status: not implemented as a separate collection

Current reality:

- idempotency is embedded directly on `clients`, `invoices`, and `transactions`
- each entity has a unique partial index on `idempotencyKey`

Implication:

- duplicate prevention exists
- but there is no standalone replay ledger with payload/response capture as described in the older schema document

---

## 9. Request Flows And Data Pipelines

## 9.1 Web Invoice Creation Flow

High-level path:

1. Frontend creates invoice payload from UI.
2. Request goes through frontend proxy `/api` to backend target.
3. Backend `InvoiceController.createInvoice()` reads organization and user context from `OrgContext`.
4. `InvoiceService.createInvoice()`:
   - validates organization and user presence
   - enforces team-action authorization
   - sets default source to `MANUAL` if not supplied
   - validates invoice DTO
   - if `clientId` exists, snapshots client name/email/company/phone onto invoice
   - generates invoice number if absent
   - recalculates totals server-side
   - saves invoice
   - writes audit log
5. Response returns invoice DTO to frontend.

Data touched:

- `clients` lookup
- `invoices` write
- `audit_logs` write

## 9.2 Voice Invoice Creation Flow

High-level path:

1. User speaks into LiveKit room.
2. Voice service entrypoint receives transcription.
3. Voice service sends text to AI gateway `/api/v1/voice/process`.
4. AI gateway `voice.py` builds `VoiceContext` and delegates to `voice_processor.process()`.
5. `FinanceAgent.handle_invoice_create()`:
   - creates or updates invoice draft
   - locks session to `FINANCE_AGENT`
   - merges extracted entities and free text
   - asks follow-up questions until client, amount, item type, item description, GST, due date, and confirmation are resolved
   - validates team security code
   - sends final payload through `BackendHttpAdapter.create_invoice_direct()`
6. Backend creates the invoice with source `VOICE`.
7. Voice service speaks response and publishes UI events back to the frontend/live room.

Data touched:

- AI gateway in-memory session state
- backend `clients`
- backend `invoices`
- backend `audit_logs`
- optionally orchestrator sync endpoints if enabled for session/org

## 9.3 Record Payment Flow

1. Backend receives payment request on invoice or transaction endpoint.
2. `InvoiceService.recordPayment()` loads invoice.
3. It routes to transaction service to create an `INCOME` transaction.
4. Invoice denormalized fields are updated:
   - `amountPaid`
   - `balanceDue`
   - `status`
   - `paymentDate`

Data touched:

- `transactions`
- `invoices`

## 9.4 Voice Session Lifecycle

Current implemented lifecycle:

1. Voice service opens room session and generates local `session_id`.
2. AI gateway `SessionManager` creates an in-memory `VoiceSession`.
3. Session tracks:
   - draft invoice or client state
   - locked intent
   - locked agent type
   - dedup hash and timestamps
   - processing lock
   - turn history
4. Session expires if inactive beyond internal TTL or process restarts.

Important limitation:

- this is not yet the Redis/Mongo durable `voice_sessions` model described in docs

## 9.5 Agent Routing Flow

1. Intent classifier determines `Intent`.
2. `AgentRouter.route()` resolves the primary agent from schema intent requirements.
3. If a session has a locked agent and it supports the new intent, the router reuses it.
4. In MVP mode, a single primary agent executes.
5. In multi-agent mode, supporting agents would execute in parallel, but much of that is still scaffolded.

Current agent reality:

- finance agent is active
- general agent is always available as fallback
- market/strategy agent is current implementation for strategic flows
- other agents are feature-flag placeholders or partial implementations

---

## 10. Security Model

## 10.1 Tenant Isolation

Primary mechanisms:

- `orgId` on most domain collections
- `X-Org-Id` propagation
- `OrgContext` resolution in backend controllers
- service methods generally query with `findBy...AndOrgId...AndDeletedAtIsNull`

Risk note:

- older schema docs prescribe mandatory explicit header enforcement everywhere
- current code often falls back from headers to `OrgContext`
- isolation is materially better than earlier versions, but consistency should still be audited controller-by-controller

## 10.2 Sensitive Action Protection

`TeamActionAuthorizationService` requires:

- valid org context
- valid user context
- user membership in org
- active user status
- role currently limited to `OWNER` or `STAFF` for sensitive create actions
- valid team security code

This protects client and invoice creation workflows.

## 10.3 Auth

- backend uses JWT + security filters
- API gateway also contains JWT validation logic
- frontend uses Clerk client-side identity
- backend onboarding resolves Clerk user ids to internal users

## 10.4 Audit

- create/update/delete operations can be logged to `audit_logs`
- pagination in `AuditLogController` is still a TODO
- `ipAddress` and `userAgent` fields exist on the entity but are not yet reliably populated end-to-end

---

## 11. Operational Procedures

## 11.1 Environment Variables

Shared root `.env` currently carries:

- MongoDB Atlas connection
- backend port and JWT values
- Groq API key
- LiveKit credentials
- Redis settings
- voice-service settings
- frontend target URLs
- Resend email values

Operational conclusion:

- current critical env variables are largely present
- startup blockers are more likely to be process/runtime orchestration issues than missing secrets

## 11.2 Recommended Local Startup Order

Using code/config conventions:

1. Redis
2. Backend core
3. AI gateway
4. Voice service
5. API gateway
6. Frontend

Using Docker Compose:

```bash
cd MoneyOps
docker-compose up -d
```

## 11.3 Service-Specific Dev Starts

Backend:

```bash
cd MoneyOps/backend
mvn spring-boot:run
```

AI gateway:

```bash
cd MoneyOps/ai-gateway
uvicorn app.main:app --reload --port 8001
```

Voice service:

```bash
cd MoneyOps/voice-service
python -m app.agent.entrypoint dev
```

Frontend:

```bash
cd MoneyOps/Frontend
npm run dev
```

## 11.4 Validation Checklist After Boot

- backend `GET /actuator/health` should respond, likely requiring auth or gateway context depending on security rules
- AI gateway `GET /api/v1/health` should return healthy JSON
- voice token endpoint should work if LiveKit deps and credentials are valid
- frontend should load on port `3000`
- invoice and client APIs should respond with authenticated context

---

## 12. Testing And Verification State

## 12.1 Verified In This Pass

- AI gateway health endpoint is live
- backend process is live enough to reject unauthenticated health access
- backend offline compile succeeded outside sandbox
- API gateway offline compile succeeded outside sandbox
- frontend production build succeeded outside sandbox
- `MoneyOps/.env` contains the required Groq and LiveKit variable names
- MongoDB Atlas was used by backend in logged runs
- voice service, API gateway runtime, and frontend dev server were not reachable during probe

## 12.2 Historical Test Evidence In Repo

From `docs/test_results.md`:

- AI gateway health test passed
- intent classification test passed
- entity extraction test passed
- simple prompt test passed
- Groq health test passed

From `VOICE_AGENT_TESTING_GUIDE.md`:

- manual validation flows exist for voice consistency, deduplication, UI + voice interactions

From `MoneyOps/voice-service/TEST_GUIDE.md`:

- STT verification guidance exists

## 12.3 Build Verification Attempt Results

Attempted during this pass:

- initial sandboxed attempts failed because Maven tried to use a sandbox-blocked user repository path and Vite hit `esbuild` spawn `EPERM`
- approved out-of-sandbox reruns then succeeded:
  - backend `mvn.cmd -o -DskipTests compile` -> `BUILD SUCCESS`, `164` source files, `7.824s`
  - API gateway `mvn.cmd -o -DskipTests compile` -> `BUILD SUCCESS`, `15` source files, `4.867s`
  - frontend `npm.cmd run build` -> success in `8.98s`

Interpretation:

- backend, API gateway, and frontend are buildable in the local toolchain when sandbox restrictions are removed
- the main operational gap is runtime parity and service orchestration, not basic compile failure
- follow-up cleanup is still warranted:
  - API gateway compile emitted an unchecked/unsafe operations note for `GlobalExceptionHandler.java`
  - frontend build emitted a large-chunk warning for the main bundle

---

## 13. Known Issues And Remediation

This section is ordered by technical dependency, not by convenience.

## 13.1 Critical: Service Runtime Parity Is Incomplete

Observed:

- backend running
- AI gateway running
- voice service not running
- API gateway not running
- frontend not running

Impact:

- full end-to-end voice and routed web stack is not currently active

Recommended next action:

1. start or restart all services in dependency order
2. verify ports `8000`, `8001`, `8003`, `8080`, and `3000`
3. record the exact failure if any service still does not boot

## 13.2 High: Documentation Drift Versus Code

Observed:

- old schema doc describes 9 collections plus planned `voice_sessions` and `idempotency_keys`
- current code implements 12 document collections and no standalone `voice_sessions` or `idempotency_keys`
- old architecture doc mentions Postgres and Celery, while current backend uses MongoDB and the current repo does not center Postgres as active persistence

Impact:

- maintainers can make incorrect assumptions about live behavior

Recommended next action:

- treat this report as the new canonical handoff basis
- update `docs/architecture.md` and `docs/MoneyOps_Database_Schema.md` to match the code

## 13.3 High: Voice Session Durability Is Weaker Than Intended

Observed:

- AI gateway session manager stores sessions in memory only
- code comment explicitly says Redis or database is needed for true atomicity

Impact:

- process restarts can lose active voice workflow state
- distributed scaling would be unsafe without shared session persistence

Recommended next action:

1. implement Redis-backed session storage
2. optionally persist completed or long-running sessions to MongoDB
3. align implementation with the documented `voice_sessions` concept

## 13.4 High: Spring Boot Baselines Are Aging

Observed:

- backend parent is Spring Boot `3.2.1`
- API gateway parent is Spring Boot `3.2.0`
- troubleshooting doc already flags 3.2.1 as outdated

Impact:

- security and maintenance risk

Recommended next action:

1. test upgrade path for backend and gateway in a dedicated branch
2. align Spring Boot versions across Java services
3. re-run integration and auth regression tests after upgrade

## 13.5 Medium: Audit API Pagination Is Not Implemented

Observed:

- `AuditLogController.getAllAuditLogs()` returns full list and wraps a synthetic one-page response
- controller comment explicitly says `TODO: Implement pagination`

Impact:

- audit queries can become heavy and non-scalable

Recommended next action:

- add paginated repository/service methods
- keep existing response wrapper shape if UI depends on it

## 13.6 Medium: IP Address And User Agent Audit Enrichment Is Incomplete

Observed:

- `AuditLog` entity has `ipAddress` and `userAgent`
- broader docs call this area unfinished

Impact:

- compliance and forensic value is reduced

Recommended next action:

- capture request metadata in controllers/filter layer
- propagate to audit log service methods

## 13.7 Medium: Frontend Proxy Targets Depend On API Gateway Being Up

Observed:

- frontend `/api` proxy defaults to `127.0.0.1:8002` in `vite.config.js`
- actual API gateway config uses `8080`

Impact:

- local frontend/backend wiring may be inconsistent depending on environment variables

Recommended next action:

- reconcile the default proxy target with actual API gateway runtime port
- or document required `VITE_BACKEND_PROXY_TARGET`

## 13.8 Low: Code Hygiene / Merge Residue

Observed:

- several Java files contain duplicate imports and comments showing iterative patching

Impact:

- readability cost
- higher risk of subtle maintenance mistakes

Recommended next action:

- run formatter/import cleanup passes after functionality is stabilized

---

## 14. Resolved Or Partially Resolved Improvements Documented In Repo

The following improvements appear to have been implemented or at least materially advanced:

- UUID to string normalization for cross-collection references
- stronger org isolation patterns in service/repository usage
- voice agent session locking and deduplication
- async LiveKit event handler fix
- backend security hardening around header trust
- OAuth secret placeholder migration into env-driven config
- embedded idempotency keys on write entities

Important nuance:

Some of these are fully reflected in current code, while others are reflected in docs plus partial code patterns. Future maintainers should verify each claim against specific files before refactoring.

---

## 15. Recommended Action Plan For The Next AI Maintainer

### Immediate

1. Bring all services up and record exact runtime failures for any that still do not start.
2. Reconcile frontend proxy defaults with API gateway port reality.
3. Decide whether API gateway should be mandatory in local dev or bypassed for some flows.

### Short Term

1. Implement durable AI gateway session storage in Redis.
2. Update architecture and database docs to reflect the code as it exists now.
3. Add proper audit pagination and metadata capture.
4. Create a reproducible end-to-end smoke script that validates:
   - backend
   - AI gateway
   - frontend
   - voice service
   - invoice create
   - payment record

### Medium Term

1. Upgrade Spring Boot baselines across both Java services.
2. Rationalize duplicate invite concepts: `invites` versus `team_invites`.
3. Decide whether orchestrator collections are now core schema and document them formally.
4. Evaluate moving from in-memory session locking to distributed locking.

---

## 16. Final Assessment

MoneyOps is a serious multi-service codebase with real domain depth. The project is further along than a typical prototype in these areas:

- tenant-aware financial domain modeling
- voice-to-backend invoice orchestration
- agent routing abstraction
- auditability and sensitive-action controls

The biggest current risk is not "missing code." It is mismatch between:

- what the docs claim
- what the code actually implements
- what services are currently running together

If a new AI maintainer starts from the code first, uses this report as the normalization layer, and treats older docs as historical context rather than truth, the project is maintainable.

---

## 17. Source Checklist

Primary files reviewed:

- `README.md`
- `docs/architecture.md`
- `docs/MoneyOps_Database_Schema.md`
- `docs/troubleshooting_and_tradeoffs.md`
- `docs/test_results.md`
- `docs/test_endpoints.md`
- `IMPLEMENTATION_COMPLETE_VOICE_FIX.md`
- `VOICE_AGENT_TESTING_GUIDE.md`
- `MoneyOps/docker-compose.yml`
- `MoneyOps/Frontend/package.json`
- `MoneyOps/Frontend/vite.config.js`
- `MoneyOps/backend/pom.xml`
- `MoneyOps/backend/src/main/resources/application.yml`
- backend entity and controller classes
- `MoneyOps/api-gateway/pom.xml`
- `MoneyOps/api-gateway/src/main/resources/application.yml`
- `MoneyOps/ai-gateway/pyproject.toml`
- `MoneyOps/ai-gateway/app/config.py`
- `MoneyOps/ai-gateway/app/main.py`
- `MoneyOps/ai-gateway/app/api/v1/voice.py`
- `MoneyOps/ai-gateway/app/orchestration/agent_router.py`
- `MoneyOps/ai-gateway/app/agents/finance_agent.py`
- `MoneyOps/ai-gateway/app/adapters/backend_adapter.py`
- `MoneyOps/ai-gateway/app/state/session_manager.py`
- `MoneyOps/voice-service/app/config.py`
- `MoneyOps/voice-service/app/agent/entrypoint.py`
- `MoneyOps/voice-service/EVENT_HANDLER_FIX.md`
- `MoneyOps/voice-service/TEST_GUIDE.md`

Live probes performed on 2026-04-22:

- `http://127.0.0.1:8000/actuator/health`
- `http://127.0.0.1:8001/api/v1/health`
- `http://127.0.0.1:8003`
- `http://127.0.0.1:8080/actuator/health`
- `http://127.0.0.1:3000`

### 17.1 Evidence Pointers

- Backend env import, MongoDB URI handling, UUID representation, and port: `MoneyOps/backend/src/main/resources/application.yml:3,20-22,39`
- API gateway route inventory, backend/AI/voice upstream URLs, Redis config, and port `8080`: `MoneyOps/api-gateway/src/main/resources/application.yml:27-200,175-185,257-258`
- AI gateway shared `.env` loading, required `GROQ_API_KEY`, backend base URL, and optional LiveKit settings: `MoneyOps/ai-gateway/app/config.py:8-13,34,48-51,86-95`
- Voice service shared `.env` loading and required LiveKit credentials: `MoneyOps/voice-service/app/config.py:10-13,32-43`
- Frontend dev port and proxy mismatch (`/api` defaulting to `8002` while API gateway config uses `8080`): `MoneyOps/Frontend/vite.config.js:10-12,23,33-40`
- Compose startup topology and published ports: `MoneyOps/docker-compose.yml:36-117`
- Invoice creation flow, server-side recalculation, audit logging, and team-action enforcement: `MoneyOps/backend/src/main/java/com/moneyops/invoices/service/InvoiceService.java:119-184`
- Sensitive-action authorization rules: `MoneyOps/backend/src/main/java/com/moneyops/security/team/TeamActionAuthorizationService.java:18-41`
- AI gateway backend header propagation and org/user forwarding: `MoneyOps/ai-gateway/app/adapters/backend_adapter.py:37-150`
- Voice invoice interview flow and final backend submission: `MoneyOps/ai-gateway/app/agents/finance_agent.py:58-317`
- In-memory voice session storage, TTL, deduplication, and explicit note that Redis or DB is needed for true atomicity: `MoneyOps/ai-gateway/app/state/session_manager.py:49-127`
- Audit pagination gap: `MoneyOps/backend/src/main/java/com/moneyops/audit/controller/AuditLogController.java:26-40`

---

End of report.
