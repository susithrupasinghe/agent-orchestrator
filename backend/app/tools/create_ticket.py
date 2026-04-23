"""Tool: real ClickUp task creation via the ClickUp REST API v2."""
import os
import time

import httpx

CLICKUP_API_BASE = "https://api.clickup.com/api/v2"

PRIORITY_MAP = {"urgent": 1, "high": 2, "normal": 3, "low": 4}


def _build_description(
    error_description: str | None,
    repo_url: str | None,
    file_path: str | None,
    findings: list[dict],
) -> str:
    """Build a clean markdown description – only include sections with actual data."""
    sections = []

    if error_description:
        sections.append(f"## Problem Description\n{error_description}")

    context_lines = []
    if repo_url:
        context_lines.append(f"- **Repository:** {repo_url}")
    if file_path:
        context_lines.append(f"- **File:** `{file_path}`")
    if context_lines:
        sections.append("## Context\n" + "\n".join(context_lines))

    if findings:
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        sorted_findings = sorted(findings, key=lambda f: severity_order.get(f.get("severity", "LOW"), 2))

        rows = ["| Severity | Category | Description | Line |", "|----------|----------|-------------|------|"]
        for f in sorted_findings:
            rows.append(
                f"| {f.get('severity', '-')} | {f.get('rule_category', '-')} "
                f"| {f.get('description', '-')} | {f.get('line_number', '-')} |"
            )
        sections.append(f"## Security Findings ({len(findings)} issue(s))\n" + "\n".join(rows))

    return "\n\n".join(sections)


def create_ticket(
    title: str,
    description: str,
    priority: str = "normal",
    # Extended fields passed through from the ClickUp agent
    error_description: str | None = None,
    repo_url: str | None = None,
    file_path: str | None = None,
    findings: list[dict] | None = None,
) -> dict:
    """
    Create a task in ClickUp under the configured list.

    Reads CLICKUP_API_KEY and CLICKUP_LIST_ID from environment variables.
    Raises RuntimeError if credentials are missing or the API call fails.
    """
    api_key = os.getenv("CLICKUP_API_KEY")
    list_id = os.getenv("CLICKUP_LIST_ID")

    if not api_key or not list_id:
        raise RuntimeError("CLICKUP_API_KEY and CLICKUP_LIST_ID must be set.")

    priority_num = PRIORITY_MAP.get(priority.lower(), 3)

    # Build rich description if extended fields are provided, else use raw description
    if error_description or findings:
        final_description = _build_description(
            error_description=error_description,
            repo_url=repo_url,
            file_path=file_path,
            findings=findings or [],
        )
    else:
        final_description = description

    payload: dict = {
        "name": title,
        "priority": priority_num,
    }
    if final_description:
        payload["description"] = final_description

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }

    resp = httpx.post(
        f"{CLICKUP_API_BASE}/list/{list_id}/task",
        json=payload,
        headers=headers,
        timeout=15,
    )

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"ClickUp API error {resp.status_code}: {resp.text}")

    data = resp.json()

    return {
        "id": data.get("id", ""),
        "url": data.get("url", f"https://app.clickup.com/t/{data.get('id', '')}"),
        "title": data.get("name", title),
        "priority": priority,
        "priority_num": priority_num,
        "status": data.get("status", {}).get("status", "open"),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
