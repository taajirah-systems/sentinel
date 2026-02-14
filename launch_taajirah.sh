#!/bin/bash
echo "🚀 Launching Taajirah Core Agent (CLI Mode)..."

# Use Sentinel's venv for dependencies
VENV_PATH="/Users/<user>/Documents/Sentinel/.venv"
TAAJIRAH_CORE_PATH="/Users/<user>/Documents/Manual_Library/Github/Taajirah_Systems/taajirah_core"

if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
else
    echo "Error: Sentinel venv not found at $VENV_PATH"
    exit 1
fi

# Run interactive CLI
adk run "$TAAJIRAH_CORE_PATH"
