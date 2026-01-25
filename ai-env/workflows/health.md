---
description: Perform a full system health check (React + Python)
---

This workflow verifies the connectivity of the 2-tier architecture.

// turbo
1. Run diagnostic script:
```bash
python3 ai-env/skills/core-ops/scripts/health_check.py
```

2. If any service is offline, check the PM2 status:
```bash
npx pm2 status
```
