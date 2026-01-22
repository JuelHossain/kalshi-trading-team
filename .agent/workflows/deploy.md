---
description: Build, test, and deploy the complete application
---

# Full Build and Deploy Workflow

Follow these steps to build, test, and deploy the trading bot:

1. **Pull latest changes**
// turbo
```bash
cd /home/jrrahman01/workspace/active/kalshi-trading-team && git pull
```

2. **Install dependencies**
```bash
npm install
cd backend && npm install && cd ..
cd frontend && npm install && cd ..
cd engine && source venv/bin/activate && pip install -r requirements.txt && cd ..
```

3. **Run tests**
```bash
npm run test
```

4. **Build the application**
// turbo
```bash
npm run build
```

5. **Stop existing PM2 processes**
// turbo
```bash
npm run stop
```

6. **Start with PM2**
// turbo
```bash
npm start
```

7. **Verify deployment**
// turbo
```bash
npm run logs
```

8. **Commit and push changes**
```bash
git add .
git commit -m "deploy: [describe changes]"
git push
```
