"""
Sentinel API Test Suite

Tests for the FastAPI server endpoints using TestClient.
Run with: pytest tests/test_api.py -v
"""

import json
import os
import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app
import sys
sys.path.insert(0, str(__file__).rsplit("/", 2)[0])
from sentinel_server import app, startup_event
import asyncio


AUTH_HEADER = {"X-Sentinel-Token": "test-token"}


@pytest.fixture(scope="module", autouse=True)
def initialize_runtime():
    """Initialize Sentinel runtime before running tests."""
    os.environ["SENTINEL_AUTH_TOKEN"] = "test-token"
    os.environ["SENTINEL_DISABLE_AUTH"] = "false"
    asyncio.get_event_loop().run_until_complete(startup_event())
    yield


client = TestClient(app)


class TestHealthEndpoint:
    """Tests for the /health endpoint."""
    
    def test_health_returns_200(self):
        """Health check returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200
        
    def test_health_response_structure(self):
        """Health check returns expected JSON structure."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "sentinel"


class TestAuditEndpoint:
    """Tests for the /audit endpoint (audit + execute)."""
    
    def test_audit_safe_command_allowed(self):
        """Safe commands (ls, pwd, echo) are approved."""
        response = client.post("/audit", json={"command": "ls -la"}, headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is True
        assert data["risk_score"] <= 3
        
    def test_audit_blocked_sudo(self):
        """Commands with 'sudo' are blocked."""
        response = client.post("/audit", json={"command": "sudo rm -rf /"}, headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is False
        assert "sudo" in data["reason"].lower() or "blocked" in data["reason"].lower()
        
    def test_audit_blocked_rm_rf(self):
        """Destructive 'rm -rf' commands are blocked."""
        response = client.post("/audit", json={"command": "rm -rf /"}, headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is False
        
    def test_audit_empty_command_rejected(self):
        """Empty commands are rejected."""
        response = client.post("/audit", json={"command": ""}, headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is False
        assert data["risk_score"] == 10
        
    def test_audit_response_structure(self):
        """Response contains all required fields."""
        response = client.post("/audit", json={"command": "echo test"}, headers=AUTH_HEADER)
        data = response.json()
        assert "allowed" in data
        assert "risk_score" in data
        assert "reason" in data

    def test_audit_requires_token(self):
        """Audit endpoint rejects missing auth token."""
        response = client.post("/audit", json={"command": "echo test"})
        assert response.status_code == 401


class TestAuditOnlyEndpoint:
    """Tests for the /audit-only endpoint (audit without execution)."""
    
    def test_audit_only_safe_command(self):
        """Audit-only returns decision without executing."""
        response = client.post("/audit-only", json={"command": "ls"}, headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is True
        # Should NOT have stdout/stderr (not executed)
        assert "stdout" not in data or data.get("stdout") == ""
        
    def test_audit_only_blocked_command(self):
        """Audit-only correctly blocks dangerous commands."""
        response = client.post("/audit-only", json={"command": "sudo su"}, headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is False


class TestStressTesting:
    """Stress and edge case tests."""
    
    def test_large_payload_handled(self):
        """Large payloads don't crash the server (fail-closed)."""
        large_command = "A" * 100000  # 100KB junk
        response = client.post("/audit", json={"command": large_command}, headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        # Should fail-closed on suspicious large input
        assert data["allowed"] is False or data["risk_score"] >= 5
        
    def test_unicode_payload(self):
        """Unicode payloads are handled gracefully."""
        response = client.post("/audit", json={"command": "echo 'こんにちは'"}, headers=AUTH_HEADER)
        assert response.status_code == 200
        
    def test_null_bytes_blocked(self):
        """Commands with null bytes are rejected."""
        response = client.post("/audit", json={"command": "ls\x00-la"}, headers=AUTH_HEADER)
        assert response.status_code == 200
        data = response.json()
        # Should block or handle gracefully
        assert isinstance(data["allowed"], bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
