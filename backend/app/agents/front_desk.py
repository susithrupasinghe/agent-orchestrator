"""Front Desk Agent – extracts structured info from the user message."""
import os
from app.state import AgentState
from app.tools.extract_repo_info import extract_repo_info
from app.redis_logger import log_agent_run


def front_desk_node(state: AgentState) -> AgentState:
    """
    Parses the user message to extract repo URL, file path, and error description.
    If no repo URL is found in the message, notes that the env-var fallback is available.
    """
    message = state.get("user_message", "")
    extracted = extract_repo_info(message)

    fallback_repo = os.getenv("GITHUB_REPO_URL", "")
    repo_url = state.get("repo_url") or extracted.get("repo_url") or fallback_repo or None
    file_path = state.get("file_path") or extracted.get("file_path")
    error_description = state.get("error_description") or extracted.get("error_description")

    tool_call = {
        "tool": "extract_repo_info",
        "input": {"message": message},
        "output": {
            "repo_url_from_message": extracted.get("repo_url"),
            "repo_url_resolved": repo_url,
            "file_path": file_path,
            "error_description": error_description,
            "fallback_repo_used": bool(
                not extracted.get("repo_url") and fallback_repo and repo_url == fallback_repo
            ),
        },
    }

    updates: AgentState = {
        "repo_url": repo_url,
        "file_path": file_path,
        "error_description": error_description,
    }

    log_agent_run(
        session_id=state["session_id"],
        agent="FrontDesk",
        input_data={"user_message": message},
        tool_calls=[tool_call],
        output=updates,
    )

    return {**state, **updates}
