# Authentication & Demo/Production Mode Implementation Plan

## Overview
Implement secure password-based authentication system that switches between Demo (development) and Production (real trading) modes.

## Security Requirements
- **Password**: `993728` (hardcoded for now, move to env var later)
- **Production Mode**: Real Kalshi API, real money trading
- **Demo Mode**: Everything real EXCEPT Kalshi Demo API
- **Clear Visual Indicators**: Users must always know which mode is active

## Phase 1: Backend Authentication

### Files to Create/Modify:
1. **engine/core/auth.py** - Enhance existing auth system
   - Add password verification endpoint
   - Add mode selection logic
   - Set session cookies

2. **engine/main.py** - Update server
   - Add `/api/auth/login` endpoint
   - Add `/api/auth/verify` endpoint
   - Store mode in session state

### Backend Changes:

```python
# engine/core/auth.py - Add these functions

AUTH_PASSWORD = "993728"

async def login_handler(request: web.Request) -> web.Response:
    """Handle login request"""
    try:
        data = await request.json()
        password = data.get("password", "")

        # Check if password matches production password
        is_production = password == AUTH_PASSWORD

        # Set session
        session = await get_session(request)
        session["authenticated"] = True
        session["is_production"] = is_production
        session["mode"] = "production" if is_production else "demo"

        return web.json_response({
            "success": True,
            "mode": "production" if is_production else "demo",
            "isAuthenticated": True
        })

    except Exception as e:
        logger.error(f"Login error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=400)

async def verify_handler(request: web.Request) -> web.Response:
    """Verify authentication status"""
    session = await get_session(request)
    is_authenticated = session.get("authenticated", False)
    is_production = session.get("is_production", False)

    return web.json_response({
        "isAuthenticated": is_authenticated,
        "mode": "production" if is_production else "demo",
        "isProduction": is_production
    })

async def logout_handler(request: web.Request) -> web.Response:
    """Handle logout"""
    session = await get_session(request)
    session.invalidate()
    return web.json_response({"success": True})
```

## Phase 2: Frontend Authentication

### Files to Create/Modify:
1. **frontend/src/components/Login.tsx** - Enhance existing login
2. **frontend/src/hooks/useAuth.ts** - Enhance auth hook
3. **frontend/src/store/useStore.ts** - Add mode state

### Frontend Changes:

```typescript
// frontend/src/components/Login.tsx - Update login form

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useStore } from '@/store/useStore';

const Login: React.FC = () => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });

      const data = await response.json();

      if (data.success) {
        await login(data.mode);
      } else {
        setError('Invalid password or login failed');
      }
    } catch (err) {
      setError('Connection error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoMode = async () => {
    setLoading(true);
    try {
      // Login without password for demo mode
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: '' })
      });

      const data = await response.json();
      if (data.success) {
        await login(data.mode);
      }
    } catch (err) {
      setError('Failed to start demo mode');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <motion.div
        className="bg-gray-900 border border-gray-700 rounded-2xl p-8 max-w-md w-full mx-4"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
      >
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            Sentient Alpha
          </h1>
          <p className="text-gray-400">Autonomous Trading System</p>
        </div>

        {/* Warning Banner */}
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 mb-6">
          <p className="text-yellow-400 text-sm">
            ⚠️ Production mode trades with REAL money. Demo mode is safe for development.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Password Input */}
          <div>
            <label className="block text-gray-400 text-sm mb-2">
              Production Password (optional)
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password for production mode"
              className="w-full bg-black border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Production Login */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-green-600 to-green-700 hover:from-green-500 hover:to-green-600 text-white font-bold py-3 rounded-lg transition-all"
          >
            {loading ? 'Connecting...' : '🚀 Production Mode (Real Trading)'}
          </button>

          {/* Demo Mode */}
          <button
            type="button"
            onClick={handleDemoMode}
            disabled={loading}
            className="w-full bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 text-white font-bold py-3 rounded-lg transition-all"
          >
            {loading ? 'Loading...' : '🎯 Demo Mode (Safe Development)'}
          </button>
        </form>

        {/* Info */}
        <div className="mt-6 text-center text-gray-500 text-xs">
          <p>Demo mode uses real AI logic but Kalshi's demo exchange.</p>
          <p className="mt-1">No real money is traded in demo mode.</p>
        </div>
      </motion.div>
    </div>
  );
};

export default Login;
```

