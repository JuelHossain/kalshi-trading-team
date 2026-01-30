# Animation System - Quick Reference

## Agent Node Animations

### Status → Animation Mapping

| Status | Scale Animation | Glow Effect | Pulse Rings | Icon Animation |
|--------|----------------|-------------|-------------|----------------|
| **idle** | None | None | None | Static |
| **active** | 1.0 → 1.02 → 1.0 | Agent color (30% opacity) | 2 rings, outward | Gentle rotation (-5° to 5°) |
| **processing** | Same as active | Same as active | Same as active | Same as active |
| **error** | 1.0 → 1.05 → 1.0 | Red (#ef4444, 60% opacity) | 2 rings, rapid | Violent shake (-10° to 10°) |
| **veto** | 1.0 → 1.03 → 1.0 | Amber (#f59e0b, 60% opacity) | 2 rings, medium | Moderate shake (-8° to 8°) |

### Animation Timings

```typescript
// Breathing (active/processing)
duration: 2s
repeat: Infinity
ease: easeInOut

// Pulse rings
ring1: scale 1 → 2, opacity 0.6 → 0, duration 2s
ring2: scale 1 → 2, opacity 0.6 → 0, duration 2s, delay 0.5s

// Error shake
duration: 0.4s (faster than active)
repeat: Infinity

// Veto shake
duration: 0.6s (intermediate)
repeat: Infinity
```

### Agent Colors

```css
--soul: #f59e0b;    /* Amber/Gold */
--senses: #06b6d4;  /* Cyan */
--brain: #a855f7;   /* Purple */
--hand: #10b981;    /* Emerald */
--error: #ef4444;   /* Red */
--veto: #f59e0b;    /* Amber */
```

## Data Flow Edge Animations

### Particle System

```
Particle 1 (Lead):
- Radius: 4px (outer glow), 2.5px (bright), 1.5px (core)
- Duration: 1.5s
- Start: 0s
- Opacity: 40% (outer), 90% (inner), pulsing (core)

Particle 2 (Middle):
- Radius: Same
- Duration: 1.8s
- Start: 0.4s
- Opacity: Same

Particle 3 (Trail):
- Radius: Same
- Duration: 2.1s
- Start: 0.8s
- Opacity: Same
```

### Flow Type Colors

```typescript
authorization: #f59e0b  // Gold (Soul → Senses)
opportunity:   #06b6d4  // Cyan (Senses → Brain)
decision:      #a855f7  // Purple (Brain → Hand)
execution:     #10b981  // Green (Hand → Market)
```

### Edge States

| State | Stroke Width | Opacity | Particles | Label |
|-------|--------------|---------|-----------|-------|
| **Idle** | 2px | 20% | 0 | Hidden |
| **Active** | 3px | 80% | 3 | Visible |

## Graph-Level Animations

### Background Pulse

```css
/* Radial gradient from center */
Colors: cyan → purple → green → cyan
Duration: 8s
Repeat: Infinity
Max Opacity: 0.02 (very subtle)
```

### Grid Pattern

```css
/* Active vs Idle */
Idle:
  - Color: #333333
  - Opacity: 0.05
  - Gap: 50px

Processing:
  - Color: #ffffff
  - Opacity: 0.10 (2x brighter)
  - Gap: 50px
  - Transition: 0.5s ease
```

### Sequential Edge Activation

```
Step 0: All edges inactive
Step 1: Soul → Senses activates (0ms)
Step 2: Senses → Brain activates (500ms)
Step 3: Brain → Hand activates (1000ms)
Step 4: Reset to idle (2000ms)
```

## Performance Tuning

### Framer Motion

```typescript
// Good: Hardware-accelerated properties
animate={{ scale: 1.05, x: 100, rotate: 90 }}

// Bad: Layout-triggering properties
animate={{ width: '100%', height: '50%' }}

// Optimize: Use layout prop
<motion.div layout />
```

### React Flow

```typescript
// Enable performance mode
<ReactFlow
  nodesDraggable={false}        // Disable for read-only
  nodesConnectable={false}       // Disable if not editing
  elementsSelectable={true}      // Keep for inspection
  minZoom={0.3}
  maxZoom={1.5}
/>
```

### Particle Count

```typescript
// Reduce for mobile or low-end devices
const particleCount = isMobile ? 1 : 3;

// Disable entirely on very slow devices
const enableParticles = !isLowEndDevice;
```

## Animation Triggers

### Manual Trigger (Demo Mode)

```typescript
// In AgentWorkflowGraph.tsx
setInterval(() => {
  const randomAgent = Math.floor(Math.random() * 4);
  setAgentState(randomAgent + 1, { status: 'active' });
}, 3000);
```

### Store-Based Trigger (Production)

```typescript
// In AgentWorkflowGraph.tsx
useEffect(() => {
  if (activeAgentId !== null) {
    setNodes((nodes) =>
      nodes.map((node) => ({
        ...node,
        data: {
          ...node.data,
          status: node.data.agentId === activeAgentId ? 'active' : 'idle'
        }
      }))
    );
  }
}, [activeAgentId]);
```

### SSE-Based Trigger (Backend Integration)

```typescript
// In useOrchestrator.ts
useEffect(() => {
  const eventHandler = (event) => {
    if (event.type === 'AGENT_STATE') {
      const { agentId, status, metrics } = event.state;
      useStore.getState().setAgentState(agentId, { status, metrics });
    }
  };
  // Subscribe to SSE...
}, []);
```

## Debugging Animations

### Check Animation Performance

```javascript
// Browser DevTools
// 1. Open Performance tab
// 2. Start recording
// 3. Interact with graph
// 4. Stop recording
// 5. Look for long frames (>16ms = bad)

// Target: 60fps = 16.67ms per frame
```

### Force Repaint

```javascript
// Trigger reflow to restart animations
const element = document.querySelector('.agent-node');
element.style.display = 'none';
element.offsetHeight; // Force reflow
element.style.display = 'block';
```

### Inspect Framer Motion

```javascript
// Log current animation values
<motion.div
  onUpdate={(latest) => {
    console.log('Current scale:', latest.scale);
  }}
/>
```

## Common Issues

### Issue: Animations Not Running

**Symptoms**: Nodes static, no pulses, edges dark

**Checklist**:
- [ ] Framer Motion installed? `npm list framer-motion`
- [ ] React Flow styles imported? `import '@xyflow/react/dist/style.css'`
- [ ] Component mounted? Check React DevTools
- [ ] State updating? Check Zustand devtools
- [ ] CSS transitions enabled? Check browser settings

**Fix**:
```typescript
// Force re-mount
key={Date.now()}
```

### Issue: Choppy Animations

**Symptoms**: FPS < 60, stuttering, lag

**Causes**:
- Too many simultaneous animations
- Expensive re-renders
- Large component tree
- No hardware acceleration

**Fixes**:
```typescript
// 1. Reduce animation count
const particleCount = 1; // Instead of 3

// 2. Memoize components
export default memo(AgentNode);

// 3. Use will-change
.agent-node {
  will-change: transform, opacity;
}

// 4. Optimize renders
const MemoizedChild = memo(({ data }) => {
  // Expensive render
}, (prev, next) => prev.data.id === next.data.id);
```

### Issue: Particles Not Following Path

**Symptoms**: Particles move in straight line, not curve

**Cause**: Invalid SVG path or wrong path reference

**Fix**:
```typescript
// Ensure path is valid
const [edgePath] = getBezierPath({
  sourceX, sourceY,
  targetX, targetY,
  curvature: 0.25
});

// Check path exists
console.log('Edge path:', edgePath);

// Verify in DOM
<animateMotion path={edgePath} />
```

## Animation Best Practices

### DO ✅

```typescript
// Hardware-accelerated
animate={{ scale: 1.05, x: 100, rotate: 90 }}

// Memoized components
export default memo(Component);

// Cleanup effects
useEffect(() => {
  const interval = setInterval(callback, 1000);
  return () => clearInterval(interval);
}, []);

// Stagger children
transition={{ staggerChildren: 0.1 }}

// Use transforms
<div style={{ transform: 'translateX(100px)' }} />
```

### DON'T ❌

```typescript
// Layout-triggering
animate={{ width: '100%', height: '50%' }}

// Un-memoized expensive renders
export default Component; // Missing memo()

// No cleanup
useEffect(() => {
  setInterval(callback, 1000);
  // Missing return cleanup
}, []);

// Simultaneous animations
animate={{ scale: 1.05, x: 100, rotate: 90, opacity: 0.5, width: '100%' }}

// Use top/left
<div style={{ left: '100px', top: '50px' }} />
```

## Resources

- [Framer Motion Docs](https://www.framer.com/motion/)
- [React Flow Docs](https://reactflow.dev/)
- [SVG animateMotion](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/animateMotion)
- [CSS Triggers](https://csstriggers.com/) - Which properties trigger layouts

---

**Last Updated**: 2025-01-29
**Version**: 1.0.0
