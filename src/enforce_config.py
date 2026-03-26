import json
import os
import sys
from pathlib import Path

def enforce_config():
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    
    # Forcefully remove agent-level overrides that fight with the global config
    workspaces = [Path.home() / ".openclaw" / "agents", Path.home() / ".openclaw" / "workspace-architect", Path.home() / ".openclaw" / "workspace-main", Path.home() / ".openclaw" / "workspace-researcher"]
    for agents_dir in workspaces:
        if agents_dir.exists():
            for override in ["models.json", "auth-profiles.json", "auth.json"]:
                for p in agents_dir.rglob(override):
                    try:
                        p.unlink()
                        print(f"🧹 Purged override: {p}")
                    except Exception:
                        pass

    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return

    try:
        if config_path.exists():
            os.chmod(config_path, 0o644)

        with open(config_path, "r") as f:
            config = json.load(f)

        modified = False

        # Enforce Sentinel Plugin - DISABLED (Sentinel is now a Skill)
        plugins = config.get("plugins", {})
        if "entries" in plugins and "sentinel" in plugins["entries"]:
            print("🛡️  Removing legacy Sentinel plugin entry...")
            del plugins["entries"]["sentinel"]
            modified = True

        # Enforce WhatsApp Group Policy
        channels = config.get("channels", {})
        whatsapp = channels.get("whatsapp", {})
        allow_from = whatsapp.get("allowFrom", [])
        modified_cl = False
        for grp in ["120363409503272487@g.us", "120363424951654295@g.us"]:
            if grp not in allow_from:
                allow_from.append(grp)
                modified_cl = True
        
        if modified_cl:
            print("📱 Adding WhatsApp groups to allowFrom list...")
            whatsapp["allowFrom"] = allow_from

        groups_wa = whatsapp.get("groups", {})
        if "*" not in groups_wa or groups_wa["*"].get("requireMention", False) is not True:
            print("📱 Enforcing requireMention for WhatsApp groups...")
            groups_wa["*"] = groups_wa.get("*", {})
            groups_wa["*"]["requireMention"] = True
            whatsapp["groups"] = groups_wa
            modified_cl = True

        if whatsapp.get("groupPolicy") != "allowlist":
            print("🔒 Enforcing groupPolicy=allowlist for WhatsApp...")
            whatsapp["groupPolicy"] = "allowlist"
            modified_cl = True
            
        if modified_cl:
            channels["whatsapp"] = whatsapp
            modified = True

        # Enforce Telegram Group Policy
        telegram = channels.get("telegram", {})
        groups_tg = telegram.get("groups", {})
        if "*" not in groups_tg or groups_tg["*"].get("requireMention", False) is not True:
            print("📱 Enforcing requireMention for Telegram groups...")
            groups_tg["*"] = groups_tg.get("*", {})
            groups_tg["*"]["requireMention"] = True
            telegram["groups"] = groups_tg
            channels["telegram"] = telegram
            modified = True

        if telegram.get("groupPolicy") != "allowlist":
            print("🔒 Enforcing groupPolicy=allowlist for Telegram...")
            telegram["groupPolicy"] = "allowlist"
            channels["telegram"] = telegram
            modified = True
            
        if modified:
            config["channels"] = channels

        # Gateway Port and Auth Enforcement
        gateway = config.get("gateway", {})
        if gateway.get("port") != 18789:
            print("⚓ Rotating Gateway Port to 18789 (Connection Reset)...")
            gateway["port"] = 18789
            modified = True

        if "bind" in gateway:
            print("🧹 Removing invalid 'bind' key from gateway...")
            del gateway["bind"]
            modified = True
            
        auth_config = gateway.get("auth", {})
        # NOTE: Auth mode is not enforced here — respect whatever is set in openclaw.json
            
        # Synchronize credentials from local .env
        env_path = Path.home() / "sentinel" / ".env"
        password = None
        google_api_key = None
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if line.startswith("OPENCLAW_PASSWORD="):
                        password = line.split("=", 1)[1].strip().strip('\'"')
                    elif line.startswith("GEMINI_API_KEY="):
                        google_api_key = line.split("=", 1)[1].strip().strip('\'"')
        
        if password:
            if auth_config.get("password") != password:
                print("🔑 Setting gateway auth password...")
                auth_config["password"] = password
                modified = True
            
            remote = gateway.get("remote", {})
            if remote.get("password") != password or remote.get("url") != "ws://127.0.0.1:18789":
                print("🔑 Synchronizing CLI remote credentials (ws://)...")
                remote["password"] = password
                remote["url"] = "ws://127.0.0.1:18789"
                gateway["remote"] = remote
                modified = True
                
        if modified:
            gateway["auth"] = auth_config
            config["gateway"] = gateway

        # Enforce Dynamic Model Selection with Failover
        agents = config.get("agents", {})
        defaults = agents.get("defaults", {})
        model_config = defaults.get("model", {})
        
        valid_models = [
            "google/gemini-3.1-flash-lite-preview"
        ]
        
        models_registry = {m: {} for m in valid_models}
        if defaults.get("models") != models_registry:
            print(f"🧹 Syncing model registry (Failover Support)...")
            defaults["models"] = models_registry
            modified = True
            
        expected_primary = "google/gemini-3.1-flash-lite-preview"
        if model_config.get("primary") != expected_primary:
            print(f"🔄 Setting primary model to {expected_primary}...")
            model_config["primary"] = expected_primary
            defaults["model"] = model_config
            modified = True

        expected_fallbacks = ["google/gemini-3.1-flash-lite-preview"]
        if model_config.get("fallbacks") != expected_fallbacks:
            print(f"🔄 Setting fallback chain: {', '.join(expected_fallbacks)}")
            model_config["fallbacks"] = expected_fallbacks
            defaults["model"] = model_config
            modified = True

        # Auth Profiles Management
        auth_block = config.get("auth", {"profiles": {}})
        profiles = auth_block.get("profiles", {})
        profiles_modified = False
        
        for name in list(profiles.keys()):
            p = profiles[name]
            if any(k in p for k in ["accessToken", "refreshToken", "clientId", "clientSecret", "apiKey"]):
                print(f"🧹 Sanitizing profile auth keys: {name}...")
                profiles[name] = {"provider": p["provider"], "mode": p["mode"]}
                profiles_modified = True
        
        if google_api_key and profiles.get("google", {}).get("mode") != "api_key":
            print("🚀 Configuring Google Gemini metadata profile...")
            profiles["google"] = {"provider": "google", "mode": "api_key"}
            profiles_modified = True

        if profiles_modified:
            auth_block["profiles"] = profiles
            config["auth"] = auth_block
            modified = True

        # Purge Local Providers (Force Sovereign Cloud-Only)
        models_obj = config.get("models", {})
        providers = models_obj.get("providers", {})
        purged_providers = ["morpheus"]
        for p in purged_providers:
            if p in providers:
                print(f"🧹 Purging local provider: {p}...")
                del providers[p]
                modified = True
        
        # Ensure Google Provider is configured correctly
        if google_api_key:
            if "google" not in providers or providers["google"].get("apiKey") != google_api_key:
                print("🚀 Synchronizing Google Gemini provider credentials...")
                providers["google"] = {
                    "baseUrl": "https://generativelanguage.googleapis.com/v1beta",
                    "api": "google-generative-ai",
                    "apiKey": google_api_key,
                    "models": []
                }
                modified = True
        
        if modified:
            models_obj["providers"] = providers
            config["models"] = models_obj

        # Specialized Agent Enforcement
        agents_list = agents.get("list", [])
        
        def ensure_identity(agent_id, prompt):
            workspace_root = Path.home() / "taajirah_systems" / "BOARDROOM"
            agent_dir = Path.home() / ".openclaw" / "agents" / agent_id / "agent"
            agent_dir.mkdir(parents=True, exist_ok=True)
            identity_file = agent_dir / "IDENTITY.md"
            if workspace_root.exists() and agent_id == "architect":
                 with open(workspace_root / "IDENTITY.md", "w") as f: f.write(prompt)
            print(f"🆔 Updating identity for {agent_id}...")
            with open(identity_file, "w") as f: f.write(prompt)

        # Enforce Architect and Sentinel Agents exist in the list
        for agent_id, name in [("architect", "Architect"), ("sentinel", "Sentinel")]:
            agent = next((a for a in agents_list if a["id"] == agent_id), None)
            if not agent:
                print(f"🏗️  Adding {name} agent...")
                agent = {"id": agent_id, "name": name}
                agents_list.append(agent)
                modified = True
            # NOTE: Per-agent model overrides are no longer stripped — respect agent-level config

        # Load Sovereign Context for Architect (Truncated for clean PR)
        boardroom_path = Path.home() / "taajirah_systems" / "BOARDROOM"
        if boardroom_path.exists():
             ensure_identity("architect", "You are the System Architect. Maintain zero-trust security and uphold the Sovereign Context.")
        
        # Load AIEOS for Sentinel
        ensure_identity("sentinel", "You are Sentinel, the security guardian. Audit system state and enforce safety protocols.")

        agents["list"] = agents_list
        config["agents"] = agents

        # Skill Directories (Sentinel & ClawdCursor)
        skills = config.get("skills", {})
        load_conf = skills.get("load", {})
        extra_dirs = load_conf.get("extraDirs", [])
        paths = [str((Path.home() / "sentinel" / "openclaw-skill").resolve()), 
                 str((Path.home() / ".openclaw" / "workspace" / "skills" / "clawd-cursor").resolve())]
        for p in paths:
            if p not in extra_dirs:
                print(f"➕ Registering skill: {p}")
                extra_dirs.append(p)
                modified = True
        
        if modified:
            load_conf["extraDirs"] = extra_dirs
            skills["load"] = load_conf
            config["skills"] = skills

        if modified:
            with open(config_path, "w") as f: json.dump(config, f, indent=2)
            print("✅ Configuration locked and secured.")
        else:
            print("✅ Configuration is already secure.")

    except Exception as e:
        print(f"❌ Failed to enforce config: {e}")
        sys.exit(1)
    finally:
        if config_path.exists(): os.chmod(config_path, 0o600)

if __name__ == "__main__":
    enforce_config()