## Phase 3: Environment Switching

### Backend Mode Detection:

```python
# engine/main.py - Update initialization

class GhostEngine:
    def __init__(self, is_production: bool = False):
        self.is_production = is_production

        # Initialize Kalshi client with correct base URL
        if is_production:
            kalshi_base_url = "https://api.kalshi.com/v2"
            logger.info("[GHOST] PRODUCTION MODE - Real Trading Enabled")
        else:
            kalshi_base_url = "https://demo-api.kalshi.com/v2"
            logger.info("[GHOST] DEMO MODE - Using Demo Exchange")

        # Initialize agents with mode awareness
        self.soul = SoulAgent(
            self.bus,
            self.synapse,
            is_production=is_production
        )
        # ... other agents

async def create_app(is_production: bool = False):
    """Create and configure the application"""
    app = web.Application()

    # Store mode in app state
    app['is_production'] = is_production
    app['engine'] = GhostEngine(is_production=is_production)

    # Add routes
    app.add_routes([
        web.post('/api/auth/login', login_handler),
        web.get('/api/auth/verify', verify_handler),
        web.post('/api/auth/logout', logout_handler),
        # ... other routes
    ])

    return app
```

## Phase 4: Visual Mode Indicators

### Frontend Mode Display:

```typescript
// frontend/src/components/ModeIndicator.tsx - NEW FILE

import React from 'react';
import { motion } from 'framer-motion';
import { useStore } from '@/store/useStore';

const ModeIndicator: React.FC = () => {
  const { isProduction, isAuthenticated } = useStore();

  if (!isAuthenticated) return null;

  return (
    <motion.div
      className={`fixed top-4 right-4 z-50 px-4 py-2 rounded-lg border-2 ${
        isProduction
          ? 'bg-red-500/20 border-red-500'
          : 'bg-blue-500/20 border-blue-500'
      }`}
      animate={{ scale: [1, 1.05, 1] }}
      transition={{ duration: 2, repeat: Infinity }}
    >
      <div className="flex items-center gap-2">
        {isProduction ? (
          <>
            <span className="text-2xl">🚨</span>
            <div>
              <p className="text-red-400 font-bold text-xs uppercase">
                Production Mode
              </p>
              <p className="text-red-300 text-[10px]">
                Real Money Trading
              </p>
            </div>
          </>
        ) : (
          <>
            <span className="text-2xl">🎯</span>
            <div>
              <p className="text-blue-400 font-bold text-xs uppercase">
                Demo Mode
              </p>
              <p className="text-blue-300 text-[10px]">
                Safe Development
              </p>
            </div>
          </>
        )}
      </div>
    </motion.div>
  );
};

export default ModeIndicator;
```

## Phase 5: Error Handling Fixes

### Backend Fixes:

1. **Fix SSE Connection Reset Error:**
```python
# engine/main.py - Update stream_logs handler

async def stream_logs(self, request: web.Request) -> web.StreamResponse:
    """Stream SSE logs with proper error handling"""
    response = web.StreamResponse()
    response.content_type = 'text/event-stream'
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'

    try:
        await response.prepare(request)
    except Exception as e:
        logger.warning(f"[SSE] Client disconnected early: {e}")
        return response

    # Register this response for broadcasting
    response_id = id(response)
    self.sse_clients[response_id] = response

    try:
        # Keep connection alive
        while True:
            await asyncio.sleep(1)
            # Send heartbeat
            try:
                await response.write(b": heartbeat\n\n")
            except (ConnectionResetError, ClientConnectionResetError):
                logger.info("[SSE] Client disconnected normally")
                break
            except Exception as e:
                logger.error(f"[SSE] Write error: {e}")
                break

    finally:
        # Clean up
        if response_id in self.sse_clients:
            del self.sse_clients[response_id]
        try:
            await response.write(b"event: close\ndata: {}\n\n")
        except:
            pass

    return response
```

2. **Fix Emoji Encoding Error:**
```python
# engine/agents/brain.py - Fix encoding issue

import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Or replace emoji in logs
def safe_log(message: str) -> str:
    """Remove or replace emoji for Windows console compatibility"""
    emoji_map = {
        '🧠': '[BRAIN]',
        '⚡': '[EXEC]',
        '💰': '[MONEY]',
        '📊': '[DATA]',
        '🎯': '[TARGET]'
    }
    for emoji, replacement in emoji_map.items():
        message = message.replace(emoji, replacement)
    return message
```

