"""GitHub Agent – clones (or pulls) the repo and reads relevant code."""
import os
from app.state import AgentState
from app.tools.fetch_code import fetch_code
from app.redis_logger import log_agent_run


def github_node(state: AgentState) -> AgentState:
    """
    Clones the target repo on first call, does git-pull on repeat calls.
    Reads the specific file if file_path is given; otherwise auto-selects
    the most relevant source files based on the error description.
    """
    repo_url = state.get("repo_url") or os.getenv("GITHUB_REPO_URL", "")
    file_path = state.get("file_path")
    error_description = state.get("error_description")

    result = fetch_code(repo_url, file_path, error_description)

    clone_status = result.get("clone_status", "failed")
    files_read = result.get("files_read", [])
    file_tree = result.get("file_tree", [])
    code_content = result.get("code_content")

    tool_call = {
        "tool": "fetch_code",
        "input": {
            "repo_url": repo_url,
            "file_path": file_path or "(auto-detect)",
            "error_description": (error_description or "")[:120],
        },
        "output": {
            "clone_status": clone_status,
            "files_read": files_read,
            "total_files_in_repo": len(file_tree),
            "code_content_chars": len(code_content) if code_content else 0,
        },
    }

    log_agent_run(
        session_id=state["session_id"],
        agent="GitHub",
        input_data={
            "repo_url": repo_url,
            "file_path": file_path,
            "error_description": (error_description or "")[:120],
        },
        tool_calls=[tool_call],
        output={
            "clone_status": clone_status,
            "files_read": files_read,
            "repo_local_path": result.get("repo_local_path"),
            "total_repo_files": len(file_tree),
            "code_available": code_content is not None,
        },
    )

    return {
        **state,
        "code_content": code_content,
        "repo_local_path": result.get("repo_local_path"),
        "repo_file_tree": file_tree,
        "clone_status": clone_status,
    }
