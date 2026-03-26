#!/bin/bash
echo "📊 Launching Sentinel Dashboard..."
cd "$(dirname "$0")/.." || exit
source .venv/bin/activate
python scripts/dashboard.py
