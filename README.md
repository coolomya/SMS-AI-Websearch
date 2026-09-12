# SMS-AI-Websearch

![GitHub stars](https://img.shields.io/github/stars/coolomya/SMS-AI-Websearch?style=for-the-badge&logo=github) ![GitHub forks](https://img.shields.io/github/forks/coolomya/SMS-AI-Websearch?style=for-the-badge&logo=github) ![GitHub issues](https://img.shields.io/github/issues/coolomya/SMS-AI-Websearch?style=for-the-badge&logo=github) ![Last commit](https://img.shields.io/github/last-commit/coolomya/SMS-AI-Websearch?style=for-the-badge&logo=github)

## 📑 Table of Contents

- [Description](#description)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Key Dependencies](#key-dependencies)
- [Project Structure](#project-structure)
- [Development Setup](#development-setup)
- [Contributors](#contributors)
- [Contributing](#contributing)

## 📝 Description

SMS-AI-Websearch — a backend api built with FastAPI, Python.

## 🛠️ Tech Stack

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white) ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

**Notable libraries:** OpenAI, Uvicorn

## 🏗️ Architecture

A high-level view of how the main pieces fit together:

```mermaid
flowchart TD
    %% Base Styling Definitions
    classDef client fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef runtime fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef workflow fill:#fff9c4,stroke:#fbc02d,stroke-width:2px;
    classDef router fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    classDef infra fill:#ffe0b2,stroke:#f57c00,stroke-width:2px;

    %% Component Elements
    User["👤 User / Client Request"] :::client
    API["⚙️ FastAPI HTTP Endpoint Layer"] :::runtime
    
    subgraph GraphEngine ["🔄 LangGraph State Orchestration Pipeline"]
        StartNode((START))
        SearchNode["🔍 SearXNG Search Node<br/>(Retries 1-3)"] :::workflow
        SMSNode["🤖 LLM SMS Summary Node<br/>(Character Constraint Verification)"] :::workflow
        KBNode["📚 LLM Knowledge Base Node<br/>(Parametric Fallback Passer)"] :::workflow
        StaticNode["🚨 Static Circuit Breaker<br/>(Zero-Dependency Hard Stop)"] :::workflow
        EndNode((END))
    end

    Router["🔀 Resilient Dual-LLM Router Service<br/>(BaseLLMService Interface)"] :::router
    
    subgraph ExternalServices ["🐳 Containerized Infrastructure Nodes"]
        SearXNG["🐋 SearXNG Instance<br/>(Docker Port 8080)"] :::infra
        OpenAI["☁️ OpenAI Cloud Gateway<br/>(Primary gpt-4o-mini)"] :::infra
        Ollama["💻 Ollama Local Daemon<br/>(Fallback llama3.2:3b)"] :::infra
    end

    %% Workflow Connectivity Matrix
    User -->|GET /api/v1/search-assistant| API
    API -->|ainvoke initial_state| StartNode
    
    StartNode --> SearchNode
    SearchNode -->|Fetch Web Snippets| SearXNG
    
    %% Condition Edge Branching: Post Search Evaluation
    SearchNode --> Edge1{Context Quality Pass?}
    Edge1 -->|TRUE| SMSNode
    Edge1 -->|FALSE & Count < Max| SearchNode
    Edge1 -->|FALSE & Retries Blown| KBNode

    %% Summary Logic Routing Pipeline
    SMSNode -->|Evaluate Text Draft| Router
    Router --> Edge2{Constraints Met?}
    Edge2 -->|TRUE| EndNode
    Edge2 -->|FALSE & Count < Max| SMSNode
    Edge2 -->|FALSE & Retries Blown| KBNode

    %% Recovery / Ultimate Fallback Architecture Path
    KBNode -->|Invoke Parametric Query| Router
    Router -->|If Models Live| EndNode
    Router -.->|If Network Drops / Crash| StaticNode
    StaticNode --> EndNode
    
    EndNode -->|JSON HTTP Payload Response| API
    API --> User

    %% LLM Component Binding Interoperability Matrix
    Router -->|1. Primary Channel| OpenAI
    OpenAI -.->|Fallback Failover Loop| Ollama
```

## ⚡ Quick Start

```bash

# 1. Clone the repository
git clone https://github.com/coolomya/SMS-AI-Websearch.git

# 2. Create & activate a virtualenv
python -m venv venv && source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env

# Run the API
uvicorn main:app --reload
```

---

## 🐳 External Infrastructure Services Setup

### 1. Containerized SearXNG Engine
Run a localized instance of SearXNG inside Docker:

```bash
docker run -d \
  -p 8080:8080 \
  --name local-searxng \
  --restart unless-stopped \
  -e SEARXNG_SETTINGS_URL=/etc/searxng/settings.yml \
  searxng/searxng:latest
```

### 2. Local Ollama Inference Node
Ensure Ollama is running locally and pull your target model weights:

```bash
ollama pull llama3.2:3b
```

---


## 🔑 Environment Variables

The following environment variables are required (see `.env.example`):

```bash
APP_TITLE=
SEARXNG_URL=
MAX_RETRY_COUNT=
OPENAI_API_KEY=
OPENAI_MODEL=
OLLAMA_MODEL=
```

## 📦 Key Dependencies

```
langgraph: latest
ollama: latest
openai: latest
fastapi: latest
uvicorn: latest
httpx: latest
pydantic_settings: latest
```

## 📁 Project Folder Layout

```text
.
├── api/          # REST API endpoints & LLM sandbox routers
├── config/       # Logging & centralized Pydantic settings
├── graph/        # LangGraph states, nodes, edges & workflow builder
├── services/     # LLM providers (OpenAI, Ollama, router) & SearXNG search client
├── .env.example  # Configuration template
├── main.py       # ASGI server initialization
└── requirements.txt
```

## 📁 Project Structure

```
.
├── .env.example
├── api
│   └── routes.py
├── config
│   ├── logging_config.py
│   └── settings.py
├── graph
│   ├── edges.py
│   ├── nodes.py
│   ├── state.py
│   └── workflow.py
├── main.py
├── requirements.txt
└── services
    ├── llm
    │   ├── base.py
    │   ├── ollama_svc.py
    │   ├── openai_svc.py
    │   └── router.py
    └── search
        └── searxng.py
```

## 🛠️ Development Setup

### Python
1. Install Python (v3.10+ recommended)
2. `python -m venv venv && source venv/bin/activate`  (Windows: `venv\Scripts\activate`)
3. `pip install -r requirements.txt`

## 👥 Contributors

Thanks to everyone who has contributed to this project:

<p align="left">
<a href="https://github.com/coolomya" title="coolomya"><img src="https://avatars.githubusercontent.com/u/47236054?v=4&s=64" width="64" height="64" alt="coolomya" style="border-radius:50%" /></a>
</p>

[See the full list of contributors →](https://github.com/coolomya/SMS-AI-Websearch/graphs/contributors)

## 👥 Contributing

Contributions are welcome! Here's the standard flow:

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/coolomya/SMS-AI-Websearch.git`
3. **Branch**: `git checkout -b feature/your-feature`
4. **Commit**: `git commit -m 'feat: add some feature'`
5. **Push**: `git push origin feature/your-feature`
6. **Open** a pull request

Please follow the existing code style and include tests for new behavior where applicable.

---

<div align="center">

[![Made with ReadmeBuddy](https://img.shields.io/badge/Made%20with-ReadmeBuddy-8B5CFF?style=for-the-badge&logo=markdown&logoColor=white)](https://readmebuddy.com)

<sub>Generate beautiful READMEs in seconds → <a href="https://readmebuddy.com">readmebuddy.com</a></sub>

</div>
