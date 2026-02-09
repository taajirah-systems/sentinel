"""
Sentinel Security Gateway - HTTP Server

FastAPI server that exposes the Sentinel runtime as an HTTP API.
The OpenClaw plugin calls this server to audit commands through the full
ADK/LLM semantic analysis pipeline.

Usage:
    python sentinel_server.py

The server runs on http://localhost:8765 by default.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import the Sentinel runtime
from sentinel_main import SentinelRuntime

app = FastAPI(
    title="Sentinel Security Gateway",
    description="HTTP API for command auditing with deterministic + LLM semantic analysis",
    version="1.0.0",
)

# Allow CORS for local development (OpenClaw plugin calls from localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Sentinel runtime once at startup
runtime: Optional[SentinelRuntime] = None


class AuditRequest(BaseModel):
    """Request body for command auditing."""
    command: str


class AuditResponse(BaseModel):
    """Response body from command auditing."""
    allowed: bool
    risk_score: int
    reason: str
    stdout: str = ""
    stderr: str = ""
    returncode: Optional[int] = None


@app.on_event("startup")
async def startup_event():
    """Initialize Sentinel runtime on server startup."""
    global runtime
    try:
        runtime = SentinelRuntime()
        if runtime.startup_warning:
            print(f"⚠️  Sentinel warning: {runtime.startup_warning}")
        print("🛡️  Sentinel Security Gateway initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Sentinel: {e}")
        raise


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "sentinel"}


@app.post("/audit", response_model=AuditResponse)
def audit_command(request: AuditRequest) -> Dict[str, Any]:
    """
    Audit a shell command through Sentinel's security layers.
    
    Layer 1: Deterministic blocklist (<1ms)
    Layer 2: LLM semantic analysis (~500ms) if available
    
    Returns audit decision with execution results if approved.
    """
    if runtime is None:
        raise HTTPException(status_code=503, detail="Sentinel runtime not initialized")
    
    if not request.command or not request.command.strip():
        return {
            "allowed": False,
            "risk_score": 10,
            "reason": "Empty command",
            "stdout": "",
            "stderr": "",
            "returncode": None,
        }
    
    start_time = time.time()
    try:
        result = runtime.run_intercepted_command(request.command)
        duration_ms = (time.time() - start_time) * 1000
        print(f"⏱️  Audit completed in {duration_ms:.2f}ms. Decision: {'✅' if result['allowed'] else '❌'} ({result.get('reason', 'No reason provided')})")
        return result
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        print(f"❌ Audit failed in {duration_ms:.2f}ms: {e}")
        raise


@app.post("/audit-only")
def audit_only(request: AuditRequest) -> Dict[str, Any]:
    """
    Audit a command WITHOUT executing it.
    Returns the audit decision only.
    """
    if runtime is None:
        raise HTTPException(status_code=503, detail="Sentinel runtime not initialized")
    
    # Use the command auditor directly for audit-only
    decision = runtime.command_auditor.audit(request.command)
    return decision.to_dict()


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("SENTINEL_PORT", "8765"))
    print(f"🛡️  Starting Sentinel Security Gateway on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
