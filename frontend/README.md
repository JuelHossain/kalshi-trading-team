# Sentient Alpha Cockpit (frontend)

The dashboard for the Sentient Alpha engine. The trading pipeline is drawn
as an **orrery**: the Synapse store is the star at the centre and the four
agents (Soul → Senses → Brain → Hand) are planets orbiting it on a tilted
plane. When an agent finishes it throws its payload at the star, the star
catches it with an ink ripple, then throws a signal out to the next agent.
Click a planet or the star to open the inspector.

Everything on screen is driven by the running engine. Nothing is simulated.

## Stack

React 19 · TypeScript · Vite 6 · Tailwind v4 (tokens in `src/index.css`) ·
zustand · lucide-react (stroke width 2.75) · vitest.

## Run it

```bash
npm install
npm run dev          # http://localhost:3000, proxies /api to the engine on :3002
```

Start the engine first (`PYTHONPATH=engine python engine/main.py` from the
repository root). Sign in with **Demo** for paper fills; **Production** asks
for the engine's `AUTH_PASSWORD` and only matters once live trading is armed
on the server.

```bash
npm run typecheck
npm test
npm run build
```

## How it is wired to the engine

| Source | What it feeds |
|---|---|
| `GET /api/stream` (SSE) | The beat machine. Agent log lines start and finish work beats, verdicts and fills become History runs and Orders rows, the vault frame moves the bankroll. See `src/cockpit/engineEvents.ts` for every line it understands. |
| `GET /api/synapse/queues` | The star's depth gauge and the Synapse inspector's list of held items. Polled every 2.5 s. |
| `GET /api/orders` | The Orders panel, from the decision ledger. Polled every 20 s and after each fill. |
| `GET /api/health`, `GET /api/autopilot/status` | Cycle number, balance, autopilot state, and why the engine is refusing cycles (error box, kill switch, lockdown). The top bar shows a Reset control while it is. |
| `GET /api/config`, `POST /api/config`, `POST /api/engine/restart` | The Config view. Every setting the engine's registry describes is rendered from the reply and saved per group; the engine validates, persists to its `.env`, applies live where it can, and lists keys that need a restart. |
| `GET /api/journal`, `GET /api/decisions` | Persistent history in the inspector (journal lines per agent, ledger decisions for the Brain) and the trace's seed on open. |
| `POST /api/trigger`, `/cancel`, `/autopilot/*`, `/kill-switch`, `/reset` | The Run cycle, Cancel, Autopilot, Kill switch and Reset controls. |

Transit beats (throw, catch, signal) are visual and run on fixed timers.
Work beats last until the engine reports the agent finished; the progress
arc holds just short of full if an agent runs over its expected budget.

## Layout of `src/cockpit`

| File | Role |
|---|---|
| `orrery-geometry.ts` | The layout algorithm from the design handoff, verbatim. Pinned by `orrery-geometry.test.ts`. |
| `stations.ts` | The four agents: icon, lane, expected duration, payload name. Add an agent by adding a row. |
| `palette.ts` | Light and dark palettes as CSS custom properties, plus the glass treatment. |
| `store.ts` | The zustand store: beat machine, engine facts, artifacts, inspector and filter state. |
| `engineEvents.ts` | Pure mapping from engine events to store actions. |
| `useEngineFeed.ts` | SSE subscription, polls, the 240 ms clock, and the control calls. |
| `OrreryPlate.tsx` | The glass plate, star, planets, throws. |
| `useEngineHistory.ts` | Persistent history for the inspector from `/decisions` and `/journal`. |
| `SettingsEditor.tsx` | The settings editor: one card per registry group, controls by kind, secrets write-only. |
| `BeatBar.tsx`, `OrdersPanel.tsx`, `Telemetry.tsx`, `InspectorCard.tsx`, `Guardrails.tsx`, `Cockpit.tsx` | The screens. |

Nothing on screen is a constant written into the page: limits come from
`/config`, durations are medians of measured runs, the star's depth is the
real queue count, and history is what the engine persisted.

Motion is pure CSS animation with negative `animation-delay` (keyframes in
`src/index.css`). Do not reimplement the orbit in JavaScript.
