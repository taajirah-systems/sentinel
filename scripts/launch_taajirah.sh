#!/bin/bash
echo "🚀 Launching Taajirah Core Agent (CLI Mode)..."
# Ensure we are in the project root
PROJECT_ROOT="$(dirname "$0")/.."
cd "$PROJECT_ROOT" || exit

# Use Sentinel's venv for dependencies
VENV_PATH="./.venv"
# Assuming taajirah_core is at the same level as sentinel or elsewhere
# For now, let's keep it as an environment variable or a known location
TAAJIRAH_CORE_PATH="/Users/taajirah_systems/taajirah_core"

if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
else
    echo "Error: Sentinel venv not found at $VENV_PATH"
    exit 1
fi

# Run interactive CLI
adk run "$TAAJIRAH_CORE_PATH"
