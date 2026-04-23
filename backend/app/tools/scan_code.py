"""Tool: rule-based security scanner (no LLM)."""
import re
from typing import Optional

# ── Rule definitions ────────────────────────────────────────────────────────

SECRET_PATTERNS: list[tuple[str, str]] = [
    (r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{3,}["\']', "Hardcoded password"),
    (r'(?i)(api_key|apikey|secret_key)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded API key"),
    (r'(?i)(token)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded token"),
    (r'(?i)aws_access_key_id\s*=\s*["\']?[A-Z0-9]{20}["\']?', "AWS access key"),
    (r'(?i)aws_secret_access_key\s*=\s*["\']?[A-Za-z0-9/+=]{40}["\']?', "AWS secret key"),
    (r'(?i)(private_key|rsa_key)\s*=\s*["\']-----BEGIN', "Private key material"),
]

SQL_INJECTION_PATTERNS: list[tuple[str, str]] = [
    (r'execute\s*\(\s*["\']?\s*SELECT.*\+', "SQL injection via string concatenation"),
    (r'execute\s*\(\s*f["\'].*SELECT', "SQL injection via f-string"),
    (r'cursor\.execute\([^,)]*%[^,)]*\)', "SQL injection via %-formatting"),
    (r'\.format\(.*\).*WHERE', "SQL injection via .format()"),
    (r'(?i)query\s*=\s*["\'].*SELECT.*["\']\s*\+', "SQL injection via concatenated query"),
]

XSS_PATTERNS: list[tuple[str, str]] = [
    (r'innerHTML\s*=\s*[^"\'`]', "Potential XSS via innerHTML assignment"),
    (r'document\.write\(', "Potential XSS via document.write"),
    (r'eval\s*\(', "Dangerous eval() call"),
]

INSECURE_FUNCTION_PATTERNS: list[tuple[str, str]] = [
    (r'\bpickle\.loads?\b', "Insecure deserialization with pickle"),
    (r'\bos\.system\s*\(', "Shell injection risk via os.system"),
    (r'\bsubprocess\.call\([^)]*shell\s*=\s*True', "Shell injection via subprocess shell=True"),
    (r'\bexec\s*\(', "Dynamic code execution with exec()"),
    (r'yaml\.load\s*\([^)]*Loader', "Insecure YAML load (use safe_load)"),
    (r'yaml\.load\s*\([^)]*\)', "Insecure YAML load (use safe_load)"),
    (r'MD5\s*\(|hashlib\.md5', "Weak hashing algorithm MD5"),
    (r'SHA1\s*\(|hashlib\.sha1', "Weak hashing algorithm SHA1"),
]

ALL_RULES = [
    ("SECRET", SECRET_PATTERNS),
    ("SQL_INJECTION", SQL_INJECTION_PATTERNS),
    ("XSS", XSS_PATTERNS),
    ("INSECURE_FUNCTION", INSECURE_FUNCTION_PATTERNS),
]


def scan_code(code: Optional[str]) -> list[dict]:
    """
    Scan code string for security issues.

    Returns a list of findings, each with:
      - rule_category: str
      - description: str
      - line_number: int
      - line_content: str
      - severity: "HIGH" | "MEDIUM" | "LOW"
    """
    if not code:
        return []

    findings: list[dict] = []
    lines = code.splitlines()

    severity_map = {
        "SECRET": "HIGH",
        "SQL_INJECTION": "HIGH",
        "XSS": "MEDIUM",
        "INSECURE_FUNCTION": "MEDIUM",
    }

    for category, rules in ALL_RULES:
        for pattern, description in rules:
            compiled = re.compile(pattern)
            for lineno, line in enumerate(lines, start=1):
                if compiled.search(line):
                    findings.append({
                        "rule_category": category,
                        "description": description,
                        "line_number": lineno,
                        "line_content": line.strip(),
                        "severity": severity_map.get(category, "LOW"),
                    })

    return findings
