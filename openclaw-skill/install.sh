#!/usr/bin/env bash
#
# Install Sentinel skill for OpenClaw
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
OPENCLAW_SKILLS="${HOME}/.openclaw/skills"
SENTINEL_SKILL="${OPENCLAW_SKILLS}/sentinel"

echo "🛡️  Installing Sentinel skill for OpenClaw"
echo ""

# Create OpenClaw skills directory if needed
if [ ! -d "$OPENCLAW_SKILLS" ]; then
    echo "Creating OpenClaw skills directory..."
    mkdir -p "$OPENCLAW_SKILLS"
fi

# Remove existing installation
if [ -d "$SENTINEL_SKILL" ] || [ -L "$SENTINEL_SKILL" ]; then
    echo "Removing existing Sentinel skill..."
    rm -rf "$SENTINEL_SKILL"
fi

# Create skill directory
mkdir -p "$SENTINEL_SKILL"

# Copy skill files
echo "Copying skill files..."
cp "$SCRIPT_DIR/skill.yaml" "$SENTINEL_SKILL/"
cp "$SCRIPT_DIR/sentinel_exec.py" "$SENTINEL_SKILL/"
cp "$SCRIPT_DIR/constitution.yaml" "$SENTINEL_SKILL/"
cp "$SCRIPT_DIR/README.md" "$SENTINEL_SKILL/"

# Copy Sentinel core package
echo "Copying Sentinel core..."
cp -r "$PARENT_DIR/sentinel" "$SENTINEL_SKILL/"
cp "$PARENT_DIR/sentinel_main.py" "$SENTINEL_SKILL/"

# Copy .env.example if it exists
if [ -f "$PARENT_DIR/.env.example" ]; then
    cp "$PARENT_DIR/.env.example" "$SENTINEL_SKILL/"
fi

# Create logs directory
mkdir -p "$SENTINEL_SKILL/logs"

echo ""
echo "✅ Sentinel skill installed to: $SENTINEL_SKILL"
echo ""
echo "Next steps:"
echo "  1. Copy .env.example to .env and add your GOOGLE_API_KEY"
echo "     cp $SENTINEL_SKILL/.env.example $SENTINEL_SKILL/.env"
echo ""
echo "  2. Edit constitution.yaml to customize security policy"
echo "     $SENTINEL_SKILL/constitution.yaml"
echo ""
echo "  3. Restart OpenClaw to load the skill"
echo ""
