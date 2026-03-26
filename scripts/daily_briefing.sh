#!/bin/bash
echo "🤖 Starting Daily Briefing Workflow..."
cd "$(dirname "$0")/.." || exit
source .venv/bin/activate
python scripts/daily_briefing.py
