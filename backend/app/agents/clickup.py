"""ClickUp Agent – creates a well-structured ticket only when there is real content."""
from app.state import AgentState
from app.tools.create_ticket import create_ticket
from app.redis_logger import log_agent_run


def _determine_priority(findings: list[dict]) -> str:
    if not findings:
        return "normal"
    severities = {f.get("severity") for f in findings}
    if "HIGH" in severities:
        return "urgent"
    if "MEDIUM" in severities:
        return "high"
    return "normal"


def clickup_node(state: AgentState) -> AgentState:
    error_desc = state.get("error_description") or ""
    findings = state.get("security_findings") or []
    repo_url = state.get("repo_url")
    file_path = state.get("file_path")
    priority = _determine_priority(findings)

    # Build a concise title
    if findings:
        top_severity = "HIGH" if any(f.get("severity") == "HIGH" for f in findings) else "MEDIUM"
        title = f"[{top_severity}] Security issues found – {(error_desc or 'code audit')[:60]}"
    else:
        title = f"Bug Report: {error_desc[:80]}"

    ticket = create_ticket(
        title=title,
        description="",  # unused when extended fields are provided
        priority=priority,
        error_description=error_desc or None,
        repo_url=repo_url,
        file_path=file_path,
        findings=findings if findings else None,
    )

    tool_call = {
        "tool": "create_ticket",
        "input": {
            "title": title,
            "priority": priority,
            "findings_count": len(findings),
            "has_repo": repo_url is not None,
        },
        "output": {
            "id": ticket["id"],
            "url": ticket["url"],
            "status": ticket["status"],
        },
    }

    log_agent_run(
        session_id=state["session_id"],
        agent="ClickUp",
        input_data={
            "error_description": error_desc or None,
            "repo_url": repo_url,
            "file_path": file_path,
            "findings_count": len(findings),
            "priority": priority,
        },
        tool_calls=[tool_call],
        output={"ticket_id": ticket["id"], "ticket_url": ticket["url"]},
    )

    return {**state, "ticket_info": ticket}
