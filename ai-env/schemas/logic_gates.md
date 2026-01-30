# Sentient Alpha - Brain Decision Logic (Logic Gates)

This file documents the mathematical thresholds used by the Brain agent to authorize trades.

## 📊 Core Thresholds

| Threshold | Value | Description |
| :--- | :--- | :--- |
| **Confidence** | `0.85` | Minimum AI probability agreement between Optimist and Critic. |
| **Max Variance** | `0.25` | Maximum volatility allowed in Monte Carlo simulations. |
| **MC Iterations** | `10,000` | Number of paths simulated for Expected Value (EV) calculation. |

## 🛡️ Safety & Vault Thresholds (Capital Preservation)

| Mechanism | Threshold | Action |
| :--- | :--- | :--- |
| **Kill Switch** | `< 85% Principal` | Halts all trading operations immediately. |
| **Profit Lock** | `+ $50 (Daily)` | Activates frozen principal mode. |
| **Ragnarok** | `Manual/Fatal` | Liquidates all positions via `safety.py`. |

## 🛠️ Veto Logic (Brain)
A trade is **VETOED** if:
1. `confidence < 0.85` (AI does not trust the move)
2. `variance > 0.25` (Mathematical uncertainty is too high)
3. `expected_value <= 0` (The math doesn't favor the payout)

## 🔄 Adjustment Protocol
Thresholds can only be lowered if the **Historian Agent** provides a PnL analysis showing that higher variance trades have outperformed the 0.25 cap over a 30-day window.---

*Last schema evolution: 2026-01-29 20:34*
*Triggered by changes in: `engine/agents/brain.py`, `engine/agents/hand.py`, `engine/core/vault.py`*
*Triggered by changes in: `engine/agents/brain.py`, `engine/agents/hand.py`, `engine/core/vault.py`*
*Triggered by changes in: `engine/agents/brain.py`, `engine/agents/hand.py`, `engine/core/vault.py`*
