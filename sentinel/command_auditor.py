from __future__ import annotations

import re
import shlex
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable, Optional
from urllib.parse import urlparse

from sentinel.models import AuditDecision
from sentinel.sentinel_auditor import SentinelAuditor


@dataclass(frozen=True)
class HardKillConfig:
    blocked_strings: tuple[str, ...]
    blocked_paths: tuple[str, ...]
    blocked_tools: tuple[str, ...]
    blocked_network_tools: tuple[str, ...]
    whitelisted_domains: tuple[str, ...]
    lockdown_mode: bool
    allowed_commands: tuple[str, ...]


class CommandAuditor:
    def __init__(self, constitution: dict[str, Any], llm_auditor: Optional[SentinelAuditor] = None) -> None:
        self.constitution = constitution or {}
        self.llm_auditor = llm_auditor
        self.config = self._load_config(self.constitution)

    def audit(self, command: str) -> AuditDecision:
        normalized_command = self._normalize_command(command)

        deterministic_decision = self._hard_kill_filter(normalized_command)
        if deterministic_decision is not None:
            return deterministic_decision

        if self._is_allowed_in_lockdown(normalized_command):
            return AuditDecision(allowed=True, risk_score=0, reason="Command explicitly allowed by policy.")

        if self.llm_auditor is None:
            return AuditDecision.reject("LLM auditor unavailable; fail-closed policy applied.", risk_score=9)

        return self.llm_auditor.audit_command(normalized_command)

    def _hard_kill_filter(self, command: str) -> Optional[AuditDecision]:
        if not command.strip():
            return AuditDecision.reject("Empty command is rejected under fail-closed policy.", risk_score=10)

        if self.config.lockdown_mode and not self._is_allowed_in_lockdown(command):
            return AuditDecision.reject("Lockdown mode active: command not in allowed_commands.", risk_score=10)

        lowered_command = command.lower()

        for blocked in self.config.blocked_strings:
            if blocked.lower() in lowered_command:
                return AuditDecision.reject(f"Blocked token detected: {blocked}", risk_score=10)

        for blocked_path in self.config.blocked_paths:
            if blocked_path.lower() in lowered_command:
                return AuditDecision.reject(f"Blocked path access detected: {blocked_path}", risk_score=10)

        blocked_tool = self._match_blocked_tool(command)
        if blocked_tool is not None:
            return AuditDecision.reject(f"Blocked tool detected: {blocked_tool}", risk_score=10)

        if self._contains_base64_shell_exec(lowered_command):
            return AuditDecision.reject("Obfuscated payload execution pattern detected: base64 to shell.", risk_score=10)

        if self._contains_network_tool(lowered_command):
            urls = self._extract_urls(command)
            if not urls:
                return AuditDecision.reject(
                    "Network command without explicit URL/domain is rejected.",
                    risk_score=10,
                )

            for url in urls:
                domain = self._extract_domain(url)
                if not domain:
                    return AuditDecision.reject(f"Could not parse domain from network target: {url}", risk_score=10)
                if not self._is_whitelisted_domain(domain):
                    return AuditDecision.reject(
                        f"Outbound network domain not whitelisted: {domain}",
                        risk_score=10,
                    )

        return None

    def _is_allowed_in_lockdown(self, command: str) -> bool:
        if not self.config.allowed_commands:
            return False

        normalized_command = command.strip().lower()
        try:
            tokens = shlex.split(command, posix=True)
        except ValueError:
            tokens = command.split()

        first_token = tokens[0].lower() if tokens else ""
        first_basename = first_token.rsplit("/", 1)[-1]

        for allowed in self.config.allowed_commands:
            allowed_normalized = self._normalize_command(allowed).lower()
            if not allowed_normalized:
                continue

            if " " in allowed_normalized:
                if normalized_command == allowed_normalized or normalized_command.startswith(allowed_normalized):
                    return True
            elif normalized_command == allowed_normalized or normalized_command.startswith(f"{allowed_normalized} "):
                return True

            if first_token == allowed_normalized or first_basename == allowed_normalized:
                return True

        return False

    @staticmethod
    def _normalize_command(command: str) -> str:
        normalized = unicodedata.normalize("NFKC", command or "")
        normalized = normalized.replace("\u200b", "")

        # Join escaped newlines and strip common shell backslash-obfuscation.
        normalized = re.sub(r"\\\r?\n", "", normalized)
        normalized = re.sub(r"\\+([^\s])", r"\1", normalized)
        normalized = re.sub(r"\\+\s+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _contains_network_tool(self, lowered_command: str) -> bool:
        for tool in self.config.blocked_network_tools:
            if re.search(rf"\b{re.escape(tool.lower())}\b", lowered_command):
                return True
        return False

    def _match_blocked_tool(self, command: str) -> Optional[str]:
        try:
            tokens = shlex.split(command, posix=True)
        except ValueError:
            tokens = command.split()

        for token in tokens:
            candidate = token.strip().lower()
            if not candidate:
                continue

            candidate = candidate.rsplit("/", 1)[-1]
            for blocked_tool in self.config.blocked_tools:
                blocked = blocked_tool.lower().strip()
                if candidate == blocked:
                    return blocked_tool

                if blocked == "python" and re.fullmatch(r"python(?:\d+(?:\.\d+)*)?", candidate):
                    return blocked_tool

        return None

    @staticmethod
    def _contains_base64_shell_exec(lowered_command: str) -> bool:
        has_base64_decode = "base64 -d" in lowered_command or "base64 --decode" in lowered_command
        invokes_shell = bool(re.search(r"(?:\||&&|;)\s*(?:bash|sh)\b", lowered_command))
        return has_base64_decode and invokes_shell

    def _extract_urls(self, command: str) -> list[str]:
        urls: list[str] = []

        try:
            tokens = shlex.split(command, posix=True)
        except ValueError:
            return urls

        for token in tokens:
            if token.startswith("http://") or token.startswith("https://"):
                urls.append(token)

        if urls:
            return urls

        # Fallback to raw regex extraction in case of unusual quoting.
        return re.findall(r"https?://[^\s'\"]+", command)

    def _extract_domain(self, url: str) -> Optional[str]:
        parsed = urlparse(url)
        if parsed.hostname:
            return parsed.hostname.lower()
        return None

    def _is_whitelisted_domain(self, domain: str) -> bool:
        for allowed in self.config.whitelisted_domains:
            candidate = allowed.lower().strip()
            if domain == candidate or domain.endswith(f".{candidate}"):
                return True
        return False

    @staticmethod
    def _load_config(constitution: dict[str, Any]) -> HardKillConfig:
        hard_kill = constitution.get("hard_kill", {})
        network_lock = constitution.get("network_lock", {})
        execution_mode = constitution.get("execution_mode", {})

        blocked_strings = _as_tuple(hard_kill.get("blocked_strings"), default=("sudo", "rm -rf", "mkfs"))
        blocked_paths = _as_tuple(hard_kill.get("blocked_paths"), default=("~/.ssh", "~/.env", "/etc/"))
        blocked_tools = _as_tuple(hard_kill.get("blocked_tools"), default=("python", "pip", "npm"))

        blocked_network_tools = _as_tuple(network_lock.get("blocked_tools"), default=("curl", "wget"))

        whitelisted_domains = _as_tuple(
            network_lock.get("whitelisted_domains", constitution.get("whitelisted_domains", ())),
            default=(),
        )
        lockdown_mode = bool(execution_mode.get("lockdown_mode", constitution.get("lockdown_mode", False)))
        allowed_commands = _as_tuple(
            execution_mode.get("allowed_commands", constitution.get("allowed_commands", ())),
            default=(),
        )

        return HardKillConfig(
            blocked_strings=blocked_strings,
            blocked_paths=blocked_paths,
            blocked_tools=blocked_tools,
            blocked_network_tools=blocked_network_tools,
            whitelisted_domains=whitelisted_domains,
            lockdown_mode=lockdown_mode,
            allowed_commands=allowed_commands,
        )


def _as_tuple(value: Any, default: tuple[str, ...]) -> tuple[str, ...]:
    if value is None:
        return default
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Iterable):
        return tuple(str(item) for item in value)
    return default
