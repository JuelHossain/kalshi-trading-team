---
description: Monitor system health and performance
---

# Monitor System Health

Check the health and performance of all system components:

1. **Check PM2 process status**
// turbo
```bash
npx pm2 status
```

2. **View all logs in real-time**
// turbo
```bash
npx pm2 logs
```

3. **Check specific component logs**
```bash
# Backend logs
npx pm2 logs kalshi-alpha-backend

# Frontend logs
npx pm2 logs kalshi-alpha-frontend

# Engine logs
npx pm2 logs sentient-alpha-engine
```

4. **Check system resource usage**
// turbo
```bash
npx pm2 monit
```

5. **View engine history log**
// turbo
```bash
tail -n 100 /home/jrrahman01/workspace/active/kalshi-trading-team/engine/history.log
```

6. **Check API connectivity**
```bash
cd /home/jrrahman01/workspace/active/kalshi-trading-team/engine
source venv/bin/activate
python -c "import os; from google import generativeai as genai; genai.configure(api_key=os.getenv('GEMINI_API_KEY')); print('Gemini API: OK')"
```

7. **Check disk space**
// turbo
```bash
df -h
```

8. **Check memory usage**
// turbo
```bash
free -h
```
