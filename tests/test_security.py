"""Tests for the Security Auditor agent and scan_code tool."""
import pytest
from app.tools.scan_code import scan_code
from app.agents.security import security_node


class TestScanCode:
    def test_empty_code_returns_no_findings(self):
        assert scan_code("") == []

    def test_none_returns_no_findings(self):
        assert scan_code(None) == []

    def test_detects_hardcoded_password(self):
        code = 'password = "super_secret_123"'
        findings = scan_code(code)
        assert any(f["rule_category"] == "SECRET" for f in findings)
        assert any("password" in f["description"].lower() for f in findings)

    def test_detects_sql_injection_concatenation(self):
        code = 'cursor.execute("SELECT * FROM users WHERE id = " + user_id)'
        findings = scan_code(code)
        assert any(f["rule_category"] == "SQL_INJECTION" for f in findings)

    def test_detects_sql_injection_fstring(self):
        code = 'db.execute(f"SELECT * FROM {table} WHERE name = {name}")'
        findings = scan_code(code)
        assert any(f["rule_category"] == "SQL_INJECTION" for f in findings)

    def test_detects_eval(self):
        code = "eval(user_input)"
        findings = scan_code(code)
        assert any(f["rule_category"] == "INSECURE_FUNCTION" for f in findings)

    def test_detects_os_system(self):
        code = "os.system(cmd)"
        findings = scan_code(code)
        assert any(f["rule_category"] == "INSECURE_FUNCTION" for f in findings)

    def test_detects_pickle(self):
        code = "data = pickle.loads(raw_bytes)"
        findings = scan_code(code)
        assert any("pickle" in f["description"].lower() for f in findings)

    def test_detects_xss_innerhtml(self):
        code = "element.innerHTML = userInput"
        findings = scan_code(code)
        assert any(f["rule_category"] == "XSS" for f in findings)

    def test_severity_high_for_sql(self):
        code = 'cursor.execute("SELECT * FROM users WHERE id = " + uid)'
        findings = scan_code(code)
        sql_findings = [f for f in findings if f["rule_category"] == "SQL_INJECTION"]
        assert all(f["severity"] == "HIGH" for f in sql_findings)

    def test_clean_code_returns_no_findings(self):
        code = """
def add(a, b):
    return a + b

result = add(1, 2)
print(result)
"""
        assert scan_code(code) == []

    def test_finding_includes_line_number(self):
        code = "x = 1\npassword = 'abc123'\ny = 3"
        findings = scan_code(code)
        secret_findings = [f for f in findings if f["rule_category"] == "SECRET"]
        assert any(f["line_number"] == 2 for f in secret_findings)


class TestSecurityNode:
    def test_populates_security_findings(self, base_state):
        state = {**base_state, "code_content": 'password = "hunter2"'}
        result = security_node(state)
        assert isinstance(result["security_findings"], list)
        assert len(result["security_findings"]) > 0

    def test_empty_findings_for_clean_code(self, base_state):
        state = {**base_state, "code_content": "x = 1 + 2"}
        result = security_node(state)
        assert result["security_findings"] == []

    def test_none_code_produces_empty_findings(self, base_state):
        state = {**base_state, "code_content": None}
        result = security_node(state)
        assert result["security_findings"] == []
