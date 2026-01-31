# GHOST ENGINE v3.0 - CRITICAL LOGIC AUDIT REPORT
**Auditor:** The Critic (Risk-Biased Committee Member)
**Date:** 2025-01-30
**Scope:** All files in `engine/` (main.py, agents/, core/)
**Core Directive:** Protect the hard floor ($255) at all costs

---

## EXECUTIVE SUMMARY

**CRITICAL RISK LEVEL:** MEDIUM-HIGH

The trading engine demonstrates solid foundational safety architecture but contains several concerning gaps that could lead to:
1. Liquidity trap scenarios in low-volume markets
2. Hard floor bypass through timing race conditions
3. Variance calculation vulnerabilities during AI fallbacks
4. Order execution without real-time slippage verification

**RECOMMENDATION:** Address CRITICAL issues before deploying with real capital.

---

## TABLE OF CONTENTS

1. [Hard Floor Protection Analysis](#1-hard-floor-protection-analysis)
2. [Liquidity & Slippage Risks](#2-liquidity--slippage-risks)
3. [Variance Sensitivity Analysis](#3-variance-sensitivity-analysis)
4. [Safety Protocol Vulnerabilities](#4-safety-protocol-vulnerabilities)
5. [Error Handling & Synapse Gaps](#5-error-handling--synapse-gaps)
6. [Prioritized Fix Recommendations](#6-prioritized-fix-recommendations)

---

## 1. HARD FLOOR PROTECTION ANALYSIS

### 1.1 CRITICAL: Race Condition in Hard Floor Check

**File:** `engine/main.py:165-169`

```python
# Hard floor check ($255)
if self.vault.current_balance < 25500:
    print(f"[GHOST] HARD FLOOR BREACH ($255). EMERGENCY LOCKDOWN.")
    return False
```

**ISSUE:** The hard floor check in `authorize_cycle()` happens BEFORE balance updates are committed. A malicious sequence:
1. Cycle starts at $256 (above floor)
2. Trade executes, balance drops to $254
3. Next cycle starts before vault is updated
4. Hard floor check passes (still sees $256 in memory)

**FIX:** Implement atomic balance reads with database source-of-truth.

**Priority:** CRITICAL

---

### 1.2 HIGH: Multiple Hard Floor Definitions

**Files:**
- `engine/main.py:165` → `25500` ($255)
- `engine/agents/hand.py:207` → `25500` ($255)
- `engine/agents/soul.py:39` → `HARD_FLOOR_CENTS = 25500`

**ISSUE:** Three separate definitions of the same threshold. If one is changed during refactoring,不一致性 could create bypass scenarios.

**FIX:** Single source of truth in `vault.py` and import everywhere.

**Priority:** HIGH

---

### 1.3 MEDIUM: Kill Switch Threshold Mismatch

**File:** `engine/core/vault.py:47-48`

```python
threshold = self.PRINCIPAL_CAPITAL_CENTS * self.KILL_SWITCH_THRESHOLD_PCT
# $300 * 0.85 = $255
```

**ISSUE:** Kill switch activates at 85% ($255) but hardcoded check uses $255 directly. If `PRINCIPAL_CAPITAL_CENTS` changes from env var, the two checks diverge.

**FIX:** Use percentage consistently or document why $255 is absolute.

**Priority:** MEDIUM

---

## 2. LIQUIDITY & SLIPPAGE RISKS

### 2.1 CRITICAL: No Real-Time Order Book Validation

**File:** `engine/agents/hand.py:131-154`

```python
async def snipe_check(self, ticker: str) -> dict:
    orderbook = await self.kalshi_client.get_orderbook(ticker)
    best_bid = orderbook.get("bids", [{}])[0].get("price", 45)
    best_ask = orderbook.get("asks", [{}])[0].get("price", 55)
    spread = best_ask - best_bid

    if spread > 5:  # More than 5¢ spread = potential slippage
        return {"valid": False, "reason": f"Spread too wide: {spread}¢"}
```

**ISSUES:**
1. No validation that orderbook contains actual liquidity (volume at each price level)
2. Empty list fallback (`[{}]`) silently passes with default prices
3. No check for minimum order size vs available liquidity
4. 5¢ spread threshold is arbitrary and not market-cap-adjusted

**SCENARIO:** Ticker has spread of 4¢ but only $10 available at best_ask. Hand tries to buy $75 → massive slippage on remaining volume.

**FIX:**
```python
# Add liquidity depth validation
bid_volume = sum(b.get("amount", 0) for b in bids[:3])
ask_volume = sum(a.get("amount", 0) for a in asks[:3])
min_liquidity = stake * 2  # 2x cushion
if ask_volume < min_liquidity:
    return {"valid": False, "reason": f"Insufficient depth: ${ask_volume}"}
```

**Priority:** CRITICAL

---

### 2.2 HIGH: Stale Market Data in Opportunity Queue

**File:** `engine/agents/senses.py:230-284`

**ISSUE:** Opportunities are queued with `yes_price` at scan time. By the time Brain processes and Hand executes, prices may have moved significantly. No TTL or price staleness check.

**FIX:** Add `timestamp` to Opportunity and reject if `now() - timestamp > 60 seconds`.

**Priority:** HIGH

---

### 2.3 MEDIUM: No Volume Validation in Top 10 Selection

**File:** `engine/agents/senses.py:38`

```python
MIN_LIQUIDITY = 0  # $0 minimum liquidity for Demo/Testing
```

**ISSUE:** Minimum liquidity is set to zero "for testing" but this value propagates to production. No enforcement that top 10 markets have minimum dollar volume.

**FIX:** Set `MIN_LIQUIDITY = 1000` ($10 minimum) and add filter in `select_top_opportunities`.

**Priority:** MEDIUM

---

## 3. VARIANCE SENSITIVITY ANALYSIS

### 3.1 CRITICAL: AI Fallback Bypasses Variance Check

**File:** `engine/agents/brain.py:289-302`

```python
async def run_debate(self, opportunity: dict) -> dict:
    if not self.client:
        return {
            "confidence": 0.0,  # Force veto
            "estimated_probability": None  # No fallback estimation
        }
```

**FOLLOWED BY:** `run_simulation()` at line 440-445:

```python
if vegas_prob is None:
    return {
        "variance": 999.0  # High variance to force veto
    }
```

**ISSUE:** Good defense-in-depth. However, the check at line 249 only skips if variance == 999.0. If AI returns a probability but confidence is 0, the simulation still runs with potentially overconfident variance.

**FIX:** Add explicit check for `confidence == 0` before simulation.

**Priority:** CRITICAL

---

### 3.2 HIGH: Variance Veto Not Applied to Simulation Result

**File:** `engine/agents/brain.py:271`

```python
if confidence >= self.CONFIDENCE_THRESHOLD and variance <= self.MAX_VARIANCE and ev > 0:
```

**ISSUE:** The heuristic veto states "If variance > 0.25, the simulation MUST veto, regardless of confidence." This is correctly implemented here. However, the MAX_VARIANCE threshold of 0.25 is not explained - is this based on backtesting or arbitrary?

**FIX:** Document the statistical basis for MAX_VARIANCE = 0.25.

**Priority:** HIGH (Documentation)

---

### 3.3 MEDIUM: Fixed Seed in Production Simulation

**File:** `engine/agents/brain.py:452-453`

```python
if os.getenv("SIMULATION_USE_FIXED_SEED") == "true":
    np.random.seed(42)
```

**ISSUE:** This is defensive but the comment says "Production simulations should be truly random for accurate variance estimation." However, there's no check to prevent SIMULATION_USE_FIXED_SEED from being set in production env.

**FIX:** Add assert to disable in production mode.

**Priority:** MEDIUM

---

## 4. SAFETY PROTOCOL VULNERABILITIES

### 4.1 CRITICAL: Manual Kill Switch Not Atomic

**File:** `engine/main.py:341-354`

```python
async def activate_kill_switch(request):
    self.manual_kill_switch = True
    # ... logging ...
    return web.json_response({"status": "killed"})
```

**ISSUE:** Between setting `manual_kill_switch = True` and the response, a cycle could still start if `authorize_cycle()` was already in progress.

**FIX:** Add immediate `self.is_processing = False` and `self.running = False` in kill switch handler.

**Priority:** CRITICAL

---

### 4.2 HIGH: Cancel Cycle Does Not Stop Pending Orders

**File:** `engine/main.py:377-404`

```python
async def cancel_cycle(request):
    self.is_processing = False
    await self.bus.publish("SYSTEM_CONTROL", {"action": "STOP_AUTOPILOT"}, "HTTP")
    # ... reset state ...
```

**ISSUE:** If HandAgent has already reserved funds but not yet confirmed the order, the cancellation leaves those funds in limbo. No rollback of vault reservations.

**FIX:** Add `self.vault.release_all_reservations()` to cancel handler.

**Priority:** HIGH

---

### 4.3 MEDIUM: No Rate Limiting on Cycle Trigger

**File:** `engine/main.py:328-338`

```python
async def trigger_cycle(request):
    data = await request.json()
    is_paper = data.get("isPaperTrading", True)
    asyncio.create_task(self.execute_single_cycle(is_paper))
```

**ISSUE:** No rate limiting on this endpoint. A malicious user could spam cycle triggers, causing:
- API rate limits from Kalshi
- Vault balance inconsistencies
- Order book spam

**FIX:** Add minimum 30-second cooldown between cycles.

**Priority:** MEDIUM

---

### 4.4 MEDIUM: Ragnarok Does Not Check Kill Switch First

**File:** `engine/core/safety.py:11-67`

**ISSUE:** `execute_ragnarok()` is callable via HTTP endpoint but does not verify if a kill switch is already active. Could cause unnecessary API calls.

**FIX:** Early return if kill switch active.

**Priority:** MEDIUM

---

## 5. ERROR HANDLING & SYNAPSE GAPS

### 5.1 CRITICAL: Synapse Error Box Does NOT Halt Engine

**File:** `engine/main.py:156-162`

```python
error_count = await self.synapse.errors.size()
if error_count > 0:
    print(f"[GHOST] ERROR BOX ACTIVE ({error_count} errors). HALTING.")
    return False
```

**GOOD:** This check exists in `authorize_cycle()`.

**BAD:** However, errors are logged to Synapse asynchronously (see `error_dispatcher.py:296`):

```python
if self.synapse:
    asyncio.create_task(self._log_to_synapse(error))
```

**ISSUE:** The `create_task()` is fire-and-forget. The error might not be written to Synapse before the next cycle check happens, creating a false negative.

**FIX:** Make error logging synchronous in critical code paths.

**Priority:** CRITICAL

---

### 5.2 HIGH: Infinite Loop Detection Has Short Memory

**File:** `engine/agents/brain.py:176-186`

```python
if opp_model.id == last_processed_id:
    loop_counter += 1
    if loop_counter >= 3:
        await self.log(f"[CRITICAL] INFINITE LOOP DETECTED...")
        await self.bus.publish("SYSTEM_FATAL", {...})
        break
else:
    last_processed_id = opp_model.id
    loop_counter = 0  # Reset on different ID
```

**ISSUE:** The counter resets on every different ID. A pattern like A-B-A-B-A-B would never trigger detection. This is actually normal processing, not a loop. The real risk is the queue delivering the exact same ID multiple times due to a bug.

**FIX:** Add a "seen IDs" set with TTL to detect true duplicates.

**Priority:** HIGH

---

### 5.3 MEDIUM: Generic Exception Catching in Synapse

**File:** `engine/core/synapse.py:119-133`

```python
def _push_sync(self, item: T, priority: int):
    conn = sqlite3.connect(self.db_path)
    try:
        # ... push logic ...
    finally:
        conn.close()
```

**ISSUE:** No exception handling at all. If SQLite is locked (common in concurrent access), the entire push fails silently.

**FIX:** Add retry logic with exponential backoff for SQLite busy errors.

**Priority:** MEDIUM

---

### 5.4 LOW: Vault Reservation Not Persistent

**File:** `engine/core/vault.py:97-111`

```python
def reserve_funds(self, amount: int) -> bool:
    # ... check available ...
    self._reserved_funds += amount
    return True
```

**ISSUE:** `_reserved_funds` is in-memory only. If the engine crashes between reservation and confirmation, the reserved funds are lost on restart. The balance will be inconsistent.

**FIX:** Persist reservations to SQLite or require full re-sync on startup.

**Priority:** LOW (Acceptable for demo/trading, not for production)

---

## 6. PRIORITIZED FIX RECOMMENDATIONS

### MUST FIX (Before Live Trading)

| Priority | Issue | File | Impact |
|----------|-------|------|--------|
| CRITICAL | Real-time order book liquidity depth validation | `agents/hand.py:131` | Could trade on thin books |
| CRITICAL | Race condition in hard floor check | `main.py:165` | Floor bypass possible |
| CRITICAL | Manual kill switch not atomic | `main.py:341` | Can't stop in emergency |
| CRITICAL | Synapse error logging async race | `error_dispatcher.py:296` | Errors may not halt engine |

### SHOULD FIX (Before Scaling)

| Priority | Issue | File | Impact |
|----------|-------|------|--------|
| HIGH | Single source of truth for hard floor | Multiple | Inconsistency risk |
| HIGH | Stale market data in queue | `agents/senses.py:230` | Trading on old prices |
| HIGH | Cancel cycle does not rollback vault | `main.py:377` | Funds locked in limbo |
| HIGH | Minimum liquidity enforcement | `agents/senses.py:38` | Low-volume trading |

### NICE TO HAVE (Future Improvements)

| Priority | Issue | File | Impact |
|----------|-------|------|--------|
| MEDIUM | Rate limiting on cycle trigger | `main.py:328` | API abuse |
| MEDIUM | Vault reservation persistence | `core/vault.py:97` | Crash recovery |
| MEDIUM | Variance threshold documentation | `agents/brain.py:56` | Transparency |

---

## CONCLUSION

The Ghost Engine v3.0 has a solid safety foundation with multiple layers of protection (kill switches, hard floors, variance vetoes). However, the CRITICAL issues around liquidity validation and race conditions should be addressed before trading with significant capital.

**The Critic's Verdict:** PROCEED WITH CAUTION after addressing MUST FIX items.

---

**Report Generated:** 2025-01-30
**Auditor:** The Critic (Risk-Biased Committee Member)
