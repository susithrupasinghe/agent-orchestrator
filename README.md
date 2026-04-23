# MAS – Multi-Agent Bug & Security Analysis System

A fully local multi-agent system that receives bug/security reports via chat, orchestrates five specialised agents to analyse code, audit security issues, and create a support ticket – all with zero cloud costs.

---

## Architecture

```
User message
     │
     ▼
┌─────────────┐        ┌──────────────┐
│ Orchestrator│◄──────►│  LangGraph   │
│  (LLM node) │        │ state machine│
└──────┬──────┘        └──────────────┘
       │ dynamic routing
   ┌───┴───┬──────┬──────┐
   ▼       ▼      ▼      ▼
Front  GitHub  Security ClickUp
Desk   Agent  Auditor   Agent
```

- **Orchestrator** – LLM-powered, decides which agent runs next (no fixed order).
- **Front Desk** – extracts repo URL, file path, and error description.
- **GitHub** – fetches raw source code from a public repo.
- **Security Auditor** – rule-based scanner (secrets, SQL injection, XSS, insecure functions).
- **ClickUp** – creates a mock ticket with priority based on findings.

All state is shared via a `TypedDict`. Redis persists session logs and tracks which agents have run.

---

## Quick Start

### 1. Set up LM Studio

1. Download and install [LM Studio](https://lmstudio.ai/).
2. Download a model (e.g. `Meta-Llama-3-8B-Instruct` or any instruction-tuned model).
3. Go to **Local Server** tab → start the server on port **1234**.
4. Note the exact model identifier shown (e.g. `meta-llama-3-8b-instruct`).

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
LM_STUDIO_URL=http://host.docker.internal:1234/v1
LM_STUDIO_MODEL=meta-llama-3-8b-instruct   # match your LM Studio model name
GITHUB_REPO_URL=https://github.com/owner/repo  # default repo if user doesn't supply one
```

### 3. Run with Docker Compose

```bash
docker-compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Redis: localhost:6379

### 4. Send a message

Open http://localhost:5173 and type something like:

```
There's a SQL injection vulnerability in https://github.com/owner/myapp at app/database.py
```

Or without a repo URL (the env var fallback kicks in):

```
I found a hardcoded API key in our authentication module
```

The agent graph on the right panel shows which agents are active in real time.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Start workflow. Body: `{"message": "..."}` → `{"session_id": "...", "status": "started"}` |
| GET | `/stream/{session_id}` | SSE stream of events |
| GET | `/state/{session_id}` | Current full state snapshot |
| GET | `/history/{session_id}` | All agent run logs from Redis |
| GET | `/health` | Health check |

### SSE Event Types

```json
{"type": "agent_start",  "agent": "FrontDesk"}
{"type": "tool_call",    "agent": "FrontDesk", "tool": "extract_repo_info", "output_summary": "..."}
{"type": "agent_end",    "agent": "FrontDesk", "next_agent": "GitHub", "done": false}
{"type": "state_update", "has_code": true, "findings_count": 3, "has_ticket": false}
{"type": "done",         "final_response": "Analysis complete. Found 3 issues..."}
{"type": "stream_end"}
```

---

## Running Tests

```bash
# Via Docker Compose (no local Python needed)
docker-compose run --rm backend pytest tests/ -v

# Or locally (with a Python 3.11+ venv)
cd backend
pip install -r requirements.txt
pytest ../tests/ -v
```

Tests use `unittest.mock` to stub Redis and the LM Studio HTTP endpoint – no live services needed.

---

## Project Structure

```
mas-system/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── run.py
│   └── app/
│       ├── main.py          # FastAPI app + SSE endpoints
│       ├── state.py         # AgentState TypedDict
│       ├── graph.py         # LangGraph state machine
│       ├── llm_client.py    # OpenAI-compat client → LM Studio
│       ├── redis_logger.py  # Redis persistence helpers
│       ├── agents/          # One file per agent node
│       └── tools/           # One file per tool function
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx           # Root: state + SSE wiring
│       ├── components/
│       │   ├── Chat.jsx      # Chat panel
│       │   ├── FlowGraph.jsx # React Flow agent visualisation
│       │   └── HistoryPanel.jsx
│       └── services/api.js   # fetch wrappers
└── tests/
    ├── conftest.py
    ├── test_front_desk.py
    ├── test_github.py
    ├── test_security.py
    ├── test_clickup.py
    └── test_orchestrator.py
```

---

## Key Design Decisions

- **Dynamic orchestration**: the LLM decides the next agent at each step, so the order can vary based on what's already been done and what information is available.
- **No duplicate runs**: Redis `smembers` tracks which agents have run; the orchestrator prompt explicitly lists them.
- **LM Studio fallback**: if the LLM output is unparseable JSON the orchestrator marks `done=True` to prevent infinite loops.
- **Zero cloud cost**: LM Studio runs entirely on your machine. No OpenAI/Anthropic keys needed.
# agent-orchestrator
