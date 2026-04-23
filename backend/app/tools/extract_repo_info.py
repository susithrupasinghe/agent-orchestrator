"""Tool: extract structured info from a user bug/security report message."""
import re
from typing import Optional


def extract_repo_info(message: str) -> dict:
    """
    Parse the user message to pull out repo URL, file path, and error description.

    Returns a dict with keys: repo_url, file_path, error_description.
    Any field not found is None.
    """
    result: dict = {
        "repo_url": None,
        "file_path": None,
        "error_description": None,
    }

    # GitHub repo URL pattern (https://github.com/owner/repo or git@ form)
    github_pattern = r"https?://github\.com/[\w\-\.]+/[\w\-\.]+"
    urls = re.findall(github_pattern, message, re.IGNORECASE)
    if urls:
        # Strip trailing slashes / .git
        result["repo_url"] = urls[0].rstrip("/").removesuffix(".git")

    # File path pattern – anything ending with a known extension
    file_pattern = r"[\w/\-\.]+\.(?:py|js|ts|java|go|rb|php|c|cpp|cs|rs|sh)"
    files = re.findall(file_pattern, message)
    if files:
        # Prefer longer (more qualified) paths
        result["file_path"] = max(files, key=len)

    # Error description: everything that is not the URL / file path
    desc = message
    if result["repo_url"]:
        desc = desc.replace(result["repo_url"], "")
    if result["file_path"]:
        desc = desc.replace(result["file_path"], "")
    desc = desc.strip()
    result["error_description"] = desc if desc else message.strip()

    return result
