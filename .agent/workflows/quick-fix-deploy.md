---
description: Quick fix, test, and redeploy for minor changes
---

# Quick Fix and Deploy

For minor bug fixes or small changes:

1. **Make your code changes**

2. **Run relevant tests**
```bash
# For backend changes
npm run test:backend

# For frontend changes
npm run test:frontend

# For engine changes
cd engine && source venv/bin/activate && python -m pytest
```

3. **Build affected component**
```bash
# Backend only
npm run build:backend

# Frontend only
npm run build:frontend

# Both
npm run build
```

4. **Restart PM2**
// turbo
```bash
npm run stop && npm start
```

5. **Commit changes**
```bash
git add .
git commit -m "fix: [describe the fix]"
git push
```