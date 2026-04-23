"""Tests for the Front Desk agent and extract_repo_info tool."""
import pytest
from app.tools.extract_repo_info import extract_repo_info
from app.agents.front_desk import front_desk_node


class TestExtractRepoInfo:
    def test_extracts_github_url(self):
        result = extract_repo_info("Bug in https://github.com/owner/repo – NullPointerException")
        assert result["repo_url"] == "https://github.com/owner/repo"

    def test_extracts_file_path(self):
        result = extract_repo_info("Error in src/auth/login.py line 42")
        assert result["file_path"] == "src/auth/login.py"

    def test_extracts_error_description(self):
        result = extract_repo_info("SQL injection found in app/db.py")
        assert "SQL injection" in result["error_description"]

    def test_no_url_returns_none(self):
        result = extract_repo_info("Just a plain error message with no URL")
        assert result["repo_url"] is None

    def test_git_url_normalised(self):
        result = extract_repo_info("https://github.com/owner/repo.git is broken")
        assert result["repo_url"] == "https://github.com/owner/repo"

    def test_multiple_file_paths_picks_longest(self):
        result = extract_repo_info("src/a.py and src/components/auth/login.py are affected")
        assert result["file_path"] == "src/components/auth/login.py"

    def test_empty_message(self):
        result = extract_repo_info("")
        assert result["repo_url"] is None
        assert result["file_path"] is None

    def test_message_with_only_url(self):
        result = extract_repo_info("https://github.com/foo/bar")
        assert result["repo_url"] == "https://github.com/foo/bar"


class TestFrontDeskNode:
    def test_populates_state(self, base_state):
        state = {**base_state, "user_message": "Bug in https://github.com/owner/repo at app/db.py"}
        result = front_desk_node(state)
        assert result["repo_url"] == "https://github.com/owner/repo"
        assert result["file_path"] == "app/db.py"

    def test_does_not_overwrite_existing_repo_url(self, base_state):
        state = {**base_state, "repo_url": "https://github.com/existing/repo"}
        result = front_desk_node(state)
        assert result["repo_url"] == "https://github.com/existing/repo"

    def test_session_id_preserved(self, base_state):
        result = front_desk_node(base_state)
        assert result["session_id"] == "test-session-123"
