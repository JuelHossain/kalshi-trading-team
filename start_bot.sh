#!/bin/bash

echo "🔧 Agent 11 (The Mechanic): Initializing Stability Protocol..."

# 1. Build the application (Shared -> Backend -> Frontend)
echo "Building Production Artifacts..."
npm run build

# 2. Start the Ecosystem (Backend + Frontend)
echo "Starting Sentient Alpha via Process Manager..."
npx pm2 start ecosystem.config.cjs

# 3. Save process list
npx pm2 save

echo "✅ Bot is Online!"
echo "📡 Engine API: http://localhost:3002"
echo "📊 HUD (Frontend): http://localhost:3000"
echo "⚠️  REMINDER: Open the HUD in your browser to start the autonomous cycle."
