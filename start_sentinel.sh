#!/bin/bash
set -e

echo "🛡️  Sentinel Hardened Launch Sequence Initiated..."

# 1. Enforce Configuration
echo "🔒 Locking OpenClaw configuration..."
python3 enforce_config.py

# 2. Kill Stale Servers (Robust)
echo "🧹 Cleaning up port 8765..."
PID=$(lsof -t -i:8765 || true)
if [ -n "$PID" ]; then
  echo "   Killing old process on port 8765 (PID: $PID)"
  kill -9 $PID
fi

# 3. Start Sentinel Server (Background)
echo "🧠 Starting Sentinel Brain..."
source .venv/bin/activate
python -u sentinel_server.py > /tmp/sentinel.log 2>&1 &
SERVER_PID=$!
echo "   PID: $SERVER_PID"

# Wait for server to be ready (simple sleep for now)
sleep 2

# 4. Start OpenClaw Gateway (Foreground)
echo "🦞 Releasing the Lobster..."
openclaw gateway

# Cleanup on exit
kill $SERVER_PID
