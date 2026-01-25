# Intelligence Core Upgrade Walkthrough

This walkthrough details the successful upgrade of the Kalshi Trading Engine's "Intelligence Core". The upgrade focused on modernizing the AI stack, adding external market awareness, and verifying mathematical decision-making logic.

## 1. Gemini SDK Migration (Critical)
We successfully migrated the `Soul` and `Brain` agents from the deprecated `google-generativeai` library to the new, standard `google-genai` (v1.0) SDK.

### Key Changes
- **Dependency**: Replaced `google-generativeai` with `google-genai` in `requirements.txt`.
- **Client Initialization**: Moved from global configuration to instance-based clients.
  ```python
  # Old
  genai.configure(api_key=key)
  model = genai.GenerativeModel("gemini-pro")

  # New
  from google import genai
  client = genai.Client(api_key=key)
  ```
- ** Generation**: Updated generation calls to match the new API signature.
  ```python
  # Old
  response = model.generate_content(prompt)

  # New
  response = client.models.generate_content(model="gemini-1.5-pro", contents=prompt)
  ```

## 2. Context Awareness ("Blind Brain" Fix)
The **Senses** agent can now "see" the world outside of Kalshi. We integrated `duckduckgo-search` to fetch real-time news and context for active markets, allowing the **Brain** to make informed decisions rather than relying solely on price action.

### Implementation
- **Senses Agent (`engine/agents/senses.py`)**:
    - Added `fetch_market_context(ticker, title)` method.
    - Uses `DDGS` (DuckDuckGo Search) to find top 3 news snippets related to the market title.
    - Appends this context to the opportunity package sent to the Brain.
- **Brain Agent (`engine/agents/brain.py`)**:
    - Updated the Debate Prompt to include a `NEWS/CONTEXT` section.
    - Explicitly instructs the AI personas (Optimist/Critic) to cite the provided news in their reasoning.

## 3. Mathematical Verification
We implemented a rigorous unit testing suite to ensure the Brain's decision-making math is sound and dependable.

### Verified Logic
1.  **High Probability / Low Payoff**: Confirmed positive Expected Value (EV).
2.  **Low Probability / High Payoff**: Confirmed positive EV (Longshot logic).
3.  **Negative EV**: Confirmed that the system successfully identifies and rejects unfavorable trades (Coin flip with negative expectancy).

### Test Results
All 5 unit tests passed successfully.

```bash
> pytest tests/unit/
======================= test session starts ========================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0
rootdir: /home/jrrahman01/workspace/active/kalshi-trading-team

tests/unit/test_brain.py ...                                 [ 60%]
tests/unit/test_senses.py ..                                 [100%]

================== 5 passed, 12 warnings in 4.15s ==================
```

## 4. System Status
The engine was successfully started with the new components active.

```log
[GHOST] Initializing 4 Mega-Agent Pillars...
[SOUL] Soul awakening. Executive Director online.
[SENSES] Senses online. 24/7 passive surveillance activated.
[BRAIN] Brain online. Intelligence & Decision engine ready.
[HAND] Hand online. Precision strike capability ready.
[GHOST] SYSTEM ONLINE - 4 Pillars Active.
```

## Next Steps
- Monitor live performance to ensure `duckduckgo-search` remains reliable (rate limits).
- Observe Brain's debate logs to confirm it is effectively using the new context.
