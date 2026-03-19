# 💸 MoneyOps: Intelligent Financial Orchestration

> **Status**: Phase 5 Complete (Smart CRM & Market Intelligence) 🚀
> **Architecture**: Distributed AI Microservices with Founder Intelligence Layer

MoneyOps is a next-generation financial platform that orchestrates **AI Agents** to handle invoicing, payments, CRM, and business intelligence via **Voice** and **Chat** interfaces. It leverages a "CEO Brain" architecture to go beyond simple CRUD operations.

---

## 🏗️ System Architecture

```mermaid
graph TD
    subgraph ClientLayer [Client Layer]
        WebApp[Web App - React]
        LiveKitVoice[Voice Interface - LiveKit]
    end

    subgraph APIGatewayLayer [API Gateway - Spring Boot]
        APIGateway[Cloud Gateway]
        RateLimiter[Redis Rate Limiter]
        Auth[JWT / Clerk Auth Validation]
        APIGateway --> RateLimiter
        APIGateway --> Auth
    end

    subgraph VoiceServiceLayer [Voice Service - Python/LiveKit]
        LiveKitAgent[LiveKit Agent Framework]
        STT[STT - AssemblyAI / Groq Whisper]
        VAD[Silero VAD]
        TTS[TTS - Cartesia / Groq Orpheus]
        LiveKitAgent --> VAD
        LiveKitAgent --> STT
        LiveKitAgent --> TTS
    end

    subgraph AIGatewayLayer [AI Gateway - FastAPI]
        IntentClassifier[Intent Classifier - Llama 3.3]
        EntityExtractor[Entity Extraction]
        AgentRouter[Agent Router]
        SessionMgr[Session Manager - Redis Cache]
        
        subgraph Agents
            FinanceAgent[Finance Agent]
            SalesCRM[Sales Agent / CRM]
            ComplianceAgent[Compliance Agent]
            MarketAgent[Market Agent]
            Orchestrator[Strategic Orchestrator]
        end
        
        IntentClassifier --> AgentRouter
        AgentRouter --> Agents
        Agents -->|Session| SessionMgr
    end

    subgraph BackendCoreLayer [Backend Core - Spring Boot]
        OrgAdmin[Organization & User Admin]
        InvoiceService[Invoice & Transaction Service]
        ClientService[Client & Lead Service]
        FinanceIntelligence[Financial Intelligence Engine]
        OnboardingService[Onboarding & Demo Data]
        
        %% Intelligence
        ClientService -->|Lead Scoring| BusinessBrain[Founder Intelligence Layer]
    end

    subgraph DataLayer [Data Layer]
        MongoDB[(MongoDB Atlas)]
        RedisCache[(Redis - Cache/Sessions)]
        KafkaBus{Kafka Event Bus}
    end

    subgraph ExternalAPIs [External Integrations]
        Groq[Groq - LLM]
        Tavily[Tavily - Search]
        AssemblyAI[AssemblyAI - STT]
        Cartesia[Cartesia - TTS]
        LiveKitCloud[LiveKit RTC Cloud]
        Clerk[Clerk - Identity Provider]
    end

    %% Flows
    WebApp -->|HTTPS/REST| APIGateway
    APIGateway -->|Route| BackendCoreLayer
    APIGateway -->|Route| AIGatewayLayer
    
    LiveKitVoice -->|WebRTC| LiveKitCloud
    LiveKitCloud <--> LiveKitAgent
    LiveKitAgent -->|Intercept| AIGatewayLayer
    
    Agents -->|Synthesis| Groq
    MarketAgent -->|Tavily Search| ExternalAPIs
    
    BackendCoreLayer --> MongoDB
    BackendCoreLayer --> RedisCache
    AIGatewayLayer --> RedisCache
    
    BackendCoreLayer --> KafkaBus
```

---

## 🧠 Data Flow & Intelligence Pipeline

1. **Transcript Interception**: Speech is captured via LiveKit, transcribed (AssemblyAI/Groq), and intercepted by the `Voice Service`.
2. **Intent Classification**: The `AI Gateway` classifies input into Operational, Strategic, or Conversational intents using Llama 3.3.
3. **Founder Enrichment**: For actions like `CLIENT_CREATE`, the system automatically:
    - Infers industry and business type.
    - Calculates a Lead Score (CEO-level value assessment).
    - Generates Smart Notes for CRM (pitch angles, ESG compliance).
4. **Backend Execution**: Core services update MongoDB and broadcast events via Kafka.
5. **CEO Summary**: The `Orchestrator` synthesizes data from Finance, Market, and Compliance agents to provide an actionable voice response.

---

## 🚀 System Components

| Service | Tech Stack | Description |
| :--- | :--- | :--- |
| **Backend Core** | Java 17, Spring Boot, MongoDB | REST API, Business Logic, Organization Isolation |
| **API Gateway** | Spring Cloud Gateway, Redis | Traffic Routing, Auth, Rate Limiting |
| **AI Gateway** | Python, FastAPI, Groq | multi-Agent Orchestration, Tool Registry, LLM Synthesis |
| **Voice Service** | Python, LiveKit Agents | Real-time Voice I/O with VAD-split utterance buffering |
| **Frontend** | React, LiveKit SDK | Intelligent Web Dashboard & Voice UI |

---

## 🛠️ Technology Stack & Third-party APIs

- **LLM**: Groq (Llama 3.3 70B Versatile)
- **Voice**: LiveKit (Cloud), AssemblyAI (STT), Cartesia (TTS), Silero (VAD)
- **Search**: Tavily (Market Intelligence), SearchAPI
- **Auth**: Clerk (Identity & Organization Management)
- **Database**: MongoDB (Persistence), Redis (Context & Rate Limiting)
- **Infrastructure**: Kafka (Event Bus), Docker Compose

---

## 📚 Documentation

- **[Architecture Deep Dive](docs/architecture.md)**: Original design document. (Legacy reference)
- **[Troubleshooting](docs/troubleshooting_and_tradeoffs.md)**: Decisions on UUID representation and VAD split handling.
- **[Testing Results](docs/test_results.md)**: Latest pipeline verification.
