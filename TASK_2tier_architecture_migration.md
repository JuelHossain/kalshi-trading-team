# 2-Tier Architecture Migration

## Overview
Remove Node.js backend, connect React frontend directly to Python engine.
Add Zustand + Shadcn UI for cleaner code.

---

## Phase 1: Python Engine Updates

### 1.1 Create Ragnarok Utility
- [ ] Create `engine/core/safety.py`
- [ ] Implement `execute_ragnarok()` function:
  - Fetch all open orders from Kalshi API
  - Cancel all orders atomically
  - Return status report
- [ ] Import and call from Soul agent when kill switch triggered

### 1.2 Add API Endpoints to `engine/main.py`
- [ ] `POST /auth` - Accept `{useSystemAuth, isPaperTrading}`, return auth status
- [ ] `GET /pnl` - Return balance history from Supabase (last 24h)
- [ ] `GET /pnl/heatmap` - Return daily PnL data (last 365 days)

---

## Phase 2: Frontend Library Migration

### 2.1 Install Dependencies
```bash
cd frontend
npm install zustand @tanstack/react-query
npx shadcn@latest init
```

### 2.2 Replace State Management with Zustand
- [ ] Create `frontend/src/store/useStore.ts`
- [ ] Migrate state from `useOrchestrator.ts` (20+ useState calls → 1 store)
- [ ] Migrate state from `useAuth.ts`

### 2.3 Add Shadcn UI Components
- [ ] Initialize Shadcn with dark theme
- [ ] Migrate buttons: `btn-primary` → Shadcn Button
- [ ] Migrate cards: `glass-panel` → Shadcn Card with glassmorphism variant
- [ ] Keep custom CSS for animations (scanlines, organic-glow)

---

## Phase 3: Update API Endpoints

### Files to Update
| File | Line | Change |
|------|------|--------|
| `useOrchestrator.ts` | L52 | `/api/stream` → `http://localhost:3002/stream` |
| `useOrchestrator.ts` | L159 | `/api/run` → `http://localhost:3002/trigger` |
| `useOrchestrator.ts` | L190 | `/api/kill-switch` → `http://localhost:3002/kill-switch` |
| `useAuth.ts` | L36 | `/api/auth` → `http://localhost:3002/auth` |
| `vite.config.ts` | L14-20 | Remove proxy block entirely |

---

## Phase 4: Backend Cleanup

- [ ] Move `/backend` → `/legacy/backend`
- [ ] Remove `backend` from root `package.json` workspaces
- [ ] Update `ecosystem.config.cjs` to only run frontend + engine
- [ ] Update `.agent/workflows/run_app.md`

---

## Phase 5: Testing & Verification

### Manual Tests
1. Start Python engine: `cd engine && python main.py`
2. Verify `http://localhost:3002/health` → `{"status": "healthy"}`
3. Start frontend: `cd frontend && npm run dev`
4. Verify SSE connection in browser DevTools (Network → filter "stream")
5. Click "INITIATE CYCLE" → logs appear in Terminal
6. Click "CANCEL CYCLE" → cycle stops

### Build & Deploy
- [ ] `npm run build`
- [ ] Test production build
- [ ] Git commit: `feat: migrate to 2-tier architecture`
- [ ] Push to remote

---

## Reference Files

### Python Engine
- [main.py](file:///home/jrrahman01/workspace/active/kalshi-trading-team/engine/main.py) - Add endpoints
- [soul.py](file:///home/jrrahman01/workspace/active/kalshi-trading-team/engine/agents/soul.py) - Sentinel at L63-70

### Frontend
- [useOrchestrator.ts](file:///home/jrrahman01/workspace/active/kalshi-trading-team/frontend/src/hooks/useOrchestrator.ts) - State + endpoints
- [useAuth.ts](file:///home/jrrahman01/workspace/active/kalshi-trading-team/frontend/src/hooks/useAuth.ts) - Auth endpoint
- [vite.config.ts](file:///home/jrrahman01/workspace/active/kalshi-trading-team/frontend/vite.config.ts) - Remove proxy

### Backend (to archive)
- [agent-12-ragnarok](file:///home/jrrahman01/workspace/active/kalshi-trading-team/backend/src/agents/agent-12-ragnarok/index.ts) - Reference for Ragnarok
- [dbService.ts](file:///home/jrrahman01/workspace/active/kalshi-trading-team/backend/src/services/dbService.ts) - Reference for PnL queries
