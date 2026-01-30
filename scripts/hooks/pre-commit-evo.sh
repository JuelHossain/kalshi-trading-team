#!/bin/bash
# Pre-commit hook for automatic documentation evolution
# This hook runs before each commit to analyze changes and update docs synchronously

set -e

# Get the project root (parent of scripts/)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Check if evolution system is enabled
if [ -n "$EVOLUTION_DISABLED" ]; then
    echo "[Evolution] System disabled via EVOLUTION_DISABLED environment variable"
    exit 0
fi

echo "[Evolution] Analyzing staged changes..."

# Run the analyzer to check significance
ANALYSIS_OUTPUT=$(python scripts/evolution/analyzer.py pre-commit --json 2>/dev/null || echo '{"is_significant": false}')
IS_SIGNIFICANT=$(echo "$ANALYSIS_OUTPUT" | python -c "import sys, json; print(json.load(sys.stdin).get('is_significant', False))")

if [ "$IS_SIGNIFICANT" = "True" ] || [ "$IS_SIGNIFICANT" = "true" ]; then
    echo "[Evolution] Significant changes detected - running synchronous updates..."

    # Run sync updates
    python scripts/evolution/orchestrator.py sync

    # Stage any documentation files that were updated
    git add ai-env/

    echo "[Evolution] Documentation updated and staged"
else
    echo "[Evolution] No significant changes detected - skipping sync updates"
fi

# Always succeed - we don't want to block commits
exit 0
