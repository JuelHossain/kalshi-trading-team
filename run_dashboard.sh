#!/bin/bash
# Launch the dashboard (React frontend) in dev mode against a running engine.
#
# This script previously installed dashboard/requirements.txt and ran
# dashboard/app.py via Streamlit. There is no dashboard/ directory in this
# repository -- that dashboard is frontend/, a React app. The script could
# never have worked.
#
# Start the engine first (see RUNBOOK.md); this serves the UI and proxies
# /api to the engine on :3002.

set -e

cd "$(dirname "$0")/frontend"

if [ ! -d node_modules ]; then
  echo "Installing frontend dependencies..."
  npm ci
fi

echo "Dashboard: http://localhost:5173  (engine expected on :3002)"
npm run dev
