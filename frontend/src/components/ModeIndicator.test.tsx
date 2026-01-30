import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import ModeIndicator from './ModeIndicator';

// Mock CSS imports
vi.mock('../index.css', () => ({}));

describe('ModeIndicator Component', () => {
  describe('Demo Mode', () => {
    it('renders with demo mode styling when mode is demo and isProduction is false', () => {
      render(<ModeIndicator mode="demo" isProduction={false} />);

      const indicator = screen.getByTestId('mode-indicator');
      expect(indicator.className).toContain('bg-emerald-500/10');
      expect(indicator.className).toContain('text-emerald-400');
      expect(indicator.className).toContain('border-emerald-500/20');
    });

    it('displays "Demo Mode" text when in demo mode', () => {
      render(<ModeIndicator mode="demo" isProduction={false} />);

      expect(screen.getByText('Demo Mode')).toBeInTheDocument();
    });

    it('shows emerald colored dot in demo mode', () => {
      render(<ModeIndicator mode="demo" isProduction={false} />);

      const dot = screen.getByTestId('mode-dot');
      expect(dot.className).toContain('bg-emerald-400');
    });

    it('does not show production warning in demo mode', () => {
      render(<ModeIndicator mode="demo" isProduction={false} />);

      const warning = screen.queryByTestId('production-warning');
      expect(warning).not.toBeInTheDocument();
    });

    it('does not have pulsing animation in demo mode', () => {
      render(<ModeIndicator mode="demo" isProduction={false} />);

      const indicator = screen.getByTestId('mode-indicator');
      expect(indicator.className).not.toContain('animate-pulse');
    });
  });

  describe('Production Mode', () => {
    it('renders with production mode styling when isProduction is true', () => {
      render(<ModeIndicator mode="production" isProduction={true} />);

      const indicator = screen.getByTestId('mode-indicator');
      expect(indicator.className).toContain('bg-red-500/10');
      expect(indicator.className).toContain('text-red-400');
      expect(indicator.className).toContain('border-red-500/20');
    });

    it('displays "Production Mode" text when in production mode', () => {
      render(<ModeIndicator mode="production" isProduction={true} />);

      expect(screen.getByText('Production Mode')).toBeInTheDocument();
    });

    it('shows red colored dot in production mode', () => {
      render(<ModeIndicator mode="production" isProduction={true} />);

      const dot = screen.getByTestId('mode-dot');
      expect(dot.className).toContain('bg-red-400');
    });

    it('shows production warning when in production mode', () => {
      render(<ModeIndicator mode="production" isProduction={true} />);

      const warning = screen.getByTestId('production-warning');
      expect(warning).toBeInTheDocument();
      expect(warning.textContent).toBe('(Live Trading)');
    });

    it('applies pulsing animation for production mode', () => {
      render(<ModeIndicator mode="production" isProduction={true} />);

      const indicator = screen.getByTestId('mode-indicator');
      expect(indicator.className).toContain('animate-pulse');
    });
  });

  describe('Edge Cases', () => {
    it('treats mode as production when isProduction is true regardless of mode prop', () => {
      // Even with mode="demo", if isProduction is true, it should show production styling
      render(<ModeIndicator mode="demo" isProduction={true} />);

      expect(screen.getByText('Production Mode')).toBeInTheDocument();
      const indicator = screen.getByTestId('mode-indicator');
      expect(indicator.className).toContain('bg-red-500/10');
    });

    it('shows production warning when isProduction is true even with mode="demo"', () => {
      render(<ModeIndicator mode="demo" isProduction={true} />);

      const warning = screen.getByTestId('production-warning');
      expect(warning).toBeInTheDocument();
    });

    it('defaults to production styling when isProduction is false but mode is not demo', () => {
      render(<ModeIndicator mode="production" isProduction={false} />);

      // When mode is "production" but isProduction flag is false, it shows production text
      // but without the warning since isProduction is false
      expect(screen.getByText('Production Mode')).toBeInTheDocument();

      const warning = screen.queryByTestId('production-warning');
      expect(warning).not.toBeInTheDocument();
    });
  });

  describe('Visual Structure', () => {
    it('renders as inline-flex container', () => {
      render(<ModeIndicator mode="demo" isProduction={false} />);

      const indicator = screen.getByTestId('mode-indicator');
      expect(indicator.className).toContain('inline-flex');
    });

    it('has rounded full border radius', () => {
      render(<ModeIndicator mode="demo" isProduction={false} />);

      const indicator = screen.getByTestId('mode-indicator');
      expect(indicator.className).toContain('rounded-full');
    });

    it('has correct font styling', () => {
      render(<ModeIndicator mode="demo" isProduction={false} />);

      const indicator = screen.getByTestId('mode-indicator');
      expect(indicator.className).toContain('font-mono');
      expect(indicator.className).toContain('font-bold');
      expect(indicator.className).toContain('uppercase');
    });

    it('dot element is circular', () => {
      render(<ModeIndicator mode="demo" isProduction={false} />);

      const dot = screen.getByTestId('mode-dot');
      expect(dot.className).toContain('rounded-full');
      expect(dot.className).toContain('w-2');
      expect(dot.className).toContain('h-2');
    });

    it('has transition animation classes', () => {
      render(<ModeIndicator mode="demo" isProduction={false} />);

      const indicator = screen.getByTestId('mode-indicator');
      expect(indicator.className).toContain('transition-all');
      expect(indicator.className).toContain('duration-300');
    });
  });

  describe('Accessibility', () => {
    it('has data-testid for main indicator', () => {
      render(<ModeIndicator mode="demo" isProduction={false} />);

      expect(screen.getByTestId('mode-indicator')).toBeInTheDocument();
    });

    it('has data-testid for mode dot', () => {
      render(<ModeIndicator mode="demo" isProduction={false} />);

      expect(screen.getByTestId('mode-dot')).toBeInTheDocument();
    });

    it('has data-testid for mode label', () => {
      render(<ModeIndicator mode="demo" isProduction={false} />);

      expect(screen.getByTestId('mode-label')).toBeInTheDocument();
    });
  });

  describe('CSS Classes', () => {
    it('has correct padding and gap in demo mode', () => {
      render(<ModeIndicator mode="demo" isProduction={false} />);

      const indicator = screen.getByTestId('mode-indicator');
      expect(indicator.className).toContain('px-3');
      expect(indicator.className).toContain('py-1.5');
      expect(indicator.className).toContain('gap-2');
    });

    it('has correct text size and tracking', () => {
      render(<ModeIndicator mode="demo" isProduction={false} />);

      const indicator = screen.getByTestId('mode-indicator');
      expect(indicator.className).toContain('text-[10px]');
      expect(indicator.className).toContain('tracking-wider');
    });

    it('has border styling in demo mode', () => {
      render(<ModeIndicator mode="demo" isProduction={false} />);

      const indicator = screen.getByTestId('mode-indicator');
      expect(indicator.className).toContain('border');
    });

    it('has border styling in production mode', () => {
      render(<ModeIndicator mode="production" isProduction={true} />);

      const indicator = screen.getByTestId('mode-indicator');
      expect(indicator.className).toContain('border');
    });
  });

  describe('Warning Text Styling', () => {
    it('warning text has red-300 color', () => {
      render(<ModeIndicator mode="production" isProduction={true} />);

      const warning = screen.getByTestId('production-warning');
      expect(warning.className).toContain('text-red-300');
    });
  });
});
