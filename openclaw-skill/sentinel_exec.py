#!/usr/bin/env python3
"""
Sentinel Exec Tool for OpenClaw

This handler intercepts shell commands, audits them through Sentinel's
security gateway, and only executes approved commands.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# Add Sentinel to path - look in multiple locations
SKILL_DIR = Path(__file__).resolve().parent
PARENT_DIR = SKILL_DIR.parent

# Search paths for Sentinel
SEARCH_PATHS = [
    os.environ.get("SENTINEL_PATH", ""),
    str(SKILL_DIR / "sentinel"),
    str(SKILL_DIR),
    str(PARENT_DIR / "sentinel"),
    str(PARENT_DIR),
]

for path in SEARCH_PATHS:
    if path and path not in sys.path and Path(path).exists():
        sys.path.insert(0, path)

try:
    from sentinel import SentinelRuntime
except ImportError:
    from sentinel_main import SentinelRuntime


class SentinelExecHandler:
    """OpenClaw tool handler for Sentinel-protected command execution."""

    def __init__(self):
        constitution_path = os.environ.get(
            "SENTINEL_CONSTITUTION_PATH",
            str(SKILL_DIR / "constitution.yaml")
        )
        model = os.environ.get("SENTINEL_MODEL", "gemini-2.0-flash")
        
        self.runtime = SentinelRuntime(
            constitution_path=constitution_path,
            model=model
        )

    def execute(self, command: str, workdir: str | None = None) -> dict[str, Any]:
        """
        Audit and execute a shell command.
        
        Args:
            command: Shell command to audit and execute
            workdir: Optional working directory
            
        Returns:
            Result dict with audit decision and command output
        """
        # Change to workdir if specified
        original_cwd = None
        if workdir:
            original_cwd = os.getcwd()
            os.chdir(os.path.expanduser(workdir))

        try:
            result = self.runtime.run_intercepted_command(command)
            
            # Format response for OpenClaw
            response = {
                "status": "allowed" if result["allowed"] else "denied",
                "risk_score": result.get("risk_score", 10),
                "reason": result.get("reason", ""),
            }

            if result["allowed"]:
                response["returncode"] = result.get("returncode")
                response["stdout"] = result.get("stdout", "")
                response["stderr"] = result.get("stderr", "")
            else:
                response["error"] = f"Command blocked: {result['reason']}"

            return response

        finally:
            if original_cwd:
                os.chdir(original_cwd)


# OpenClaw entry point
def handle(params: dict[str, Any]) -> dict[str, Any]:
    """OpenClaw tool handler entry point."""
    handler = SentinelExecHandler()
    
    command = params.get("command")
    if not command:
        return {"status": "error", "error": "Missing required parameter: command"}
    
    workdir = params.get("workdir")
    
    return handler.execute(command, workdir)


# CLI testing
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sentinel_exec.py <command>")
        sys.exit(1)
    
    result = handle({"command": " ".join(sys.argv[1:])})
    print(json.dumps(result, indent=2))
