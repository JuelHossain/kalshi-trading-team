#!/usr/bin/env bash
# Pull the latest main, rebuild, restart. Run on the mini PC:
#   bash ~/kalshi-trading-team/deploy/update.sh
set -euo pipefail
cd "$HOME/kalshi-trading-team"
git pull --ff-only
.venv/bin/pip install --quiet -r engine/requirements.txt
( cd frontend && npm ci --no-audit --no-fund --silent && npm run build --silent )
systemctl --user restart sentient-alpha
sleep 3
systemctl --user --no-pager --lines=5 status sentient-alpha
