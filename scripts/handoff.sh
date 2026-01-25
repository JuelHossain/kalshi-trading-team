#!/bin/bash
# Sentient Alpha - Multi-Agent Git Handoff Script
# Usage: ./scripts/handoff.sh "Commit message"

MSG=$1

if [ -z "$MSG" ]; then
    echo "ERROR: Please provide a commit message."
    echo "Usage: ./scripts/handoff.sh \"feat(brain): update optimist logic\""
    exit 1
fi

echo "--- STARTING ATOMIC HANDOFF ---"

# -1. Capture Mental Snapshot (Project Soul)
read -p "Enter Mental Snapshot (AI Intuition/Identity update): " SNAPSHOT
if [ -z "$SNAPSHOT" ]; then
    echo "ERROR: Snapshot required for Project Soul. Stay Alive protocol mandate."
    exit 1
fi
echo -e "\n### [$(date +%F)] by ${MSG%%:*}\n**Snapshot**: $SNAPSHOT" >> ai-env/soul/identity.md

# 0. Verify Symlink Integrity (Stay Alive Protocol)
echo "[0/4] Verifying Symlink Integrity..."
if [ ! -L ".opencode/skills" ] || [ ! -L ".agent/workflows" ]; then
    echo "ERROR: Symlinks broken. Run repair protocol."
    exit 1
fi

# 1. Sync Intelligence
echo "[1/4] Syncing Skills and Workflows..."
# python3 -c "import os; print('Syncing...')" # Placeholder for future logic check
# In a real scenario, this would trigger the /sync logic

# 2. Pull with Rebase (Stay Linear)
echo "[2/4] Pulling latest changes (rebase)..."
git pull --rebase origin opencode

# 3. Add and Commit Atomically
echo "[3/4] Committing code and knowledge context..."
git add .
git commit -m "$MSG"

# 4. Push to Sovereignty Branch
echo "[4/4] Pushing to opencode branch..."
git push origin opencode

echo "--- HANDOFF COMPLETE ---"
echo "Next agent: Ready for entry."
