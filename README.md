# Resilient Async LangGraph Search Assistant

An enterprise-grade, asynchronous AI orchestration engine powered by **FastAPI** and **LangGraph**. This engine executes multi-engine web search queries through a local **SearXNG** instance and aggregates results into strict, character-capped SMS-ready payloads. 

The architecture features a resilient **Layered Core Pattern** built with dynamic failovers: utilizing **OpenAI** cloud infrastructure as the primary execution engine with a graceful cascade down to a localized **Ollama** engine if cloud connections encounter network faults, authentication breaks, or strict layout rejections.

---

## 🏗️ Architectural Overview & Design Patterns

To deliver clear separation of concerns (SoC), decoupling metrics, and production stability, the monolithic core has been refactored into isolated functional boundaries:

```text
       [ FastAPI Client Request Layer ]
                      │
                      ▼
          [ LangGraph Engine State ]
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
  [ SearXNG Node ]        [ LLM Summary Node ]
         │                         │
         ▼                         ▼
[ Infrastructure Client ]   [ Resilient LLM Router ]
                            ┌──────┴──────┐
                            ▼             ▼
                       [ OpenAI ] ──► [ Ollama ]
                     (Primary Cloud)  (Local Fallback)
```

### Key Engineering Patterns Implemented:
* **Interface-Driven Component Strategy:** LLM integrations inherit from a unified abstract interface (`BaseLLMService`), making component swaps or third-party unit-mocking straightforward without breaking the runtime workflow.
* **Autonomous Resilience Loop (LangGraph Transitions):** The state machine evaluates data structures iteratively via LLM-backed judgment edges. If payload evaluations fail quality checks, it dynamically modifies parameters (e.g., swapping search engines from commercial arrays to isolated encyclopaedic clusters like Wikipedia) and self-heals over cyclical feedback loops.
* **Non-Blocking Thread Concurrency:** Local execution models (Ollama) carry blocking synchronous IO signatures. These processing blocks are offloaded to isolated asynchronous event executors (`loop.run_in_executor`) to prevent engine-thread starvation and keep FastAPI serving throughput smooth.
* **Dual-Stream Rolling Auditing:** Logs are multiplexed into a dedicated CLI terminal context and a standard automated rotating file buffer to enable auditing while avoiding systemic disk usage issues.

---

## 📂 Repository Directory Layout

```text
search-assistant/
│
├── config/
│   ├── settings.py          # Centralized configuration via pydantic-settings
│   └── logging_config.py    # Non-duplicating dual-stream logger bootstrapper
│
├── graph/
│   ├── state.py             # Strongly-typed LangGraph State Schema
│   ├── nodes.py             # Functional business process action handlers
│   ├── edges.py             # Conditional structural evaluation routing logic
│   └── workflow.py          # Framework state construction and compilation
│
├── services/
│   ├── search/
│   │   └── searxng.py       # Client network interface wrapper for SearXNG
│   └── llm/
│       ├── base.py          # Structural Abstract Base Class for LLM abstractions
│       ├── openai_svc.py    # Primary OpenAI Integration Layer
│       ├── ollama_svc.py    # Fallback Local Ollama Driver
│       └── router.py        # Centralized Cascade Selection Manager
│
├── api/
│   └── routes.py            # Restful API endpoints pointing to the compiled state graph
│
├── .env.example             # Clean configuration template for deployments
├── main.py                  # Operational server bootstrapper
└── requirements.txt         # Pinned operational application dependencies
```

---

## 🚀 Quick Start & Installation

### 1. Prerequisites
Ensure you have Python 3.10+ installed along with a local running instance of **SearXNG** and **Ollama**.

### 2. Dependency Setup
Clone the repository and install all engine dependencies within an isolated virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Allocation
Initialize your localized runtime parameters by mirroring the deployment template:
```bash
cp .env.example .env
```
Open `.env` and assign your personal `OPENAI_API_KEY`. If no key is attached, the execution layers will automatically route down to local **Ollama** runtimes natively.

### 4. Booting the ASGI Server
Launch the production web engine directly using Uvicorn:
```bash
uvicorn main:app --reload
```
The application will mount an active server worker listener context pointing to: `http://127.0.0.1:8000`

---

## 🧪 API Validation & Interface Tracking

You can track runtime operational steps and execution cascades through automated Swagger generation portals:
* **Interactive Open-API UI:** Navigate to `http://127.0.0`
* **Direct Pipeline Execution Call:**
  ```text
  GET http://127.0.0 is the Taj Mahal?
  ```

### Sample Automated Fallback Logging Sequence:
```text
2026-09-12 16:30:30,142 [INFO] (nodes.py:13) - --- [Node] Querying SearXNG (Attempt 1) ---
2026-09-12 16:30:32,116 [INFO] (edges.py:11) - --- [Edge Evaluation] Analyzing search context quality ---
2026-09-12 16:30:32,116 [INFO] (router.py:24) - Evaluating via Primary LLM (OpenAI)...
2026-09-12 16:30:32,116 [WARNING] (router.py:28) - Primary evaluation failed. Diverting evaluation to local Ollama...
2026-09-12 16:30:38,973 [INFO] (ollama_svc.py:79) -    [Ollama Judge Process] Raw response received: 'TRUE'
```
