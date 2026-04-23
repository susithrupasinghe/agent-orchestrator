"""Tests for the GitHub agent and fetch_code tool."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.tools.fetch_code import fetch_code, get_file_tree, find_relevant_files, clone_or_pull
from app.agents.github_agent import github_node


def _mock_clone(status="cloned"):
    """Patch clone_or_pull to return a temp-dir-like path."""
    fake_dir = MagicMock(spec=Path)
    fake_dir.__truediv__ = lambda self, other: Path(f"/tmp/fake-repo/{other}")
    return fake_dir, status


class TestFetchCode:
    def test_empty_url_returns_failed_result(self, monkeypatch):
        monkeypatch.delenv("GITHUB_REPO_URL", raising=False)
        result = fetch_code("", None)
        assert result["clone_status"] == "failed"
        assert result["code_content"] is None

    def test_invalid_url_returns_failed(self, monkeypatch):
        monkeypatch.delenv("GITHUB_REPO_URL", raising=False)
        result = fetch_code("not-a-url", "README.md")
        assert result["clone_status"] == "failed"

    def test_successful_clone_reads_file(self, tmp_path):
        (tmp_path / "app.py").write_text("import os\nprint('hello')")
        with patch("app.tools.fetch_code.clone_or_pull", return_value=(tmp_path, "cloned")):
            result = fetch_code("https://github.com/owner/repo", "app.py")
        assert result["clone_status"] == "cloned"
        assert "import os" in result["code_content"]
        assert "app.py" in result["files_read"]

    def test_pull_used_on_second_run(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / "main.go").write_text("package main")
        with patch("app.tools.fetch_code.clone_or_pull", return_value=(tmp_path, "pulled")):
            result = fetch_code("https://github.com/owner/repo", "main.go")
        assert result["clone_status"] == "pulled"

    def test_missing_file_returns_no_content(self, tmp_path):
        with patch("app.tools.fetch_code.clone_or_pull", return_value=(tmp_path, "cloned")):
            result = fetch_code("https://github.com/owner/repo", "nonexistent.py")
        assert result["code_content"] is None
        assert result["files_read"] == []

    def test_auto_selects_relevant_files_when_no_path(self, tmp_path):
        (tmp_path / "auth.py").write_text("def login(): pass")
        (tmp_path / "db.py").write_text("def query(): pass")
        with patch("app.tools.fetch_code.clone_or_pull", return_value=(tmp_path, "cloned")):
            result = fetch_code("https://github.com/owner/repo", None, "authentication login bug")
        assert result["code_content"] is not None
        assert len(result["files_read"]) > 0

    def test_env_fallback_used_when_url_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GITHUB_REPO_URL", "https://github.com/fallback/repo")
        (tmp_path / "README.md").write_text("# Hello")
        with patch("app.tools.fetch_code.clone_or_pull", return_value=(tmp_path, "cloned")):
            result = fetch_code("", "README.md")
        assert result["clone_status"] == "cloned"

    def test_file_tree_returned(self, tmp_path):
        (tmp_path / "a.py").write_text("x=1")
        (tmp_path / "b.py").write_text("y=2")
        with patch("app.tools.fetch_code.clone_or_pull", return_value=(tmp_path, "cloned")):
            result = fetch_code("https://github.com/owner/repo", None)
        assert isinstance(result["file_tree"], list)


class TestGetFileTree:
    def test_returns_source_files(self, tmp_path):
        (tmp_path / "main.py").write_text("x=1")
        (tmp_path / "skip.txt").write_text("x=1")
        tree = get_file_tree(tmp_path)
        assert "main.py" in tree
        assert "skip.txt" not in tree

    def test_excludes_node_modules(self, tmp_path):
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "lib.js").write_text("x=1")
        tree = get_file_tree(tmp_path)
        assert not any("node_modules" in f for f in tree)


class TestFindRelevantFiles:
    def test_scores_by_keyword_match(self, tmp_path):
        files = ["auth/login.py", "db/query.py", "utils/helpers.py"]
        result = find_relevant_files(tmp_path, files, "authentication login failed")
        assert "auth/login.py" in result

    def test_fallback_when_no_keywords(self, tmp_path):
        files = ["a.py", "b.py", "c.py"]
        result = find_relevant_files(tmp_path, files, None)
        assert len(result) > 0


class TestGithubNode:
    def test_stores_code_and_metadata_in_state(self, base_state, tmp_path):
        (tmp_path / "app.py").write_text("import os")
        state = {**base_state, "repo_url": "https://github.com/owner/repo", "file_path": "app.py"}
        with patch("app.tools.fetch_code.clone_or_pull", return_value=(tmp_path, "cloned")):
            result = github_node(state)
        assert result["code_content"] == "import os"
        assert result["clone_status"] == "cloned"
        assert result["repo_local_path"] is not None
        assert isinstance(result["repo_file_tree"], list)

    def test_failed_clone_sets_none_content(self, base_state, monkeypatch):
        monkeypatch.delenv("GITHUB_REPO_URL", raising=False)
        result = github_node({**base_state, "repo_url": ""})
        assert result["code_content"] is None
        assert result["clone_status"] == "failed"
