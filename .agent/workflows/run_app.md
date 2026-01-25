---
description: How to run the application in development or production mode
---

This workflow describes the steps to install dependencies and run the Kalshi Trading Team application.

## Prerequisites

Ensure you have the following installed:
- Node.js (v18+)
- Python (v3.10+)
- pip

## 1. Install Dependencies

You must install dependencies for the root, backend, frontend, and python engine.

### Root Dependencies
```bash
npm install
```

### Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

### Python Engine Dependencies
```bash
python3 -m pip install -r engine/requirements.txt
```

## 2. Environment Configuration

Ensure you have your `.env` files set up.
- `.env.local` (Root): May be used by specific scripts.

## 3. Running the Application

### Option A: Development Mode (Hot Reload)
Use this for development. It runs the backend, frontend, and engine simultaneously with log output to the terminal.

```bash
npm run dev
```

### Option B: Production Mode (PM2)
Use this for a stable background execution.

**Using the Helper Script:**
This script builds the frontend and backend, then starts everything with PM2.
```bash
// turbo
./start_bot.sh
```

**Manual Production Startup:**
1. Build the project:
   ```bash
   npm run build
   ```
2. Start with PM2:
   ```bash
   npx pm2 start ecosystem.config.cjs
   ```

## 4. Viewing the Application

- **Frontend HUD**: http://localhost:3000 (or the port shown in terminal)
- **PM2 Dashboard**:
  To view a visual dashboard of the running processes (in production mode):
  ```bash
  npx pm2 monit
  ```
