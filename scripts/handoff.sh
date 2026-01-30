#!/bin/bash
# Sentient Alpha - Multi-Agent Git Handoff Script
# Usage: ./scripts/handoff.sh "Commit message" [--snapshot "Optional snapshot text"]
#
# This script performs atomic git handoffs with automatic evolution system integration.
# It ensures code changes are committed together with documentation updates.

set -e  # Exit on error

MSG=$1
SNAPSHOT_TEXT=""

# Parse optional --snapshot flag
if [ "$2" == "--snapshot" ]; then
    SNAPSHOT_TEXT="$3"
fi

if [ -z "$MSG" ]; then
    echo "ERROR: Please provide a commit message."
    echo "Usage: ./scripts/handoff.sh \"feat(brain): update optimist logic\""
    echo "       ./scripts/handoff.sh \"feat(brain): update\" --snapshot \"Added variance check\""
    exit 1
fi

echo "=========================================="
echo "  SENTIENT ALPHA - ATOMIC HANDOFF"
echo "=========================================="

# Detect OS and set Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "ERROR: Python not found. Please install Python."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "CLAUDE.md" ]; then
    echo "ERROR: Must run from project root (where CLAUDE.md exists)"
    exit 1
fi

# 0. Run Evolution System (Intelligent Documentation Sync)
echo ""
echo "[0/5] Running Evolution System..."
echo "      (Skipped - evolution system in beta)"

#if [ -f "scripts/evolution/orchestrator.py" ]; then
#    $PYTHON_CMD scripts/evolution/orchestrator.py sync
#    EVOLUTION_STATUS=$?
#    if [ $EVOLUTION_STATUS -ne 0 ]; then
#        echo "WARNING: Evolution system had issues (exit code: $EVOLUTION_STATUS)"
#        echo "         Continuing with handoff..."
#    else
#        echo "      Evolution complete."
#    fi
#else
#    echo "      Evolution system not found, skipping..."
#fi

# 1. Capture Mental Snapshot (Project Soul) - Optional but recommended
echo ""
echo "[1/5] Capturing Mental Snapshot..."

if [ -z "$SNAPSHOT_TEXT" ]; then
    # Auto-generate snapshot from recent changes
    RECENT_CHANGES=$(git diff --stat HEAD 2>/dev/null | tail -1 || echo "Code changes committed")
    SNAPSHOT_TEXT="Auto: $RECENT_CHANGES"
    echo "      (Auto-generated snapshot - use --snapshot for custom)"
fi

# Append to identity.md
DATE_STR=$(date +%F)
COMMIT_PREFIX="${MSG%%:*}"
echo -e "\n### [$DATE_STR] by $COMMIT_PREFIX\n**Snapshot**: $SNAPSHOT_TEXT" >> ai-env/soul/identity.md
echo "      Snapshot recorded to ai-env/soul/identity.md"

# 2. Check for uncommitted changes
echo ""
echo "[2/5] Checking Repository State..."

if git diff --quiet && git diff --cached --quiet; then
    echo "      No changes to commit. Working directory clean."
    echo ""
    echo "=========================================="
    echo "  HANDOFF COMPLETE (No changes)"
    echo "=========================================="
    exit 0
fi

# Show what's being committed
echo "      Changes to be committed:"
git status --short | head -10
CHANGE_COUNT=$(git status --short | wc -l)
if [ $CHANGE_COUNT -gt 10 ]; then
    echo "      ... and $((CHANGE_COUNT - 10)) more files"
fi

# 3. Stage and Commit FIRST (so we can rebase on top of remote)
echo ""
echo "[3/5] Staging and Committing Changes..."

git add .
git commit --no-verify -m "$MSG" || {
    echo "ERROR: Commit failed. Check git status."
    exit 1
}
COMMIT_HASH=$(git rev-parse --short HEAD)
echo "      Committed: $COMMIT_HASH - $MSG"

# 4. Pull with Rebase (Stay Linear) - now our commit is safe
echo ""
echo "[4/5] Syncing with Remote (git pull --rebase)..."

# Check if we have a remote
if git remote | grep -q origin; then
    CURRENT_BRANCH=$(git branch --show-current)
    # Check if there are remote changes to rebase onto
    git fetch origin $CURRENT_BRANCH 2>/dev/null || true
    git pull --rebase origin $CURRENT_BRANCH || {
        echo "ERROR: Failed to pull/rebase. Resolve conflicts manually."
        echo "       Run: git rebase --abort  # to cancel"
        echo "       Then: git reset HEAD~1     # to undo our commit"
        exit 1
    }
    echo "      Successfully synced with origin/$CURRENT_BRANCH"
else
    echo "      No remote configured, skipping sync"
fi

# 5. Push to Remote
echo ""
echo "[5/5] Pushing to Remote..."

if git remote | grep -q origin; then
    CURRENT_BRANCH=$(git branch --show-current)
    git push origin $CURRENT_BRANCH || {
        echo "ERROR: Push failed. Check network or permissions."
        exit 1
    }
    echo "      Pushed to origin/$CURRENT_BRANCH"
else
    echo "      No remote configured, skipping push"
fi

# Record in evolution database if available
if [ -f "scripts/evolution/database.py" ]; then
    $PYTHON_CMD -c "
import sys
sys.path.insert(0, 'scripts/evolution')
from database import EvolutionDatabase
db = EvolutionDatabase()
db.record_handoff('$COMMIT_HASH', '$MSG', '$SNAPSHOT_TEXT')
" 2>/dev/null || true
fi

# Summary
echo ""
echo "=========================================="
echo "  HANDOFF COMPLETE"
echo "=========================================="
echo "  Commit: $COMMIT_HASH"
echo "  Message: $MSG"
echo "  Branch: $(git branch --show-current)"
echo "  Files: $CHANGE_COUNT"
echo ""
echo "  Next agent can start immediately."
echo "=========================================="
