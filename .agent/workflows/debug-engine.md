---
description: Debug Python engine and agent issues
---

# Debug Engine Issues

When the Python engine is not working correctly:

1. **Check engine logs**
// turbo
```bash
cd /home/jrrahman01/workspace/active/kalshi-trading-team && tail -f engine/history.log
```

2. **Check PM2 logs for engine process**
// turbo
```bash
npx pm2 logs sentient-alpha-engine
```

3. **Test engine standalone**
```bash
cd engine && source venv/bin/activate && python main.py
```

4. **Verify API keys**
```bash
cat engine/.env | grep -E "GEMINI_API_KEY|KALSHI_API_KEY|RAPID_API_KEY"
```

5. **Check agent outputs individually**
```bash
cd engine && source venv/bin/activate
python -m agents.scout --test
python -m agents.interceptor --test
python -m agents.analyst --test
```

6. **Verify model names**
Ensure all Gemini API calls use valid model names (e.g., `gemini-1.5-flash`)

7. **Check process status**
// turbo
```bash
npx pm2 status
```
