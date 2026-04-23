"""Security Auditor Agent – rule-based scan, no LLM."""
from app.state import AgentState
from app.tools.scan_code import scan_code
from app.redis_logger import log_agent_run


def security_node(state: AgentState) -> AgentState:
    """
    Runs the rule-based security scanner on code_content.
    Groups findings by severity so downstream agents have a clear picture.
    """
    code = state.get("code_content")
    files_read = state.get("repo_file_tree", [])  # for context in logs
    findings = scan_code(code)

    # Group by severity for the log output
    by_severity: dict[str, list] = {"HIGH": [], "MEDIUM": [], "LOW": []}
    for f in findings:
        by_severity.setdefault(f.get("severity", "LOW"), []).append(f)

    tool_call = {
        "tool": "scan_code",
        "input": {
            "code_length": len(code) if code else 0,
            "files_in_repo": len(state.get("repo_file_tree") or []),
        },
        "output": {
            "total_findings": len(findings),
            "high": len(by_severity["HIGH"]),
            "medium": len(by_severity["MEDIUM"]),
            "low": len(by_severity["LOW"]),
            "findings": findings,
        },
    }

    log_agent_run(
        session_id=state["session_id"],
        agent="Security",
        input_data={
            "code_length": len(code) if code else 0,
            "clone_status": state.get("clone_status"),
            "repo_file_count": len(state.get("repo_file_tree") or []),
        },
        tool_calls=[tool_call],
        output={
            "total_findings": len(findings),
            "high": len(by_severity["HIGH"]),
            "medium": len(by_severity["MEDIUM"]),
            "low": len(by_severity["LOW"]),
            "top_findings": findings[:5],
        },
    )

    return {**state, "security_findings": findings}
