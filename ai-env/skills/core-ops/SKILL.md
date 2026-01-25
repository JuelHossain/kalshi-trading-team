---
name: core-ops
description: Essential operational tools for environment verification and connectivity
---

## Overview
This skill provides automated tools to verify the Sentient Alpha environment. Use the provided scripts to diagnose port conflicts or check the status of the 2-tier architecture.

## Commands
- **Verify Ports**: `python3 ai-env/skills/core-ops/scripts/health_check.py`
  - Checks if Frontend (3000) and Engine (3002) are responsive.
  - Detects if port 3002 is held by a non-engine process.

## Usage
When an agent encounters "Connection Refused" or "404 Not Found" errors, it should run the health check script first before attempting to fix the code.

## Files
- `scripts/health_check.py`: Port and service validator.
- `resources/architecture_map.md`: Visual diagram of the 2-tier system.
