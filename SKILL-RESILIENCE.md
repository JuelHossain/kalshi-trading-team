# SKILL-RESILIENCE.md - Resilience & Scalability

## Overview
This skill enforces the Resilience & Scalability pillar, ensuring robust operation and efficient resource usage.

## Core Rules

### Defensive API Usage
- **Backoff**: Implement exponential backoff for 429/500 errors
- **Hibernation**: Agents hibernate after 5 consecutive failures
- **Retry Logic**: Intelligent retry with jitter
- **Rate Limits**: Respect API limits to protect reputation

### Determinism
- **Logging**: Log enough context to recreate decisions
- **Replay**: Enable `replay-debug` workflow for debugging
- **State**: Capture all decision inputs and outputs
- **Reproducibility**: Same inputs produce same outputs

### Alpha Efficiency
- **Computation**: Heavy math/filtering in Python/Numpy
- **LLM Usage**: Reserve LLMs for high-value "Finalist" tickers only
- **Optimization**: Minimize API calls and computational overhead
- **Caching**: Cache expensive operations when possible

### Process Management
- **PM2**: Follow `ecosystem.config.cjs` architecture
- **Services**: All services (Backend, Frontend, Engine) via PM2
- **Monitoring**: PM2 monitoring for health checks
- **Scaling**: Horizontal scaling capabilities

## Implementation
- Exponential backoff with jitter
- Comprehensive logging with context
- Numpy for numerical computations
- PM2 process management
- Caching layers where appropriate

## Testing
- Backoff works on API errors
- Decisions are reproducible
- LLMs used sparingly
- All services managed by PM2