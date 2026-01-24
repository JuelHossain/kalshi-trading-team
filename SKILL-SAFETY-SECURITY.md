# SKILL-SAFETY-SECURITY.md - Safety & Operational Security

## Overview
This skill enforces the Safety & Operational Security pillar of the Kalshi Trading Team constitution. It ensures all trading operations prioritize risk management and credential protection.

## Core Rules

### Veto Supremacy
- **Trigger**: If ANY security agent (Auditor, Sim Scientist) emits `veto: true` or `verdict: VETO`
- **Action**: Immediately terminate the trade cycle
- **Constraint**: No buy orders allowed after veto
- **Validation**: Check event bus for veto signals before execution

### Vault Lock
- **Trigger**: `VaultState.isLocked` is true
- **Action**: Block all trade executions
- **Fallback**: Log warning and abort cycle
- **Recovery**: Manual vault unlock required

### Paper-First Protocol
- **Default**: `IS_PAPER_TRADING: true` for all new agents/workflows
- **Override**: Explicit production flag required
- **Validation**: Check environment before real trades
- **Logging**: Mark all paper trades clearly

### Credential Shield
- **Forbidden**: Never commit `.env` or `.env.local` files
- **Process**: Use `update-env` workflow for key rotation
- **Audit**: Pre-commit hooks must block credential commits
- **Storage**: Secure key management outside repository

## Implementation
- Security agents must implement veto checking
- Vault state monitoring required
- Environment validation on startup
- Credential scanning in CI/CD pipeline

## Testing
- Veto signals trigger cycle abortion
- Locked vault prevents trades
- Paper mode enforced by default
- No credentials in git history