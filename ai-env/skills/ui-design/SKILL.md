---
name: ui-design
description: UI design system and visual patterns for the Sentient Alpha cockpit
---

# UI Design System for Sentient Alpha

All new UI components must follow these standards to maintain the "Cinematic Terminal" aesthetic and consistent state logic.

## Core Design Principles

- **Framework**: React + Vite + Shadcn UI.
- **State**: **Zustand** (`src/store/useStore.ts`) for all global logic and log buffering.
- **Aesthetic**: Dark theme, glassmorphism, high-contrast monospace data.
- **Responsiveness**: Recharts adaptivity and grid-based layout.

## Component Standards

### Layout Components
- Use **Shadcn UI** `Card` and `Button` as the base.
- **Glass Panel Variant**: Semi-transparent, backdrop-blur, subtle white border.

### State & Communication
- **API Standard**: All network calls must use the relative `/api` proxy.
- **SSE Integration**: Subscriptions to `/api/stream` must be buffered in the Zustand store to allow for high-frequency log updates without UI jitter.
- **Real-time Status**: Green pulse for connected/online, red for disconnect/offline.

## Naming & Style

- **Components**: PascalCase (e.g., `LogTerminal.tsx`).
- **Icons**: Lucide-react for standard actions.
- **Colors**: Blue-400 (Active), Emerald-400 (Success), Red-500 (Fatal), Gray-600 (Dim).

## Implementation
- Zustand for state centralized container.
- Shadcn for accessible UI primitives.
- Tailwind CSS for all utility styling.

## Testing
- Verify responsive layout on mobile/desktop.
- Ensure log streaming doesn't freeze the main thread.
- Confirm `/api` proxy works without CORS errors.