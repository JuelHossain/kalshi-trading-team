---
description: Update API keys and environment variables
---

# Update Environment Variables

Safely update API keys and environment variables:

1. **Edit backend environment file**
```bash
nano /home/jrrahman01/workspace/active/kalshi-trading-team/backend/.env
```

2. **Edit engine environment file**
```bash
nano /home/jrrahman01/workspace/active/kalshi-trading-team/engine/.env
```

3. **Edit root environment file (if needed)**
```bash
nano /home/jrrahman01/workspace/active/kalshi-trading-team/.env.local
```

4. **Verify required keys are set**
```bash
# Check backend
grep -E "GEMINI_API_KEY|KALSHI_API_KEY" /home/jrrahman01/workspace/active/kalshi-trading-team/backend/.env

# Check engine
grep -E "GEMINI_API_KEY|KALSHI_API_KEY|RAPID_API_KEY" /home/jrrahman01/workspace/active/kalshi-trading-team/engine/.env
```

5. **Restart services to apply changes**
// turbo
```bash
cd /home/jrrahman01/workspace/active/kalshi-trading-team && npm run stop && npm start
```

6. **Test API connectivity**
```bash
cd engine && source venv/bin/activate
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Keys loaded:', bool(os.getenv('GEMINI_API_KEY')))"
```

7. **Monitor logs for errors**
// turbo
```bash
npm run logs
```

**Security Note:** Never commit `.env` files to git. They are already in `.gitignore`.
