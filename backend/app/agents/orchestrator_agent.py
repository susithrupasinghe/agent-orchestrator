"""Orchestrator Agent – hybrid rule-based routing + LLM for the ClickUp judgment call."""
import json
import os
import re
from app.state import AgentState
from app.llm_client import chat_completion
from app.redis_logger import get_agents_already_run, log_agent_run

# ── LLM prompt used ONLY for the ClickUp judgment call ───────────────────────
_CLICKUP_PROMPT = """You are deciding whether to create a ClickUp support ticket for a bug/security report.

Answer with ONLY one of these two JSON objects — nothing else:

Create a ticket:
{"create_ticket": true}

Do not create a ticket:
{"create_ticket": false}

Create a ticket only when there is something concrete and actionable:
- There are actual security findings (vulnerabilities found in the code), OR
- The user described a specific, reproducible bug with enough detail to act on.

Do NOT create a ticket when:
- No security issues were found AND the description is vague or generic.
- The user was just asking a general question with no specific problem.
- There is no useful information to put in the ticket.
"""


def _ask_llm_for_clickup(state: AgentState) -> bool:
    """Ask the LLM the single yes/no question: should we create a ClickUp ticket?"""
    findings = state.get("security_findings") or []
    error_desc = state.get("error_description") or ""

    context = {
        "error_description": error_desc[:300],
        "security_findings_count": len(findings),
        "top_findings": [
            {"severity": f.get("severity"), "description": f.get("description")}
            for f in findings[:5]
        ],
    }

    messages = [
        {"role": "system", "content": _CLICKUP_PROMPT},
        {"role": "user", "content": f"Report context:\n{json.dumps(context, indent=2)}"},
    ]

    try:
        raw = chat_completion(messages, temperature=0.0)
        raw = re.sub(r"```(?:json)?", "", raw).strip()
        match = re.search(r"\{.*?\}", raw, re.DOTALL)
        if match:
            return bool(json.loads(match.group()).get("create_ticket", False))
    except Exception:
        pass

    # Fallback: create ticket if there are findings or a substantial description
    return len(findings) > 0 or len(error_desc) > 40


# ── Rule-based routing ────────────────────────────────────────────────────────

def _decide(state: AgentState, already_run: set[str]) -> tuple[str | None, list[str], bool]:
    """
    Returns (next_agent, input_subset, done).

    Rules applied in order — the LLM is only called for the ClickUp decision.
    """
    repo_url = state.get("repo_url") or os.getenv("GITHUB_REPO_URL", "")

    # 1. FrontDesk always runs first — extracts structure from the user message
    if "FrontDesk" not in already_run:
        return "FrontDesk", ["user_message"], False

    # 2. GitHub runs whenever a repo URL is available (from message or env fallback)
    if repo_url and "GitHub" not in already_run:
        return "GitHub", ["repo_url", "file_path", "error_description"], False

    # 3. Security runs whenever we have code to scan
    if state.get("code_content") and "Security" not in already_run:
        return "Security", ["code_content"], False

    # 4. ClickUp — ask the LLM whether a ticket is warranted
    if "ClickUp" not in already_run:
        should_create = _ask_llm_for_clickup(state)
        if should_create:
            return "ClickUp", [
                "error_description", "repo_url", "file_path",
                "security_findings", "clone_status",
            ], False

    # 5. All done
    return None, [], True


# ── Node ─────────────────────────────────────────────────────────────────────

def orchestrator_node(state: AgentState) -> AgentState:
    session_id = state["session_id"]
    already_run: set[str] = get_agents_already_run(session_id)

    next_agent, input_subset, done = _decide(state, already_run)

    repo_url = state.get("repo_url") or os.getenv("GITHUB_REPO_URL", "")
    state_summary = {
        "user_message_preview": (state.get("user_message") or "")[:120],
        "repo_url": repo_url or None,
        "file_path": state.get("file_path"),
        "error_description": (state.get("error_description") or "")[:200],
        "clone_status": state.get("clone_status"),
        "code_available": state.get("code_content") is not None,
        "repo_file_count": len(state.get("repo_file_tree") or []),
        "security_findings_count": len(state.get("security_findings") or []),
        "has_ticket": state.get("ticket_info") is not None,
        "already_run": list(already_run),
        "decision": {"next_agent": next_agent, "done": done},
    }

    log_agent_run(
        session_id=session_id,
        agent="Orchestrator",
        input_data={
            "already_run": list(already_run),
            "code_available": state.get("code_content") is not None,
            "findings_count": len(state.get("security_findings") or []),
            "repo_url": repo_url or None,
        },
        tool_calls=[],
        output={"next_agent": next_agent, "done": done},
    )

    return {
        **state,
        "next_agent": next_agent,
        "input_subset": input_subset,
        "done": done,
    }
