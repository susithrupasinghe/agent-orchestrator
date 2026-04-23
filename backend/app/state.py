"""Shared state definition for the multi-agent system."""
from typing import Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    session_id: str
    user_message: str
    repo_url: Optional[str]
    file_path: Optional[str]
    error_description: Optional[str]
    # Set by GitHub agent
    code_content: Optional[str]          # content of the specific file (or best-match files)
    repo_local_path: Optional[str]       # local path of the cloned repo
    repo_file_tree: Optional[list[str]]  # flat list of repo files (for context)
    clone_status: Optional[str]          # "cloned" | "pulled" | "failed"
    # Set by Security agent
    security_findings: Optional[list[dict]]
    # Set by ClickUp agent
    ticket_info: Optional[dict]
    final_response: Optional[str]
    messages: list[dict]
    history: list[dict]
    # Orchestrator bookkeeping
    next_agent: Optional[str]
    input_subset: Optional[list[str]]
    done: bool
