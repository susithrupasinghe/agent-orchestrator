"""Tests for the ClickUp agent and create_ticket tool."""
import pytest
from unittest.mock import patch, MagicMock
from app.tools.create_ticket import create_ticket
from app.agents.clickup import clickup_node


def _mock_clickup_response(task_id="abc123", status="open"):
    """Build a fake httpx response that looks like a ClickUp API success."""
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {
        "id": task_id,
        "url": f"https://app.clickup.com/t/{task_id}",
        "name": "Test bug",
        "status": {"status": status},
    }
    return mock_resp


@pytest.fixture(autouse=True)
def clickup_env(monkeypatch):
    """Inject required env vars for every test in this module."""
    monkeypatch.setenv("CLICKUP_API_KEY", "pk_test_fake_key")
    monkeypatch.setenv("CLICKUP_LIST_ID", "901817612256")


class TestCreateTicket:
    def test_returns_dict_with_required_keys(self):
        with patch("app.tools.create_ticket.httpx.post", return_value=_mock_clickup_response()):
            ticket = create_ticket("Test bug", "Description here", "normal")
        assert "id" in ticket
        assert "url" in ticket
        assert "title" in ticket
        assert "priority" in ticket
        assert "status" in ticket
        assert "created_at" in ticket

    def test_id_comes_from_api_response(self):
        with patch("app.tools.create_ticket.httpx.post", return_value=_mock_clickup_response("xyz999")):
            ticket = create_ticket("Bug", "Desc")
        assert ticket["id"] == "xyz999"

    def test_url_contains_id(self):
        with patch("app.tools.create_ticket.httpx.post", return_value=_mock_clickup_response("tid1")):
            ticket = create_ticket("Bug", "Desc")
        assert "tid1" in ticket["url"]

    def test_priority_urgent_sends_1_to_api(self):
        with patch("app.tools.create_ticket.httpx.post", return_value=_mock_clickup_response()) as mock_post:
            create_ticket("Critical", "Desc", "urgent")
        called_payload = mock_post.call_args.kwargs["json"]
        assert called_payload["priority"] == 1

    def test_priority_low_sends_4_to_api(self):
        with patch("app.tools.create_ticket.httpx.post", return_value=_mock_clickup_response()) as mock_post:
            create_ticket("Low", "Desc", "low")
        assert mock_post.call_args.kwargs["json"]["priority"] == 4

    def test_unknown_priority_defaults_to_3(self):
        with patch("app.tools.create_ticket.httpx.post", return_value=_mock_clickup_response()) as mock_post:
            create_ticket("Bug", "Desc", "unknown")
        assert mock_post.call_args.kwargs["json"]["priority"] == 3

    def test_long_description_truncated_in_return(self):
        with patch("app.tools.create_ticket.httpx.post", return_value=_mock_clickup_response()):
            ticket = create_ticket("Bug", "x" * 1000)
        assert len(ticket["description"]) <= 500

    def test_api_error_raises_runtime_error(self):
        bad_resp = MagicMock()
        bad_resp.status_code = 401
        bad_resp.text = "Unauthorized"
        with patch("app.tools.create_ticket.httpx.post", return_value=bad_resp):
            with pytest.raises(RuntimeError, match="ClickUp API error 401"):
                create_ticket("Bug", "Desc")

    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("CLICKUP_API_KEY")
        with pytest.raises(RuntimeError, match="CLICKUP_API_KEY"):
            create_ticket("Bug", "Desc")

    def test_missing_list_id_raises(self, monkeypatch):
        monkeypatch.delenv("CLICKUP_LIST_ID")
        with pytest.raises(RuntimeError, match="CLICKUP_LIST_ID"):
            create_ticket("Bug", "Desc")

    def test_correct_list_id_used_in_url(self):
        with patch("app.tools.create_ticket.httpx.post", return_value=_mock_clickup_response()) as mock_post:
            create_ticket("Bug", "Desc")
        called_url = mock_post.call_args.args[0]
        assert "901817612256" in called_url


class TestClickUpNode:
    def test_creates_ticket_in_state(self, base_state):
        state = {
            **base_state,
            "error_description": "SQL injection found",
            "security_findings": [
                {"severity": "HIGH", "description": "SQL injection", "line_number": 5, "line_content": "..."}
            ],
        }
        with patch("app.tools.create_ticket.httpx.post", return_value=_mock_clickup_response("ticket-001")):
            result = clickup_node(state)
        assert result["ticket_info"] is not None
        assert result["ticket_info"]["id"] == "ticket-001"

    def test_urgent_priority_for_high_severity(self, base_state):
        state = {
            **base_state,
            "security_findings": [
                {"severity": "HIGH", "description": "Hardcoded password", "line_number": 1, "line_content": "x"}
            ],
        }
        with patch("app.tools.create_ticket.httpx.post", return_value=_mock_clickup_response()) as mock_post:
            result = clickup_node(state)
        assert result["ticket_info"]["priority"] == "urgent"
        assert mock_post.call_args.kwargs["json"]["priority"] == 1

    def test_normal_priority_when_no_findings(self, base_state):
        state = {**base_state, "security_findings": []}
        with patch("app.tools.create_ticket.httpx.post", return_value=_mock_clickup_response()) as mock_post:
            clickup_node(state)
        assert mock_post.call_args.kwargs["json"]["priority"] == 3
