"""Tests for the orchestrator agent – mocks the LLM."""
import json
import pytest
from unittest.mock import patch
from app.agents.orchestrator_agent import orchestrator_node, _extract_json


class TestExtractJson:
    def test_clean_json(self):
        result = _extract_json('{"next_agent": "FrontDesk", "input_subset": [], "done": false}')
        assert result["next_agent"] == "FrontDesk"

    def test_json_inside_markdown(self):
        text = "```json\n{\"next_agent\": \"GitHub\", \"input_subset\": [], \"done\": false}\n```"
        result = _extract_json(text)
        assert result["next_agent"] == "GitHub"

    def test_raises_on_no_json(self):
        with pytest.raises(ValueError):
            _extract_json("This has no JSON at all.")


class TestOrchestratorNode:
    def test_routes_to_front_desk_first(self, base_state):
        llm_response = json.dumps({
            "next_agent": "FrontDesk",
            "input_subset": ["user_message"],
            "done": False,
        })
        with patch("app.agents.orchestrator_agent.chat_completion", return_value=llm_response):
            result = orchestrator_node(base_state)
        assert result["next_agent"] == "FrontDesk"
        assert result["done"] is False

    def test_sets_done_when_llm_says_so(self, base_state):
        llm_response = json.dumps({
            "next_agent": None,
            "input_subset": [],
            "done": True,
        })
        with patch("app.agents.orchestrator_agent.chat_completion", return_value=llm_response):
            result = orchestrator_node(base_state)
        assert result["done"] is True
        assert result["next_agent"] is None

    def test_fallback_on_unparseable_llm_output(self, base_state):
        with patch("app.agents.orchestrator_agent.chat_completion", return_value="garbage output"):
            result = orchestrator_node(base_state)
        assert result["done"] is True  # safe fallback

    def test_input_subset_stored_in_state(self, base_state):
        llm_response = json.dumps({
            "next_agent": "GitHub",
            "input_subset": ["repo_url", "file_path"],
            "done": False,
        })
        with patch("app.agents.orchestrator_agent.chat_completion", return_value=llm_response):
            result = orchestrator_node(base_state)
        assert "repo_url" in result["input_subset"]

    def test_session_id_preserved(self, base_state):
        llm_response = json.dumps({"next_agent": "Security", "input_subset": [], "done": False})
        with patch("app.agents.orchestrator_agent.chat_completion", return_value=llm_response):
            result = orchestrator_node(base_state)
        assert result["session_id"] == "test-session-123"
