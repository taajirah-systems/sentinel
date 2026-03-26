#!/bin/bash
# Wrapper to launch context_monitor with correct CWD and venv
cd /Users/taajirah_systems/sentinel || exit 1
exec /Users/taajirah_systems/sentinel/.venv/bin/python -u src/context_monitor.py
