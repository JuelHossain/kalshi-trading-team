# Task: Upgrade Intelligence Core

## Goal
Upgrade the AI decision-making capabilities ("The Mind") by fixing deprecated libraries, adding external context to market analysis, and verifying mathematical models.

---

## Phase 1: Gemini SDK Migration (Critical)
**Context**: The `google.generativeai` library is deprecated and printing warnings.
- [ ] Uninstall `google-generativeai` and install `google-genai` (or latest recommended `google-generativeai` version if the warning was about a specific version, but `google.genai` is the new standard).
- [ ] Refactor `engine/agents/soul.py`:
    - Update import statements.
    - Update `generate_content` calls to match new API signature.
- [ ] Refactor `engine/agents/brain.py`:
    - Update import statements.
    - Update `generate_content` calls and response parsing.
- [ ] Verify: Run engine and ensure no deprecation warnings appear during startup/evolution.

## Phase 2: "Blind Brain" Fix (Context Awareness)
**Context**: The Brain currently only sees the market title. It needs external news/data to make informed decisions.
- [ ] Enhancing `engine/agents/senses.py`:
    - [ ] Add a `fetch_market_context(ticker, title)` method.
    - [ ] Implement a simple search/scraping retrieval (e.g., using `duckduckgo-search` python package or similar lightweight tool).
    - [ ] Append top 3 news headlines/summaries to the `opportunity` dictionary.
- [ ] Enhancing `engine/agents/brain.py`:
    - [ ] Update the `run_debate` prompt to include the new `external_context` (news snippets).
    - [ ] Instruct the AI to explicitly reference the news in its debate.

## Phase 3: Mathematical Verification (Trust but Verify)
**Context**: We need to ensure the Monte Carlo simulation correctly calculates EV and variance.
- [ ] Create `tests/unit/test_brain.py`:
    - [ ] Test Case 1: High Probability (80%), Low Payoff -> Should Approve.
    - [ ] Test Case 2: Low Probability (20%), High Payoff -> Should Reject (or Veto based on variance).
    - [ ] Test Case 3: 50/50 Coin Flip with negative EV -> Should Veto.
- [ ] Create `tests/unit/test_senses.py`:
    - [ ] Test context fetching (mocked network calls).

## Phase 4: Execution & Verification
- [ ] Run `python3 engine/main.py`.
- [ ] Monitor logs: Ensure "Context" is showing up in Brain analysis logs.
- [ ] Run tests: `pytest tests/unit/test_brain.py`.

---

## Technical Notes
- **Library**: Consider `duckduckgo-search` for free, keyless search results in Python.
- **Prompt Engineering**: The prompt in `brain.py` needs to be robust against empty context (handle cases where no news is found).