3. **Fix Deprecated DuckDuckGo Search:**
```bash
# Update requirements.txt
# Remove: duckduckgo-search
# Add: ddgs

pip install ddgs
```

```python
# engine/agents/senses.py - Update search

from ddgs import DDGS

# Replace all DDGS() usage
# Old: list(DDGS().text(query, max_results=3))
# New: DDGS(proxy=None).text(query, max_results=3)
```

4. **Fix Missing Database Table:**
```sql
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS public.opportunity_queue (
  id BIGSERIAL PRIMARY KEY,
  market_id TEXT NOT NULL,
  market_title TEXT,
  volume BIGINT,
  price DECIMAL,
  yes_price DECIMAL,
  no_price DECIMAL,
  created_at TIMESTAMP DEFAULT NOW(),
  agent_source TEXT DEFAULT 'SENSES'
);

CREATE INDEX IF NOT EXISTS idx_opportunity_queue_created_at
  ON public.opportunity_queue(created_at DESC);

-- Optional: Create execution_queue table
CREATE TABLE IF NOT EXISTS public.execution_queue (
  id BIGSERIAL PRIMARY KEY,
  market_id TEXT NOT NULL,
  action TEXT NOT NULL,
  contracts INTEGER,
  price DECIMAL,
  confidence DECIMAL,
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT NOW(),
  executed_at TIMESTAMP
);
```

## Phase 6: Frontend Error Boundaries

### Add Error Boundary:

```typescript
// frontend/src/components/ErrorBoundary.tsx - NEW FILE

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { motion } from 'framer-motion';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-black flex items-center justify-center p-4">
          <motion.div
            className="bg-red-500/10 border border-red-500/30 rounded-2xl p-8 max-w-lg"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <div className="text-center">
              <div className="text-6xl mb-4">💥</div>
              <h1 className="text-2xl font-bold text-red-400 mb-2">
                Something went wrong
              </h1>
              <p className="text-gray-400 mb-4">
                {this.state.error?.message || 'An unexpected error occurred'}
              </p>
              <button
                onClick={() => window.location.reload()}
                className="bg-red-600 hover:bg-red-500 text-white px-6 py-2 rounded-lg"
              >
                Reload Page
              </button>
            </div>
          </motion.div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
```

## Phase 7: Testing Checklist

### Backend Tests:
- [ ] Login with correct password (993728) → Production mode
- [ ] Login with incorrect password → Error
- [ ] Login without password → Demo mode
- [ ] Verify production mode uses real Kalshi API
- [ ] Verify demo mode uses Kalshi demo API
- [ ] Test SSE connection handling (connect/disconnect)
- [ ] Test emoji encoding in Windows console
- [ ] Test database operations (opportunity_queue)

### Frontend Tests:
- [ ] Login form renders correctly
- [ ] Demo mode button works
- [ ] Production password works
- [ ] Mode indicator shows correct mode
- [ ] Workflow visualization works in both modes
- [ ] Error boundary catches React errors
- [ ] SSE reconnection after disconnect

### Integration Tests:
- [ ] Full cycle in demo mode (no real money)
- [ ] Mode switching requires re-authentication
- [ ] Session persistence across page reloads
- [ ] Logout clears session correctly

## Phase 8: Security Considerations

### Important Notes:
1. **Password Storage**: Currently hardcoded, should move to environment variable
2. **Session Management**: Use secure HTTP-only cookies in production
3. **HTTPS Required**: Production must use HTTPS
4. **Rate Limiting**: Add login attempt rate limiting
5. **Audit Logging**: Log all production mode activities
6. **Kill Switch**: Keep Ragnarok emergency protocol functional

## Implementation Order:

1. ✅ **Backend Authentication** (auth.py, main.py)
2. ✅ **Frontend Login** (Login.tsx, useAuth.ts)
3. ✅ **Environment Switching** (is_production flag)
4. ✅ **Error Fixes** (SSE, encoding, DB)
5. ✅ **Mode Indicators** (visual feedback)
6. ✅ **Error Boundaries** (React safety)
7. ✅ **Testing** (all scenarios)
8. ✅ **Documentation** (update CLAUDE.md)

---

**Status**: 📝 Planning Complete
**Next**: Delegate implementation to specialized agents
