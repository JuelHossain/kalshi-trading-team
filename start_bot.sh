#!/bin/bash

echo "🔧 Agent 11 (The Mechanic): Initializing Stability Protocol..."

# 1. Use npx to run PM2 without global install
echo "Using npx to manage process..."


# 2. Build the application
echo "Building Production Artifacts..."
npm run build

# 3. Start the Ecosystem
echo "Starting Bot via Process Manager..."
npx pm2 start ecosystem.config.cjs

# 4. Save list related to system reboot
npx pm2 save

echo "✅ Bot is Online at http://YOUR_VPS_IP:8501"
echo "⚠️  REMINDER: You must keep a BROWSER TAB OPEN at this URL for the Orchestrator (Agent 1) to run."
