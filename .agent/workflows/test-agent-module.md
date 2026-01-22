---
description: Test a specific Python agent module in isolation
---

# Test Agent Module Workflow

Test an individual agent module before integration:

1. **Activate Python virtual environment**
```bash
cd /home/jrrahman01/workspace/active/kalshi-trading-team/engine && source venv/bin/activate
```

2. **Run the specific agent test**
```bash
python -m agents.[agent_name] --test
```

3. **Verify Output**
- Check that the agent returns valid JSON with expected fields.
- Test error handling by simulating API failures.
- Ensure the agent completes within expected time constraints (performance check).