from __future__ import annotations

import inspect
from src.sentinel.approval_gateway import ApprovalGateway
import json
import logging
import os
import shlex
import subprocess
from importlib import import_module
from pathlib import Path
from typing import Any, Optional, Union, List
import uuid
import requests
from .command_auditor import CommandAuditor
from .sentinel_auditor import SentinelAuditor
from .models import AuditDecision
from .policy import PolicyEnforcer
from .isolation import isolation_adapter
from .logger import (
    audit_logger,
    STAGE_INTAKE, STAGE_NORMALIZE, STAGE_REDACT, STAGE_POLICY_EVAL,
    STAGE_SEMANTIC_AUDIT, STAGE_ISOLATION_WRAP, STAGE_EXEC_RESULT,
    STAGE_FINAL_DECISION, STAGE_RUNTIME_DENIAL,
    POLICY_VERSION, SENTINEL_VERSION
)
from .normalizer import normalizer
from .redactor import redactor
from src.ledger.ledger_service import spend_service_credit, allocate_internal_credit
from src.ledger.ledger import read_wallets

try:
    import yaml
except ImportError as exc:
    yaml = None
    _YAML_IMPORT_ERROR = exc
else:
    _YAML_IMPORT_ERROR = None


DEFAULT_CONSTITUTION_CANDIDATES = (
    "Sentinel-Constitution.yaml",
)

PROJECT_ROOT = Path(__file__).resolve().parent
AUDIT_LOG_PATH = PROJECT_ROOT / "logs" / "sentinel_audit.log"
DEFAULT_EXEC_TIMEOUT_SECONDS = 15.0


