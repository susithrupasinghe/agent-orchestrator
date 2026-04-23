"""Redis persistence for agent run history and already-run tracking."""
import json
import os
import time
from datetime import datetime, timezone

import redis

_pool: redis.ConnectionPool | None = None


def _get_redis() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True,
        )
    return redis.Redis(connection_pool=_pool)


def register_session(session_id: str, user_message: str) -> None:
    """Register a new session in the global sessions index."""
    r = _get_redis()
    meta = {
        "session_id": session_id,
        "user_message": user_message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    r.set(f"session:{session_id}:meta", json.dumps(meta))
    # Sorted set keyed by unix timestamp so we can list sessions newest-first
    r.zadd("all_sessions", {session_id: time.time()})


def get_all_sessions() -> list[dict]:
    """Return metadata for all sessions, newest first."""
    r = _get_redis()
    session_ids = r.zrevrange("all_sessions", 0, -1)
    sessions = []
    for sid in session_ids:
        raw = r.get(f"session:{sid}:meta")
        if raw:
            meta = json.loads(raw)
            # Attach agent count from logs length
            meta["agent_count"] = r.llen(f"session:{sid}:logs")
            sessions.append(meta)
    return sessions


def log_agent_run(
    session_id: str,
    agent: str,
    input_data: dict,
    tool_calls: list[dict],
    output: dict,
) -> None:
    """Append a structured log entry to session:{id}:logs."""
    r = _get_redis()
    entry = {
        "agent": agent,
        "input": input_data,
        "tool_calls": tool_calls,
        "output": output,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    r.rpush(f"session:{session_id}:logs", json.dumps(entry))
    r.sadd(f"session:{session_id}:agents_run", agent)


def get_agent_run_history(session_id: str) -> list[dict]:
    """Return all log entries for a session."""
    r = _get_redis()
    raw = r.lrange(f"session:{session_id}:logs", 0, -1)
    return [json.loads(x) for x in raw]


def get_agents_already_run(session_id: str) -> set[str]:
    """Return the set of agent names that have already run in this session."""
    r = _get_redis()
    return r.smembers(f"session:{session_id}:agents_run")


def save_state_snapshot(session_id: str, state: dict) -> None:
    """Persist latest full state for /state endpoint."""
    r = _get_redis()
    r.set(f"session:{session_id}:state", json.dumps(state))


def load_state_snapshot(session_id: str) -> dict | None:
    r = _get_redis()
    raw = r.get(f"session:{session_id}:state")
    return json.loads(raw) if raw else None
