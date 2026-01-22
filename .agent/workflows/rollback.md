---
description: Rollback to previous deployment
---

# Rollback Deployment

When something goes wrong with the latest deployment:

1. **Stop current processes**
// turbo
```bash
cd /home/jrrahman01/workspace/active/kalshi-trading-team && npm run stop
```

2. **Check git log to find last working commit**
```bash
git log --oneline -10
```

3. **Revert to previous commit**
```bash
git reset --hard [commit-hash]
```

4. **Reinstall dependencies (if needed)**
```bash
npm install
cd backend && npm install && cd ..
cd frontend && npm install && cd ..
```

5. **Rebuild application**
// turbo
```bash
npm run build
```

6. **Restart services**
// turbo
```bash
npm start
```

7. **Verify rollback**
// turbo
```bash
npm run logs
```

8. **Create fix branch for the issue**
```bash
git checkout -b fix/[issue-description]
```

**Note:** Only use this for emergency rollbacks. For planned rollbacks, use `git revert` instead to maintain history.
