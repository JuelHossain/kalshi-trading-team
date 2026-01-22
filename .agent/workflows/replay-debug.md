---
description: Replay historical data to debug agent decisions
---

# Replay Debug Workflow

Use this workflow to reproduce bugs by re-injecting historical market data:

1. **Locate the historical JSON**
Find the relevant log or snapshot in `engine/history.log` or the `snapshots/` directory.

2. **Prepare the replay environment**
```bash
cd /home/jrrahman01/workspace/active/kalshi-trading-team/engine
source venv/bin/activate
mkdir -p debug/input
```

3. **Copy snapshot to debug input**
```bash
cp [path-to-snapshot.json] debug/input/market_state.json
```

4. **Run the engine in REPLAY mode**
// turbo
```bash
python main.py --mode=replay --input=debug/input/market_state.json
```

5. **Monitor agent reactions**
Check if the Analyst and Auditor make the same (or improved) decisions based on the historical data.

6. **Verify the fix**
Apply your fix and run step 4 again. The `Decision` output should now be correct.

7. **Clean up**
```bash
rm debug/input/market_state.json
```
