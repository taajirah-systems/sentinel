# Sentinel Skill for OpenClaw

🛡️ Security gateway that intercepts and audits shell commands before execution.

## Installation

### Option 1: Copy to OpenClaw skills directory

```bash
# Clone Sentinel
git clone https://github.com/turnono/sentinel.git
cd sentinel

# Copy skill to OpenClaw
cp -r openclaw-skill ~/.openclaw/skills/sentinel

# Copy core Sentinel package into the skill
cp -r sentinel ~/.openclaw/skills/sentinel/
cp sentinel_main.py ~/.openclaw/skills/sentinel/
```

### Option 2: Symlink (for development)

```bash
# Clone Sentinel
git clone https://github.com/turnono/sentinel.git

# Symlink to OpenClaw
ln -s $(pwd)/sentinel/openclaw-skill ~/.openclaw/skills/sentinel
```

## Configuration

### 1. Set your API key

Create `~/.openclaw/skills/sentinel/.env`:

```env
GOOGLE_API_KEY=your_api_key_here
SENTINEL_MODEL=gemini-2.0-flash
SENTINEL_AUTH_TOKEN=replace_with_long_random_value
```

### 2. Customize the constitution

Edit `~/.openclaw/skills/sentinel/constitution.yaml` to match your security requirements.

## Usage

Once installed, use the `sentinel_exec` tool in OpenClaw:

```
You: Run "ls -la" through the security gateway
OpenClaw: {"tool": "sentinel_exec", "command": "ls -la"}
```

### Example: Blocked command

```
You: Run "sudo rm -rf /"
OpenClaw: {"tool": "sentinel_exec", "command": "sudo rm -rf /"}
Result: {
  "status": "denied",
  "risk_score": 10,
  "reason": "Blocked token detected: sudo"
}
```

## Files

| File | Purpose |
|------|---------|
| `skill.yaml` | OpenClaw skill manifest |
| `sentinel_exec.py` | Tool handler |
| `constitution.yaml` | Security policy |
| `sentinel/` | Core Sentinel package (copy from parent) |

## Security Features

- **Blocked strings**: `sudo`, `rm -rf`, etc.
- **Blocked paths**: `~/.ssh`, `~/.aws`, `/etc/`
- **Blocked tools**: `python`, `pip`, `npm`
- **Network allowlist**: Only whitelisted domains
- **Obfuscation detection**: Unicode normalization, backslash handling
- **LLM semantic analysis**: Detects complex attack patterns
- **Fail-closed**: Uncertain commands are rejected

## License

MIT
