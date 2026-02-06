# Architecture Overview

Welcome to the Kalshi Trading Team architecture documentation.

## System Architecture

This project implements a sophisticated automated trading system for the Kalshi prediction market platform. The architecture follows a multi-agent pattern with clear separation of concerns.

### Core Components

#### Engine (`/engine`)
The engine is the heart of the trading system, containing:

- **Agents Layer**: Specialized agents handling different aspects of trading
  - `brain.py`: Strategic decision-making and analysis
  - `gateway.py`: External API communication and market data fetching
  - `hand.py`: Order execution and trade management
  - `senses.py`: Market monitoring and data collection
  - `soul.py`: Agent lifecycle and orchestration

- **Core Layer**: Fundamental system services
  - `auth.py`: Authentication and credential management
  - `db.py`: Database operations and persistence
  - `vault.py`: Secure storage for sensitive data
  - `error_dispatcher.py`: Centralized error handling
  - `ai_client.py`: AI/LLM integration
  - `logger.py`: System-wide logging

#### Frontend (`/frontend`)
React-based user interface providing:
- Real-time market monitoring
- Agent status visualization
- Trade execution controls
- Performance analytics

#### HTTP API (`/engine/http_api`)
RESTful API endpoints for:
- Agent control and monitoring
- Market data access
- Order management
- System health checks

### Architecture Principles

1. **Separation of Concerns**: Each agent has a specific, well-defined responsibility
2. **Fail-Safe Design**: Comprehensive error handling and recovery mechanisms
3. **Security First**: Secure credential management and data protection
4. **Observability**: Extensive logging and diagnostics
5. **Testability**: Unit and integration tests for all critical components

### Data Flow

```
Market Data (Gateway/Senses)
         ↓
    Analysis (Brain)
         ↓
  Decision (Soul)
         ↓
 Execution (Hand)
         ↓
    Orders (Gateway)
```

### Technology Stack

- **Backend**: Python 3.11+
- **Frontend**: React + TypeScript
- **Database**: SQLite (with PostgreSQL support)
- **API**: REST + WebSocket for real-time updates
- **AI Integration**: Multiple LLM providers

## Documentation Structure

- `/api`: API endpoint documentation
- `/deployment`: Deployment and configuration guides
- `/development`: Development setup and workflows

## Getting Started

For development setup and configuration, see the main project README.

## Contributing

When making architectural changes:
1. Update this documentation
2. Ensure all tests pass
3. Follow the established patterns
4. Document new components thoroughly

---

Last updated: 2025-01-31
