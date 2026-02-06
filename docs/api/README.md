# API Documentation

Welcome to the Kalshi Trading Team API documentation.

## Overview

This system exposes a RESTful API for controlling and monitoring the automated trading agents. The API is built using FastAPI and provides comprehensive endpoints for all system operations.

## Base URL

```
http://localhost:8000/api
```

## Authentication

All API endpoints require authentication using Bearer tokens. Include the token in the Authorization header:

```
Authorization: Bearer <your-token-here>
```

### Getting an API Token

API tokens can be generated through the authentication endpoint or configured in the system settings.

## API Endpoints

### Agent Management

#### List All Agents
```http
GET /api/agents
```
Returns a list of all active and inactive agents with their current status.

#### Get Agent Status
```http
GET /api/agents/{agent_id}
```
Retrieves detailed status information for a specific agent.

#### Start Agent
```http
POST /api/agents/{agent_id}/start
```
Starts a specific agent.

#### Stop Agent
```http
POST /api/agents/{agent_id}/stop
```
Stops a running agent.

### Market Data

#### Get Market List
```http
GET /api/markets
```
Retrieves available markets with current pricing.

#### Get Market Details
```http
GET /api/markets/{market_id}
```
Gets detailed information for a specific market.

#### Get Market History
```http
GET /api/markets/{market_id}/history
```
Retrieves historical data for a market.

### Trading Operations

#### Place Order
```http
POST /api/orders
Content-Type: application/json

{
  "market_id": "string",
  "side": "yes" | "no",
  "quantity": number,
  "price": number,
  "client_order_id": "string"
}
```

#### Get Order Status
```http
GET /api/orders/{order_id}
```
Retrieves the status of a specific order.

#### Cancel Order
```http
DELETE /api/orders/{order_id}
```
Cancels a pending order.

#### Get Order History
```http
GET /api/orders/history
```
Retrieves historical order data with optional filtering.

### System Health

#### Health Check
```http
GET /api/health
```
Returns system health status and component availability.

#### Get System Metrics
```http
GET /api/metrics
```
Retrieves performance metrics and statistics.

## Response Format

All API responses follow a consistent format:

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": { ... }
  }
}
```

## Error Codes

| Code | Description |
|------|-------------|
| `AUTH_FAILED` | Authentication failed |
| `INVALID_PARAMS` | Invalid request parameters |
| `AGENT_NOT_FOUND` | Agent does not exist |
| `MARKET_CLOSED` | Market is not open for trading |
| `INSUFFICIENT_BALANCE` | Insufficient funds for order |
| `RATE_LIMITED` | Too many requests |
| `SYSTEM_ERROR` | Internal system error |

## Rate Limiting

API requests are rate-limited to prevent abuse:
- Standard tier: 100 requests per minute
- Premium tier: 1000 requests per minute

Rate limit headers are included in all responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## WebSocket API

Real-time updates are available through WebSocket connections:

```
ws://localhost:8000/api/ws
```

### WebSocket Events

- `market_update`: Market price changes
- `order_update`: Order status changes
- `agent_status`: Agent state changes
- `system_alert`: System notifications

## SDK Examples

### Python
```python
import requests

response = requests.get(
    'http://localhost:8000/api/agents',
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)
data = response.json()
```

### JavaScript
```javascript
fetch('http://localhost:8000/api/agents', {
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN'
  }
})
.then(res => res.json())
.then(data => console.log(data));
```

### curl
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/agents
```

## Testing

Use the provided Postman collection or OpenAPI specification for API testing:
- OpenAPI Spec: `/api/openapi.json`
- Postman Collection: `/docs/postman/`

## Versioning

The API is versioned using URL paths. Current version: `v1`

Include the version in your requests:
```
http://localhost:8000/api/v1/agents
```

## Changelog

### v1.0.0 (2025-01-31)
- Initial API release
- Agent management endpoints
- Market data endpoints
- Trading operations
- WebSocket support

---

For detailed endpoint specifications with request/response schemas, see the OpenAPI specification.

Last updated: 2025-01-31
