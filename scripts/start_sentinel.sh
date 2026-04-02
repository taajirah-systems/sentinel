#!/bin/bash

# Sentinel: Sovereign Security Guardian
# Optimized for ZeroClaw Integration & Privacy

# 1. Environment & Initialization
echo "🛡️  Initializing Sentinel Security Layers..."
# Ensure we are in the project root
cd "$(dirname "$0")/.." || exit
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

# 2. Port Check & Cleanup
for PORT in 8765 18790; do
  PID=$(lsof -ti :$PORT)
  if [ ! -z "$PID" ]; then
    echo "⚠️  Port $PORT occupied by PID $PID. Clearing..."
    kill -9 $PID
  fi
done

echo "   Aggressively killing any lingering instances..."
pkill -9 -f "scripts/monitoring/" || true
pkill -9 -f "src/api/server.py" || true
pkill -9 -f "src/context_monitor.py" || true
pkill -9 -f "src/model_monitor.py" || true
sleep 2

# 3. Start Sentinel Server (Brain)
echo "🧠 Starting Sentinel Brain..."
source .venv/bin/activate
python -u -m src.api.server > /tmp/sentinel.log 2>&1 &
SERVER_PID=$!

# 4. Start New Upstream Monitors
echo "👀 Starting Context & Model Monitors..."
python -u src/context_monitor.py > /tmp/context_monitor.log 2>&1 &
MONITOR_PID=$!
python -u src/model_monitor.py > /tmp/model_monitor.log 2>&1 &
MONITOR_MODEL_PID=$!

# 5. Start Autonomic Healing (Phase 7 upgrade)
echo "🩹 Starting Autonomic Healing Monitor..."
python -u scripts/monitoring/autonomic.py > /tmp/sentinel_healing.log 2>&1 &
MONITOR_HEAL_PID=$!

# 6. OpenClaw Gateway — DISABLED (dmPolicy set to disabled; auto-replies stopped)
# openclaw gateway --force > /tmp/openclaw.log 2>&1 &
# OPENCLAW_PID=$!
OPENCLAW_PID=""

echo "✅ Sentinel Security Layers are active."
echo "   (OpenClaw Gateway is DISABLED — WhatsApp auto-replies are off)"

# Cleanup on exit
trap 'kill $SERVER_PID $MONITOR_PID $MONITOR_MODEL_PID $MONITOR_HEAL_PID 2>/dev/null' EXIT

# Keep script alive to maintain background monitors
wait
