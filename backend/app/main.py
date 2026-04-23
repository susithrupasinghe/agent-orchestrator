"""FastAPI application – chat, SSE streaming, state and history endpoints."""
import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.state import AgentState
from app.redis_logger import (
    get_agent_run_history,
    get_all_sessions,
    load_state_snapshot,
    register_session,
    save_state_snapshot,
)
from app.graph import compiled_graph

# In-process SSE queues keyed by session_id
_sse_queues: dict[str, asyncio.Queue] = {}


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    session_id: str
    status: str


app = FastAPI(title="MAS – Multi-Agent System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _run_workflow(session_id: str, message: str) -> None:
    """Run the LangGraph workflow and emit SSE events per step."""
    queue = _sse_queues.setdefault(session_id, asyncio.Queue())

    initial_state: AgentState = {
        "session_id": session_id,
        "user_message": message,
        "repo_url": None,
        "file_path": None,
        "error_description": None,
        "code_content": None,
        "security_findings": None,
        "ticket_info": None,
        "final_response": None,
        "messages": [{"role": "user", "content": message}],
        "history": [],
        "next_agent": None,
        "input_subset": [],
        "done": False,
    }

    loop = asyncio.get_event_loop()

    def _stream_graph():
        final = initial_state.copy()

        for step in compiled_graph.stream(initial_state):
            for node_name, node_state in step.items():
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    json.dumps({"type": "agent_start", "agent": node_name, "session_id": session_id}),
                )

                # Pull latest log entry for tool call detail
                history = get_agent_run_history(session_id)
                if history:
                    last = history[-1]
                    for tc in last.get("tool_calls", []):
                        loop.call_soon_threadsafe(
                            queue.put_nowait,
                            json.dumps({
                                "type": "tool_call",
                                "agent": node_name,
                                "tool": tc.get("tool"),
                                "output_summary": str(tc.get("output", ""))[:200],
                            }),
                        )

                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    json.dumps({
                        "type": "agent_end",
                        "agent": node_name,
                        "next_agent": node_state.get("next_agent"),
                        "done": node_state.get("done", False),
                    }),
                )

                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    json.dumps({
                        "type": "state_update",
                        "session_id": session_id,
                        "has_code": node_state.get("code_content") is not None,
                        "findings_count": len(node_state.get("security_findings") or []),
                        "has_ticket": node_state.get("ticket_info") is not None,
                        "done": node_state.get("done", False),
                    }),
                )

                final = {**final, **node_state}

        # Build final response
        ticket = final.get("ticket_info")
        findings = final.get("security_findings") or []
        clone_status = final.get("clone_status")
        files_read = []

        # Pull files_read from the GitHub agent's tool call in history
        history = get_agent_run_history(session_id)
        for entry in history:
            if entry.get("agent") == "GitHub":
                for tc in entry.get("tool_calls", []):
                    files_read = tc.get("output", {}).get("files_read", [])

        parts = ["**Analysis complete.**\n"]

        # Repo / clone context
        if clone_status in ("cloned", "pulled"):
            action = "Cloned" if clone_status == "cloned" else "Updated"
            repo_url = final.get("repo_url", "")
            parts.append(f"{action} repository: `{repo_url}`")
            if files_read:
                parts.append(f"Scanned file(s): {', '.join(f'`{f}`' for f in files_read)}")
        elif clone_status == "failed":
            parts.append("⚠ Could not clone the repository – scanned description only.")

        # Security findings
        if findings:
            high   = [f for f in findings if f.get("severity") == "HIGH"]
            medium = [f for f in findings if f.get("severity") == "MEDIUM"]
            low    = [f for f in findings if f.get("severity") == "LOW"]
            parts.append(f"\nFound **{len(findings)}** security issue(s) — {len(high)} HIGH · {len(medium)} MEDIUM · {len(low)} LOW:\n")
            for f in findings[:8]:
                parts.append(f"- **[{f['severity']}]** {f['description']} _(line {f['line_number']})_")
            if len(findings) > 8:
                parts.append(f"- … and {len(findings) - 8} more.")
        elif clone_status in ("cloned", "pulled"):
            parts.append("\nNo security issues detected in the scanned code.")

        if ticket:
            parts.append(f"\nTicket created: **{ticket['id']}** – {ticket['url']}")

        final["final_response"] = "\n".join(parts)
        save_state_snapshot(session_id, final)

        loop.call_soon_threadsafe(
            queue.put_nowait,
            json.dumps({"type": "done", "session_id": session_id, "final_response": final["final_response"]}),
        )
        loop.call_soon_threadsafe(queue.put_nowait, None)

    await loop.run_in_executor(None, _stream_graph)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    session_id = str(uuid.uuid4())
    _sse_queues[session_id] = asyncio.Queue()
    register_session(session_id, req.message)
    background_tasks.add_task(_run_workflow, session_id, req.message)
    return ChatResponse(session_id=session_id, status="started")


@app.get("/stream/{session_id}")
async def stream(session_id: str):
    if session_id not in _sse_queues:
        raise HTTPException(status_code=404, detail="Session not found")

    queue = _sse_queues[session_id]

    async def _generator() -> AsyncGenerator[str, None]:
        while True:
            item = await queue.get()
            if item is None:
                yield 'data: {"type": "stream_end"}\n\n'
                break
            yield f"data: {item}\n\n"

    return StreamingResponse(
        _generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/sessions")
async def sessions():
    """List all sessions (newest first) with metadata."""
    return get_all_sessions()


@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """All agent run log entries for a session — structured input/output per stage."""
    return get_agent_run_history(session_id)


@app.get("/state/{session_id}")
async def get_state(session_id: str):
    snapshot = load_state_snapshot(session_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return snapshot


@app.get("/health")
async def health():
    return {"status": "ok"}
