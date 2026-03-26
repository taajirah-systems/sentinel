#!/bin/bash
export NVM_DIR="$HOME/.nvm"
[s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
# Ensure we are in the project root
cd "$(dirname "$0")/.." || exit

# Try to use the version we know works, or default
nvm use v22.14.0 > /dev/null 2>&1 || nvm use default > /dev/null 2>&1

echo "🦞 Launching OpenClaw TUI..."
openclaw tui "$@"
