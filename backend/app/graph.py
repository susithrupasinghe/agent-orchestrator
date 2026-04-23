"""LangGraph state machine: dynamic orchestration of all agents."""
from langgraph.graph import StateGraph, END

from app.state import AgentState
from app.agents import (
    orchestrator_node,
    front_desk_node,
    github_node,
    security_node,
    clickup_node,
)

# ── Router ───────────────────────────────────────────────────────────────────

def _route_from_orchestrator(state: AgentState) -> str:
    """After the orchestrator runs, decide which node to go to next."""
    if state.get("done"):
        return END
    next_agent = state.get("next_agent")
    mapping = {
        "FrontDesk": "FrontDesk",
        "GitHub": "GitHub",
        "Security": "Security",
        "ClickUp": "ClickUp",
    }
    return mapping.get(next_agent, END)


# ── Graph construction ───────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    g.add_node("orchestrator", orchestrator_node)
    g.add_node("FrontDesk", front_desk_node)
    g.add_node("GitHub", github_node)
    g.add_node("Security", security_node)
    g.add_node("ClickUp", clickup_node)

    # Entry point
    g.set_entry_point("orchestrator")

    # After orchestrator: dynamic branch
    g.add_conditional_edges(
        "orchestrator",
        _route_from_orchestrator,
        {
            "FrontDesk": "FrontDesk",
            "GitHub": "GitHub",
            "Security": "Security",
            "ClickUp": "ClickUp",
            END: END,
        },
    )

    # Every worker loops back to orchestrator
    for worker in ("FrontDesk", "GitHub", "Security", "ClickUp"):
        g.add_edge(worker, "orchestrator")

    return g.compile()


# Singleton compiled graph
compiled_graph = build_graph()
