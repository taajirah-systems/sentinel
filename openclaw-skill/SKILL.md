---
name: sentinel
description: Security gateway that intercepts and audits shell commands before execution. Uses deterministic blocklists + LLM semantic analysis with fail-closed policy.
homepage: https://github.com/turnono/sentinel
command-dispatch: tool
command-tool: exec
---

# Sentinel Security Gateway

🛡️ **Sentinel** provides a security layer for command execution.

## Usage

When you need to run a shell command securely, use this skill to audit it first.

The skill wraps the exec tool and applies:
- **Blocked strings**: `sudo`, `rm -rf`, `mkfs`, etc.
- **Blocked paths**: `~/.ssh`, `~/.aws`, `/etc/passwd`
- **Blocked tools**: `python`, `pip`, `npm`, `node`
- **Network allowlist**: Only whitelisted domains permitted
- **Obfuscation detection**: Unicode normalization, base64 detection
- **LLM semantic analysis**: Detects complex attack patterns

## Security Policy

Commands are audited against the constitution at `{baseDir}/constitution.yaml`.

Fail-closed: Any uncertain or blocked command is rejected.

## Example

To run a command through Sentinel:

```
/sentinel ls -la
```

If blocked:
```
/sentinel sudo rm -rf /
→ Blocked: "Blocked token detected: sudo"
```
