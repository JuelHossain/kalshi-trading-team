---
name: ui-design
description: UI design system and visual patterns for the Kalshi Trading Team dashboard
---

# UI Design System for Kalshi Trading Team

This skill documents the established visual design patterns and component styling used throughout the Kalshi Trading Team dashboard. All new UI components must follow these locked design standards to maintain visual consistency.

## Core Design Principles

- **Dark Theme**: Primary dark background with glassmorphism effects
- **Typography**: Monospace font for technical data, uppercase labels
- **Color Palette**: Blue accents, gray text hierarchy, white highlights
- **Glass Panels**: Semi-transparent backgrounds with backdrop blur
- **Status Indicators**: Colored dots and badges for real-time feedback

## Component Patterns

### Glass Panels
```css
bg-white/5 rounded-2xl p-5 border border-white/5 relative overflow-hidden group
```
- **Background**: `bg-white/5` (semi-transparent white)
- **Border Radius**: `rounded-2xl` (large rounded corners)
- **Padding**: `p-5` (20px padding)
- **Border**: `border border-white/5` (subtle white border)
- **Effects**: `backdrop-blur-sm` for glass effect

### Typography Hierarchy
- **Headers**: `text-[10px] text-blue-400/80 uppercase font-mono tracking-widest`
- **Labels**: `text-[8px] text-gray-500 uppercase tracking-widest`
- **Body**: `text-[10px] text-gray-600 font-mono`
- **Values**: `text-sm font-bold text-white` or colored variants

### Status Indicators
- **Active Pulse**: `w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse`
- **Status Badges**:
  - Active: `bg-emerald-400/10 border border-emerald-400/20 text-emerald-400`
  - Processing: `bg-blue-400/10 border border-blue-400/20 text-blue-400`
  - Warning: `bg-yellow-400/10 border border-yellow-400/20 text-yellow-400`
  - Error: `bg-red-500/10 border border-red-500/20 text-red-500`

### Layout Patterns

#### Dashboard Grid
- **Container**: `glass-panel rounded-[2rem] p-8 shadow-lg hover:border-white/10 transition-colors`
- **Grid**: `grid grid-cols-1 md:grid-cols-3 gap-6`
- **Card Spacing**: Consistent 24px gaps

#### Component Structure
1. **Header Section**: Title and status indicators
2. **Content Area**: Data display with proper spacing
3. **Interactive Elements**: Hover effects and transitions

### Color Usage

#### Primary Colors
- **Background**: Dark theme (#0a0a0a)
- **Glass**: `bg-white/5` with `border-white/5`
- **Text Primary**: `text-white`
- **Text Secondary**: `text-gray-400`
- **Text Tertiary**: `text-gray-600`

#### Accent Colors
- **Blue**: `blue-400` for headers and active states
- **Green**: `emerald-400` for success/active
- **Yellow**: `yellow-400` for warnings
- **Red**: `red-500` for errors/danger

### Animation & Interaction

#### Pulse Indicators
```css
w-1.5 h-1.5 bg-[color] rounded-full animate-pulse
```
- Used for live status indicators
- Colors match status: green for active, red for error, etc.

#### Hover Effects
- `hover:bg-white/5` for subtle background changes
- `hover:border-white/10` for border highlights
- `group-hover:text-gray-200` for text color changes

### Component Examples

#### Status Header
```jsx
<span className="text-[10px] text-blue-400/80 uppercase font-mono tracking-widest flex items-center gap-2">
  <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
  Component Name
</span>
```

#### Status Badge
```jsx
<span className="text-[9px] uppercase px-2 py-0.5 rounded-full font-bold bg-emerald-400/10 border border-emerald-400/20 text-emerald-400">
  ACTIVE
</span>
```

#### Data Display
```jsx
<div className="text-[8px] text-gray-500 uppercase tracking-widest mb-2">Label</div>
<div className="text-[10px] text-gray-600 font-mono">Value</div>
```

## Implementation Rules

1. **Consistency**: All components must use these patterns
2. **Accessibility**: Maintain contrast ratios for readability
3. **Performance**: Use CSS classes over inline styles
4. **Responsiveness**: Grid layouts adapt to screen sizes
5. **Theme**: Locked to dark theme with glassmorphism

## Testing
- Visual consistency across all components
- Proper contrast for accessibility
- Responsive behavior on different screens
- Animation performance and smoothness

This UI design system ensures the dashboard maintains a cohesive, professional, and technically aesthetic appearance suitable for a trading platform.