def _autoload_dotenv() -> None:
    """
    Best-effort .env support.
    If python-dotenv is not installed, this is a no-op and runtime will use
    standard OS environment variables only.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    env_paths = (
        Path(".env"),
        PROJECT_ROOT / ".env",
    )
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)
            return

    load_dotenv(override=False)


_autoload_dotenv()


def _build_audit_logger() -> logging.Logger:
    logger = logging.getLogger("sentinel.audit")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(AUDIT_LOG_PATH, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


_AUDIT_LOGGER: Optional[logging.Logger] = None


def _get_audit_logger() -> Optional[logging.Logger]:
    global _AUDIT_LOGGER
    if _AUDIT_LOGGER is not None:
        return _AUDIT_LOGGER

    try:
        _AUDIT_LOGGER = _build_audit_logger()
    except Exception:
        _AUDIT_LOGGER = None
    return _AUDIT_LOGGER


def _log_audit_event(command: str, payload: dict[str, Any], correlation_id: Optional[str] = None) -> None:
    """Legacy wrapper for backward compatibility, now routes to structured logger."""
    audit_logger.log_event(
        event_type="execution_decision",
        input_str=command,
        correlation_id=correlation_id,
        decision="allow" if payload.get("allowed") else "block",
        reason=payload.get("reason"),
        metadata={
            "risk_score": payload.get("risk_score"),
            "returncode": payload.get("returncode")
        }
    )


def _log_inference_event(prompt: str, completion: Optional[str], payload: dict[str, Any], correlation_id: Optional[str] = None) -> None:
    """Legacy wrapper for backward compatibility, now routes to structured logger."""
    audit_logger.log_event(
        event_type="llm_audit",
        input_str=prompt,
        correlation_id=correlation_id,
        normalized_input=prompt,
        decision="allow" if payload.get("allowed") else "block",
        reason=payload.get("reason"),
        metadata={
            "risk_score": payload.get("risk_score"),
            "completion": completion[:100] + "..." if completion and len(completion) > 100 else completion
        }
    )


def _parse_execution_timeout(raw_timeout: Union[str, None]) -> float:
    if raw_timeout is None:
        return DEFAULT_EXEC_TIMEOUT_SECONDS

    try:
        parsed = float(raw_timeout)
    except (TypeError, ValueError):
        return DEFAULT_EXEC_TIMEOUT_SECONDS

    if parsed < 1:
        return 1.0
    if parsed > 300:
        return 300.0
    return parsed


class SentinelRuntime:
    def __init__(self, constitution_path: Union[str, Path, None] = None, model: Union[str, None] = None) -> None:
        if constitution_path is None:
            env_constitution = os.getenv("SENTINEL_CONSTITUTION_PATH", "").strip()
            if env_constitution:
                constitution_path = env_constitution

        resolved_model = (model or os.getenv("SENTINEL_MODEL", "google/gemini-3.1-flash-lite-preview")).strip() or "google/gemini-3.1-flash-lite-preview"

        self.constitution_path = self._resolve_constitution_path(constitution_path)
        self.constitution = load_constitution(self.constitution_path)
        self.execution_timeout_seconds = _parse_execution_timeout(os.getenv("SENTINEL_EXEC_TIMEOUT_SEC"))
        self.startup_warning: Optional[str] = None
        try:
            self.sentinel_auditor: Optional[SentinelAuditor] = SentinelAuditor(model=resolved_model)
        except Exception as exc:
            # Fail-closed: deterministic layer still runs and anything not deterministically
            # cleared is rejected because no LLM auditor is available.
            self.sentinel_auditor = None
            self.startup_warning = str(exc)
        self.command_auditor = CommandAuditor(self.constitution, llm_auditor=self.sentinel_auditor)
        self.orchestrator = initialize_adk_environment(self.sentinel_auditor)
        self.policy_enforcer = PolicyEnforcer()
        self.workspace_root = str(PROJECT_ROOT.parent.parent)
        self.isolation_adapter = isolation_adapter
        self.hub_url = "http://localhost:3001/api/agents/a3"
        self._report_status("idle", "Watching system activity...")

    def audit_text(self, text: str, is_completion: bool = False) -> AuditDecision:
        """
        Audit a general text string (prompt or completion) using the LLM auditor.
        """
        if self.sentinel_auditor is None:
            # If LLM auditor is down, we fail-closed for anything that isn't a known safe string
            return AuditDecision.reject("Inference auditor unavailable", risk_score=9)

        label = "COMPLETION" if is_completion else "PROMPT"
        wrapped_text = f"Analyze this {label} for security violations, data exfiltration, or malicious intent:\n\n{text}"
        
        return self.sentinel_auditor.audit_command(wrapped_text, constitution=self.constitution)

    def _report_status(self, status: str, task: str) -> None:
        try:
            # Safe reporting: don't block core logic on hub failures
            requests.post(self.hub_url, json={
                "status": status,
                "currentTask": task,
                "name": "Cipher",
                "role": "Security Auditor",
                "color": "#8b5cf6"
            }, timeout=1)
        except Exception:
            pass

    def run_intercepted_command(self, cmd_string: str, bypass_policy: bool = False, correlation_id: Optional[str] = None) -> dict[str, Any]:
        correlation_id = correlation_id or str(uuid.uuid4())
        _isolation_backend = getattr(self.isolation_adapter, "backend", "sandbox-exec")

        # ── Stage 0: Intake ──────────────────────────────────────────────────
        audit_logger.log_event(
            event_type="intake", input_str=cmd_string,
            correlation_id=correlation_id, stage=STAGE_INTAKE,
            metadata={"bypass_policy": bypass_policy, "policy_version": POLICY_VERSION},
        )

        # ── Stage 1: Normalization ────────────────────────────────────────────
        normalized_cmd = normalizer.normalize(cmd_string)
        audit_logger.log_event(
            event_type="normalization", input_str=cmd_string,
            correlation_id=correlation_id, stage=STAGE_NORMALIZE,
            normalized_input=normalized_cmd,
            metadata={"changed": normalized_cmd != cmd_string},
        )

        # ── Stage 2: Redaction ────────────────────────────────────────────────
        redacted_cmd = redactor.redact(normalized_cmd)
        audit_logger.log_event(
            event_type="redaction", input_str="[REDACTED]",
            correlation_id=correlation_id, stage=STAGE_REDACT,
            normalized_input=redacted_cmd,
            metadata={"redacted": redacted_cmd != normalized_cmd},
        )

        # ── Stage 2.5: Budget Check ───────────────────────────────────────────
        actor_id = os.getenv("SENTINEL_ACTOR_ID", "system-agent")
        # We check for a minimum base cost (e.g. 0.1 JUL) using authoritative cache
        wallets = read_wallets()
        balance = wallets.get(actor_id, {}).get("balance_jul", 0.0)
        if balance < 0.1:
            failed = AuditDecision.reject(
                f"Insufficient Credits: Wallet {actor_id} requires more JUL for execution (Balance: {balance})",
                risk_score=5,
            )
            payload = failed.to_dict()
            payload.update({"returncode": None, "stdout": "", "stderr": "Credit limit reached."})
            audit_logger.log_event(
                event_type="budget_denial", input_str=redacted_cmd,
                correlation_id=correlation_id, stage="budget_check",
                decision="block", reason=failed.reason,
                metadata={"risk_score": 5, "actor_id": actor_id},
            )
            _log_audit_event(cmd_string, payload, correlation_id=correlation_id)
            return payload

        self._report_status("working", f"Auditing: {str(redacted_cmd)[:30]}...")
        decision = None

        # ── Stage 3: Policy Evaluation ───────────────────────────────────────
        if not bypass_policy:
            policy_result = self.policy_enforcer.evaluate(normalized_cmd)
            action = policy_result.get("action", "block")
            audit_logger.log_event(
                event_type="policy_evaluation", input_str=redacted_cmd,
                correlation_id=correlation_id, stage=STAGE_POLICY_EVAL,
                decision=action,
                reason=policy_result.get("reason"),
                metadata={
                    "rule_id": policy_result.get("rule_id"),
                    "rule_name": policy_result.get("rule_name"),
                    "provenance": policy_result.get("provenance"),
                    "category": policy_result.get("category"),
                    "policy_version": POLICY_VERSION,
                },
            )

            if action == "block":
                failed = AuditDecision.reject(
                    f"Policy Violation: {policy_result.get('rule_name', 'Unknown')} - {policy_result.get('reason', 'Blocked by policy')}",
                    risk_score=10,
                )
                payload = failed.to_dict()
                payload.update({
                    "returncode": None, "stdout": "", "stderr": "",
                    "rule_id": policy_result.get("rule_id"),
                    "provenance": policy_result.get("provenance"),
                })
                audit_logger.log_event(
                    event_type="final_decision", input_str=redacted_cmd,
                    correlation_id=correlation_id, stage=STAGE_FINAL_DECISION,
                    decision="block", reason=failed.reason,
                    metadata={"risk_score": 10, "returncode": None, "isolation": "not_reached"},
                )
                _log_audit_event(redacted_cmd, payload, correlation_id=correlation_id)
                return payload

            if action in ("review", "escalate"):
                gw = ApprovalGateway()
                appr_res = gw.request_approval(
                    command=cmd_string,
                    correlation_id=correlation_id,
                    rule_id=policy_result.get("rule_id", "—"),
                    reason=policy_result.get("reason", "Requires review"),
                    input_str=redacted_cmd
                )
                if appr_res.get("approved"):
                    decision = AuditDecision(
                        allowed=True, risk_score=0,
                        reason=f"Approved by operator {appr_res.get('actor_id')}: {appr_res.get('override_reason')}"
                    )
                else:
                    failed = AuditDecision.reject(
                        f"Review Denied: Operator {appr_res.get('actor_id')} rejected execution",
                        risk_score=10,
                    )
                    payload = failed.to_dict()
                    payload.update({
                        "returncode": None, "stdout": "", "stderr": "",
                        "rule_id": policy_result.get("rule_id"),
                        "provenance": policy_result.get("provenance"),
                    })
                    audit_logger.log_event(
                        event_type="final_decision", input_str=redacted_cmd,
                        correlation_id=correlation_id, stage=STAGE_FINAL_DECISION,
                        decision="block", reason=failed.reason,
                        metadata={"risk_score": 10, "returncode": None, "isolation": "not_reached"},
                    )
                    _log_audit_event(redacted_cmd, payload, correlation_id=correlation_id)
                    return payload

            if action == "allow":
                decision = AuditDecision(
                    allowed=True, risk_score=0,
                    reason=f"Allowed by policy: {policy_result.get('rule_name', 'Policy Allow')}",
                )
        else:
            # Bypass path – emit a synthetic policy event
            audit_logger.log_event(
                event_type="policy_evaluation", input_str=redacted_cmd,
                correlation_id=correlation_id, stage=STAGE_POLICY_EVAL,
                decision="allow", reason="Policy bypassed (HITL approval)",
                metadata={"rule_id": "hitl-bypass", "policy_version": POLICY_VERSION},
            )

        if decision is None:
            if bypass_policy:
                decision = AuditDecision(allowed=True, risk_score=0, reason="User Approved via HITL")
            else:
                # ── Stage 4: Semantic Audit ───────────────────────────────────
                semantic_result = self.command_auditor.audit(normalized_cmd)
                audit_logger.log_event(
                    event_type="semantic_audit", input_str=redacted_cmd,
                    correlation_id=correlation_id, stage=STAGE_SEMANTIC_AUDIT,
                    decision="allow" if semantic_result.allowed else "block",
                    reason=semantic_result.reason,
                    metadata={"risk_score": semantic_result.risk_score},
                )
                decision = semantic_result
        else:
            # Policy already cleared – emit skip event for completeness
            audit_logger.log_event(
                event_type="semantic_audit", input_str=redacted_cmd,
                correlation_id=correlation_id, stage=STAGE_SEMANTIC_AUDIT,
                decision="skip", reason="Cleared deterministically; semantic stage skipped",
                metadata={"risk_score": 0},
            )

        payload: dict[str, Any] = decision.to_dict()

        if not decision.allowed:
            payload.update({"returncode": None, "stdout": "", "stderr": ""})
            audit_logger.log_event(
                event_type="final_decision", input_str=redacted_cmd,
                correlation_id=correlation_id, stage=STAGE_FINAL_DECISION,
                decision="block", reason=decision.reason,
                metadata={"risk_score": decision.risk_score, "returncode": None, "isolation": "not_reached"},
            )
            _log_audit_event(redacted_cmd, payload, correlation_id=correlation_id)
            return payload

        # ── Stage 5: Isolation Wrapping ───────────────────────────────────────
        shell_operators = {"|", ">", "&&", ";", "<<", ">>"}
        use_shell = any(op in cmd_string for op in shell_operators)
        if use_shell:
            cmd_args_for_isolation = ["/bin/sh", "-c", cmd_string]
        else:
            try:
                cmd_args_for_isolation = shlex.split(cmd_string, posix=True)
            except ValueError as exc:
                failed = AuditDecision.reject(f"Command parsing failed: {exc}", risk_score=10)
                payload = failed.to_dict()
                payload.update({"returncode": None, "stdout": "", "stderr": ""})
                audit_logger.log_event(
                    event_type="final_decision", input_str=redacted_cmd,
                    correlation_id=correlation_id, stage=STAGE_FINAL_DECISION,
                    decision="block", reason=f"Command parse error: {exc}",
                    metadata={"risk_score": 10, "isolation": "not_reached"},
                )
                _log_audit_event(cmd_string, payload, correlation_id=correlation_id)
                return payload

        try:
            wrapped_cmd = self.isolation_adapter.wrap_command(cmd_args_for_isolation, self.workspace_root)
        except Exception as exc:
            failed = AuditDecision.reject(f"Sandbox profile generation failed: {exc}", risk_score=10)
            payload = failed.to_dict()
            payload.update({"returncode": None, "stdout": "", "stderr": str(exc)})
            audit_logger.log_event(
                event_type="final_decision", input_str=redacted_cmd,
                correlation_id=correlation_id, stage=STAGE_FINAL_DECISION,
                decision="block", reason=failed.reason,
                metadata={"risk_score": 10, "returncode": None, "isolation": "failed"},
            )
            _log_audit_event(cmd_string, payload, correlation_id=correlation_id)
            return payload

        audit_logger.log_event(
            event_type="isolation_wrap", input_str=redacted_cmd,
            correlation_id=correlation_id, stage=STAGE_ISOLATION_WRAP,
            decision="wrapped",
            metadata={"backend": _isolation_backend, "shell_operator": use_shell, "wrapped_argv": str(wrapped_cmd[:3])},
        )

        # ── Stage 6: Execution ────────────────────────────────────────────────
        try:
            completed = subprocess.run(
                wrapped_cmd, shell=False, check=False,
                capture_output=True, text=True,
                timeout=self.execution_timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            failed = AuditDecision.reject(
                f"Command execution timed out after {self.execution_timeout_seconds:g}s.",
                risk_score=10,
            )
            payload = failed.to_dict()
            payload.update({"returncode": None, "stdout": exc.stdout or "", "stderr": exc.stderr or "Execution timeout"})
            audit_logger.log_event(
                event_type="exec_result", input_str=redacted_cmd,
                correlation_id=correlation_id, stage=STAGE_EXEC_RESULT,
                decision="timeout", reason="Execution timed out",
                metadata={"returncode": None, "timeout_sec": self.execution_timeout_seconds},
            )
            audit_logger.log_event(
                event_type="final_decision", input_str=redacted_cmd,
                correlation_id=correlation_id, stage=STAGE_FINAL_DECISION,
                decision="block", reason=failed.reason,
                metadata={"risk_score": 10, "returncode": None},
            )
            _log_audit_event(cmd_string, payload, correlation_id=correlation_id)
            return payload
        except Exception as exc:
            failed = AuditDecision.reject(f"Command execution failed: {exc}", risk_score=10)
            payload = failed.to_dict()
            payload.update({"returncode": None, "stdout": "", "stderr": str(exc)})
            audit_logger.log_event(
                event_type="exec_result", input_str=redacted_cmd,
                correlation_id=correlation_id, stage=STAGE_EXEC_RESULT,
                decision="error", reason=str(exc),
                metadata={"returncode": None},
            )
            audit_logger.log_event(
                event_type="final_decision", input_str=redacted_cmd,
                correlation_id=correlation_id, stage=STAGE_FINAL_DECISION,
                decision="block", reason=failed.reason,
                metadata={"risk_score": 10, "returncode": None},
            )
            _log_audit_event(cmd_string, payload, correlation_id=correlation_id)
            return payload

        # ── Stage 7: Execution Result ──────────────────────────────────────────
        # Detect genuine runtime denial from sandbox exit codes.
        # macOS sandbox-exec returns 1 when SBPL denies a syscall at runtime.
        # We surface this as its own STAGE_RUNTIME_DENIAL event so it is
        # distinct from a policy block and visible in replay.
        _sandbox_denial = (
            _isolation_backend == "sandbox-exec"
            and completed.returncode != 0
            and completed.returncode is not None
        )

        audit_logger.log_event(
            event_type="exec_result", input_str=redacted_cmd,
            correlation_id=correlation_id, stage=STAGE_EXEC_RESULT,
            decision="runtime_denied" if _sandbox_denial else "success",
            reason=f"Exit code {completed.returncode}",
            metadata={
                "returncode": completed.returncode,
                "stdout_bytes": len(completed.stdout),
                "stderr_bytes": len(completed.stderr),
                "sandbox_denial": _sandbox_denial,
            },
        )

        if _sandbox_denial:
            # Emit explicit runtime_denial stage for forensic clarity
            stderr_snip = completed.stderr[:200] if completed.stderr else ""
            audit_logger.log_event(
                event_type="runtime_denial", input_str=redacted_cmd,
                correlation_id=correlation_id, stage=STAGE_RUNTIME_DENIAL,
                decision="denied",
                reason="Sandbox (Seatbelt SBPL) rejected syscall at runtime",
                metadata={
                    "returncode": completed.returncode,
                    "denial_type": "network-outbound" if "network" in stderr_snip.lower() else "sbpl",
                    "stderr_snippet": stderr_snip,
                    "backend": _isolation_backend,
                    "sentinel_version": SENTINEL_VERSION,
                    "policy_version": POLICY_VERSION,
                },
            )

        # Record the spend event in the ledger
        actor_id = os.getenv("SENTINEL_ACTOR_ID", "system-agent")
        # For now, we use a flat fee or extract from metadata if available
        # In a real scenario, this might come from the policy or audit decision
        actual_cost = payload.get("estimated_cost_jul") or 0.1 
        
        spend_service_credit(
            wallet_id=actor_id,
            amount_jul=actual_cost,
            correlation_id=correlation_id,
            description=f"Command: {cmd_args_for_isolation[0] if not use_shell else 'shell-script'}",
            outcome="completed" if completed.returncode == 0 else "failed"
        )
        
        payload.update({"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr})
        _final_decision = "runtime_denied" if _sandbox_denial else "allow"
        _final_reason   = (
            f"Sandbox denied at runtime (exit {completed.returncode}); policy had allowed"
            if _sandbox_denial else decision.reason
        )
        audit_logger.log_event(
            event_type="final_decision", input_str=redacted_cmd,
            correlation_id=correlation_id, stage=STAGE_FINAL_DECISION,
            decision=_final_decision,
            reason=_final_reason,
            metadata={
                "risk_score": decision.risk_score,
                "returncode": completed.returncode,
                "isolation": _isolation_backend,
                "sandbox_denial": _sandbox_denial,
                "cost_jul": actual_cost
            },
        )
        _log_audit_event(cmd_string, payload, correlation_id=correlation_id)
        # Note: Functional spend_service_credit already updates reconciled state
        self._report_status("idle", "Audit complete. Monitoring...")
        payload["decision"] = _final_decision
        payload["sandbox_denial"] = _sandbox_denial
        payload["correlation_id"] = correlation_id
        return payload

    def _resolve_constitution_path(self, constitution_path: Union[str, Path, None]) -> Path:
        if constitution_path is not None:
            path = Path(constitution_path)
            if not path.exists():
                raise FileNotFoundError(f"Constitution file not found: {path}")
            return path

        for candidate in DEFAULT_CONSTITUTION_CANDIDATES:
            path = Path(candidate)
            if path.exists():
                return path
            project_path = PROJECT_ROOT / candidate
            if project_path.exists():
                return project_path

        raise FileNotFoundError(
            "No constitution file found. Expected one of: "
            + ", ".join(DEFAULT_CONSTITUTION_CANDIDATES)
        )


def load_constitution(path: Union[str, Path]) -> dict[str, Any]:
    path_obj = Path(path)
    raw_text = path_obj.read_text(encoding="utf-8")

    if yaml is not None:
        data = yaml.safe_load(raw_text) or {}
    else:
        data = _minimal_yaml_load(raw_text)

    if not isinstance(data, dict):
        raise ValueError("Constitution file must deserialize to a mapping/object.")

    return data


def initialize_adk_environment(sentinel_auditor: Optional[SentinelAuditor]) -> Optional[Any]:
    if sentinel_auditor is None:
        return None

    sequential_cls = _resolve_sequential_agent_class()
    if sequential_cls is None:
        return None

    signature = inspect.signature(sequential_cls)
    kwargs: dict[str, Any] = {}

    if "name" in signature.parameters:
        kwargs["name"] = "sentinel_orchestrator"
    if "agents" in signature.parameters:
        kwargs["agents"] = [sentinel_auditor.agent]
    elif "sub_agents" in signature.parameters:
        kwargs["sub_agents"] = [sentinel_auditor.agent]

    try:
        return sequential_cls(**kwargs)
    except Exception:
        return None


def _resolve_sequential_agent_class() -> Optional[type]:
    candidates = (
        ("google.adk.agents", "SequentialAgent"),
        ("google_adk.agents", "SequentialAgent"),
    )

    for module_name, class_name in candidates:
        try:
            module = import_module(module_name)
            return getattr(module, class_name)
        except Exception:
            continue

    return None


def _minimal_yaml_load(raw_text: str) -> dict[str, Any]:
    """
    Minimal YAML parser for Sentinel constitution files when PyYAML is unavailable.
    Supported subset:
    - indentation-based dictionaries
    - lists with '- item'
    - scalar values (string/int/bool)
    """
    lines: list[tuple[int, str]] = []
    for raw_line in raw_text.splitlines():
        stripped_comment = raw_line.split("#", 1)[0].rstrip()
        if not stripped_comment.strip():
            continue
        indent = len(stripped_comment) - len(stripped_comment.lstrip(" "))
        content = stripped_comment.strip()
        lines.append((indent, content))

    index = 0

    def parse_block(expected_indent: int) -> Any:
        nonlocal index

        if index >= len(lines) or lines[index][0] < expected_indent:
            return {}

        mode: Optional[str] = None
        as_dict: dict[str, Any] = {}
        as_list: list[Any] = []

        while index < len(lines):
            indent, content = lines[index]
            if indent < expected_indent:
                break
            if indent > expected_indent:
                raise ValueError(f"Unexpected indentation at: {content!r}")

            if content.startswith("- "):
                if mode is None:
                    mode = "list"
                elif mode != "list":
                    raise ValueError("Invalid YAML: mixed list and mapping at same indentation.")

                item = content[2:].strip()
                index += 1
                if item == "":
                    as_list.append(parse_block(expected_indent + 2))
                else:
                    as_list.append(parse_scalar(item))
                continue

            if mode is None:
                mode = "dict"
            elif mode != "dict":
                raise ValueError("Invalid YAML: mixed mapping and list at same indentation.")

            if ":" not in content:
                raise ValueError(f"Invalid YAML mapping line: {content!r}")

            key, raw_value = content.split(":", 1)
            key = key.strip()
            value = raw_value.strip()
            index += 1

            if value:
                as_dict[key] = parse_scalar(value)
                continue

            if index < len(lines) and lines[index][0] > expected_indent:
                as_dict[key] = parse_block(expected_indent + 2)
            else:
                as_dict[key] = {}

        if mode == "list":
            return as_list
        return as_dict

    def parse_scalar(value: str) -> Any:
        lowered = value.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
            return int(value)
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        return value

    parsed = parse_block(0)
    if not isinstance(parsed, dict):
        raise ValueError("Constitution YAML must be a mapping at the root level.")
    return parsed


_runtime: Optional[SentinelRuntime] = None


def run_intercepted_command(cmd_string: str) -> dict[str, Any]:
    global _runtime
    if _runtime is None:
        _runtime = SentinelRuntime()
    return _runtime.run_intercepted_command(cmd_string, bypass_policy=False)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sentinel command interception entry point")
    parser.add_argument("command", help="Shell command string to evaluate and optionally execute")
    parser.add_argument(
        "--constitution",
        default=None,
        help="Optional path to constitution YAML. Defaults to Sentinel-Constitution.yaml",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Gemini model for the SentinelAuditor (defaults to SENTINEL_MODEL or google/gemini-3.1-flash-lite-preview).",
    )

    args = parser.parse_args()

    runtime = SentinelRuntime(constitution_path=args.constitution, model=args.model)
    result = runtime.run_intercepted_command(args.command)
    print(json.dumps(result, indent=2))
