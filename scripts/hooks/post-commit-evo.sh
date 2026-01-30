#!/bin/bash
# Post-commit hook for automatic documentation evolution
# This hook runs after each commit to handle async documentation updates

# Get the project root (parent of scripts/)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Check if evolution system is enabled
if [ -n "$EVOLUTION_DISABLED" ]; then
    echo "[Evolution] System disabled via EVOLUTION_DISABLED environment variable"
    exit 0
fi

# Get commit information
COMMIT_HASH=$(git rev-parse HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B)
BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "[Evolution] Queuing async documentation updates for commit ${COMMIT_HASH:0:8}..."

# Run async updates in the background
# This allows the commit to complete without waiting for documentation updates
nohup python scripts/evolution/orchestrator.py async \
  --commit "$COMMIT_HASH" \
  --message "$COMMIT_MSG" \
  > /tmp/evolution_async.log 2>&1 &

# Store the PID for potential monitoring
EVO_PID=$!
echo "[Evolution] Async updates running in background (PID: $EVO_PID)"

# Optionally, you can wait a moment to catch immediate errors
sleep 0.5
if ! kill -0 $EVO_PID 2>/dev/null; then
    echo "[Evolution] Warning: Async process may have exited immediately"
    echo "[Evolution] Check /tmp/evolution_async.log for details"
fi

exit 0
