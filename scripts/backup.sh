#!/usr/bin/env bash

# Sentinel, OpenClaw, and NemoClaw Master Backup Script
# This script compresses the entire architecture into a single tarball on your Desktop.

BACKUP_NAME="sentinel_architecture_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
BACKUP_DEST="$HOME/Desktop/$BACKUP_NAME"

echo "🛡️ Starting Master Sentinel Backup..."
echo "Destination: $BACKUP_DEST"
echo "------------------------------------------------"

# Folders to backup
TARGETS=(
  "$HOME/sentinel"
  "$HOME/.openclaw"
)

# If NemoClaw local dir exists, add it to backup
if [ -d "$HOME/nemoclaw-lab" ]; then
  TARGETS+=("$HOME/nemoclaw-lab")
fi

echo "Compressing..."
# Create the compressed tarball without printing every single file (keeps output clean)
tar -czf "$BACKUP_DEST" "${TARGETS[@]}"

if [ $? -eq 0 ]; then
  echo "✅ Backup Successful!"
  echo "📦 Saved to: $BACKUP_DEST"
  # Show the file size
  ls -lh "$BACKUP_DEST"
else
  echo "❌ Backup Failed. Please check permissions."
fi
