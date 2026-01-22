---
description: Switch between paper trading and live trading
---

# Toggle Trading Mode

**⚠️ CAUTION: Live trading involves real money**

1. **Edit ecosystem config**
```bash
nano /home/jrrahman01/workspace/active/kalshi-trading-team/ecosystem.config.cjs
```

2. **Change IS_PAPER_TRADING value**
- For paper trading: `IS_PAPER_TRADING: "true"`
- For live trading: `IS_PAPER_TRADING: "false"`

3. **Save and exit**
Press `Ctrl+X`, then `Y`, then `Enter`

4. **Restart the engine**
// turbo
```bash
cd /home/jrrahman01/workspace/active/kalshi-trading-team && npm run stop && npm start
```

5. **Verify mode in logs**
// turbo
```bash
npx pm2 logs sentient-alpha-engine | grep -i "trading mode"
```

6. **Monitor first few cycles closely**
Watch for any unexpected behavior before leaving unattended

7. **Check vault balance**
```bash
npx pm2 logs sentient-alpha-engine | grep -i "vault"
```
