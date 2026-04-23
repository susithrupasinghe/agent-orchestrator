"""Shared pytest fixtures."""
import pytest
from unittest.mock import MagicMock, patch
from app.state import AgentState


@pytest.fixture
def base_state() -> AgentState:
    return {
        "session_id": "test-session-123",
        "user_message": "There is a SQL injection bug in https://github.com/owner/repo at app/db.py",
        "repo_url": None,
        "file_path": None,
        "error_description": None,
        "code_content": None,
        "security_findings": None,
        "ticket_info": None,
        "final_response": None,
        "messages": [],
        "history": [],
        "next_agent": None,
        "input_subset": [],
        "done": False,
    }


@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    """Patch redis so tests don't need a live Redis instance."""
    fake_redis = MagicMock()
    fake_redis.rpush = MagicMock()
    fake_redis.sadd  = MagicMock()
    fake_redis.lrange = MagicMock(return_value=[])
    fake_redis.smembers = MagicMock(return_value=set())
    fake_redis.set   = MagicMock()
    fake_redis.get   = MagicMock(return_value=None)

    with patch("app.redis_logger._get_redis", return_value=fake_redis):
        yield fake_redis
