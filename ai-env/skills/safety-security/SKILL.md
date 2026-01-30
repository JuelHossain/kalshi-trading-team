---
name: safety-security
description: Safety & Operational Security protocols for tactical trading
last_modified: 2026-01-29
---

## Overview
This skill enforces the Safety pillar of the Sentient Alpha constitution. It prioritizes capital preservation and automated risk mitigation.

## Core Rules

### Ragnarok Protocol
- **Definition**: Emergency liquidation of all open orders.
- **Trigger**: Fatal errors, manual UI kill-switch, or authorization failure.
- **Action**: Hand agent must execute the Ragnarok protocol immediately.
- **Verification**: UI must show "VAULT LOCKED" status.

### Autopilot Pulse
- **Executive Authority**: `SoulAgent` manages the Autopilot cycle.
- **Compliance**: All agents must respect the current pulse state before performing expensive/risky actions.
- **Veto Supremacy**: A `veto: true` signal from any agent (e.g., Audit) terminates the pulse immediately.

### Paper-First & Vault Safety
- **Default**: `IS_PAPER_TRADING: true`.
- **Vault Lock**: No strike execution if `isLocked` is true.
- **Safety**: Hard floor check at $255 to prevent total loss.

### Isolated Testing
- **Diagnostics**: Use `engine/diagnostics/` tools (e.g., `brain_tap.py`) to test agent logic without firing live signals.
- **Simulation**: Monte Carlo results must have variance < 25%.

## Implementation
- Ragnarok liquidation in `engine/core/safety.py`.
- SoulAgent executive authorization logic.
- Hard floor and vault locking in `core/vault.py`.

## Testing
- Trigger Ragnarok from UI and verify order cancellation.
- Verify Autopilot Pulse halt upon negative authorization.
- Confirm isolated diagnostic scripts pass before main engine deployment.

## Evolution Context
### Evolution Entry [2026-01-29 20:34]
- **Trigger**: Code changes detected
- **Files**: `engine/core/auth.py`, `engine/core/vault.py`


### Evolution Entry [2026-01-29 20:34]
- **Trigger**: Code changes detected
- **Files**: `engine/core/auth.py`, `engine/core/vault.py`


### Evolution Entry [2026-01-29 20:34]
- **Trigger**: Code changes detected
- **Files**: `engine/core/auth.py`, `engine/core/vault.py`


### Evolution Entry [2026-01-29 20:34]
- **Trigger**: Code changes detected
- **Files**: `engine/core/auth.py`, `engine/core/vault.py`
