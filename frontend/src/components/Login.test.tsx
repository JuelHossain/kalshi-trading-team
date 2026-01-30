import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Login, { AuthMode } from './Login';
import React from 'react';

describe('Login Component', () => {
  const mockOnLogin = vi.fn();

  const defaultProps = {
    onLogin: mockOnLogin,
    authError: null as string | null,
    isAuthenticating: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Rendering', () => {
    it('renders the login form with title', () => {
      render(<Login {...defaultProps} />);

      expect(screen.getByText('SENTIENT ALPHA')).toBeInTheDocument();
      expect(screen.getByText('Proprietary Trading Command Node')).toBeInTheDocument();
    });

    it('renders demo and production mode buttons', () => {
      render(<Login {...defaultProps} />);

      expect(screen.getByText('DEMO MODE')).toBeInTheDocument();
      expect(screen.getByText('PRODUCTION')).toBeInTheDocument();
    });

    it('renders the submit button', () => {
      render(<Login {...defaultProps} />);

      expect(screen.getByText('ENTER DEMO MODE')).toBeInTheDocument();
    });

    it('renders footer text', () => {
      render(<Login {...defaultProps} />);

      expect(
        screen.getByText('RSA-SHA256 Encrypted Session • Demo Environment')
      ).toBeInTheDocument();
    });
  });

  describe('Mode Selection', () => {
    it('shows demo button as active when initially rendered', () => {
      render(<Login {...defaultProps} />);

      const demoButton = screen.getByText('DEMO MODE');
      expect(demoButton.parentElement?.parentElement?.className).toContain('bg-cyan-500');
    });

    it('shows production button with correct styling when clicked', () => {
      render(<Login {...defaultProps} />);

      const productionButton = screen.getByText('PRODUCTION');
      fireEvent.click(productionButton);

      expect(productionButton.parentElement?.parentElement?.className).toContain('bg-red-500');
    });

    it('switches to demo mode when demo button is clicked', () => {
      render(<Login {...defaultProps} />);

      const productionButton = screen.getByText('PRODUCTION');
      fireEvent.click(productionButton);

      const demoButton = screen.getByText('DEMO MODE');
      fireEvent.click(demoButton);

      expect(demoButton.parentElement?.parentElement?.className).toContain('bg-cyan-500');
    });
  });

  describe('Demo Mode', () => {
    it('shows demo mode description', () => {
      render(<Login {...defaultProps} />);

      expect(screen.getByText('Demo Environment')).toBeInTheDocument();
      expect(screen.getByText('• Kalshi Demo API (paper trading)')).toBeInTheDocument();
      expect(screen.getByText('• No real money at risk')).toBeInTheDocument();
      expect(screen.getByText('• No password required')).toBeInTheDocument();
    });

    it('does not show password input in demo mode', () => {
      render(<Login {...defaultProps} />);

      const passwordInput = screen.queryByPlaceholderText('Enter production password');
      expect(passwordInput).not.toBeInTheDocument();
    });

    it('calls onLogin with demo mode when form is submitted', async () => {
      render(<Login {...defaultProps} />);

      const submitButton = screen.getByText('ENTER DEMO MODE');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnLogin).toHaveBeenCalledWith('demo', undefined);
      });
    });
  });

  describe('Production Mode', () => {
    it('shows production mode description when selected', () => {
      render(<Login {...defaultProps} />);

      const productionButton = screen.getByText('PRODUCTION');
      fireEvent.click(productionButton);

      expect(screen.getByText('Production Environment')).toBeInTheDocument();
      expect(screen.getByText('• Real Kalshi API (live markets)')).toBeInTheDocument();
      expect(screen.getByText('• Actual monetary transactions')).toBeInTheDocument();
      expect(screen.getByText('• Requires authorization password')).toBeInTheDocument();
    });

    it('shows password input when production mode is selected', () => {
      render(<Login {...defaultProps} />);

      const productionButton = screen.getByText('PRODUCTION');
      fireEvent.click(productionButton);

      const passwordInput = screen.getByPlaceholderText('Enter production password');
      expect(passwordInput).toBeInTheDocument();
    });

    it('shows warning banner in production mode', () => {
      render(<Login {...defaultProps} />);

      const productionButton = screen.getByText('PRODUCTION');
      fireEvent.click(productionButton);

      expect(screen.getByText('REAL MONEY TRADING - PROCEED WITH CAUTION')).toBeInTheDocument();
    });

    it('shows correct submit button text in production mode', () => {
      render(<Login {...defaultProps} />);

      const productionButton = screen.getByText('PRODUCTION');
      fireEvent.click(productionButton);

      expect(screen.getByText('🔓 UNLOCK PRODUCTION')).toBeInTheDocument();
    });

    it('shows correct footer text in production mode', () => {
      render(<Login {...defaultProps} />);

      const productionButton = screen.getByText('PRODUCTION');
      fireEvent.click(productionButton);

      expect(
        screen.getByText('RSA-SHA256 Encrypted Session • Real Funds at Risk')
      ).toBeInTheDocument();
    });

    it('validates empty password in production mode', async () => {
      render(<Login {...defaultProps} />);

      const productionButton = screen.getByText('PRODUCTION');
      fireEvent.click(productionButton);

      const submitButton = screen.getByText('🔓 UNLOCK PRODUCTION');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Password is required for Production Mode')).toBeInTheDocument();
      });

      expect(mockOnLogin).not.toHaveBeenCalled();
    });

    it('validates incorrect password in production mode', async () => {
      render(<Login {...defaultProps} />);

      const productionButton = screen.getByText('PRODUCTION');
      fireEvent.click(productionButton);

      const passwordInput = screen.getByPlaceholderText('Enter production password');
      fireEvent.change(passwordInput, { target: { value: 'wrong-password' } });

      const submitButton = screen.getByText('🔓 UNLOCK PRODUCTION');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Invalid password')).toBeInTheDocument();
      });

      expect(mockOnLogin).not.toHaveBeenCalled();
    });

    it('calls onLogin with production mode and password when correct password is entered', async () => {
      render(<Login {...defaultProps} />);

      const productionButton = screen.getByText('PRODUCTION');
      fireEvent.click(productionButton);

      const passwordInput = screen.getByPlaceholderText('Enter production password');
      fireEvent.change(passwordInput, { target: { value: '993728' } });

      const submitButton = screen.getByText('🔓 UNLOCK PRODUCTION');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnLogin).toHaveBeenCalledWith('production', '993728');
      });
    });
  });

  describe('Error States', () => {
    it('displays authError when provided', () => {
      render(<Login {...defaultProps} authError="Server connection failed" />);

      expect(screen.getByText('Server connection failed')).toBeInTheDocument();
    });

    it('clears local error when mode is changed', async () => {
      render(<Login {...defaultProps} />);

      // Switch to production and trigger validation error
      const productionButton = screen.getByText('PRODUCTION');
      fireEvent.click(productionButton);

      const submitButton = screen.getByText('🔓 UNLOCK PRODUCTION');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Password is required for Production Mode')).toBeInTheDocument();
      });

      // Switch to demo mode - error should be cleared
      const demoButton = screen.getByText('DEMO MODE');
      fireEvent.click(demoButton);

      expect(
        screen.queryByText('Password is required for Production Mode')
      ).not.toBeInTheDocument();
    });
  });

  describe('Loading States', () => {
    it('disables buttons when authenticating', () => {
      render(<Login {...defaultProps} isAuthenticating={true} />);

      const demoButton = screen.getByText('DEMO MODE');
      expect(demoButton.parentElement?.parentElement).toBeDisabled();
    });

    it('shows authenticating text when isAuthenticating is true', () => {
      render(<Login {...defaultProps} isAuthenticating={true} />);

      expect(screen.getByText('AUTHENTICATING...')).toBeInTheDocument();
    });

    it('disables submit button when authenticating', () => {
      render(<Login {...defaultProps} isAuthenticating={true} />);

      const submitButton = screen.getByText('AUTHENTICATING...');
      expect(submitButton.parentElement).toBeDisabled();
    });
  });

  describe('Password Visibility', () => {
    it('toggles password visibility when eye button is clicked', () => {
      render(<Login {...defaultProps} />);

      const productionButton = screen.getByText('PRODUCTION');
      fireEvent.click(productionButton);

      const passwordInput = screen.getByPlaceholderText(
        'Enter production password'
      ) as HTMLInputElement;
      expect(passwordInput.type).toBe('password');

      const toggleButton = screen.getByText('👁️');
      fireEvent.click(toggleButton);

      expect(passwordInput.type).toBe('text');
    });

    it('shows hide password icon when password is visible', () => {
      render(<Login {...defaultProps} />);

      const productionButton = screen.getByText('PRODUCTION');
      fireEvent.click(productionButton);

      const toggleButton = screen.getByText('👁️');
      fireEvent.click(toggleButton);

      expect(screen.getByText('🙈')).toBeInTheDocument();
    });
  });

  describe('Visual Elements', () => {
    it('renders the logo with correct text', () => {
      render(<Login {...defaultProps} />);

      const logo = screen.getByText('S');
      expect(logo).toBeInTheDocument();
    });

    it('has correct mode selection label', () => {
      render(<Login {...defaultProps} />);

      expect(screen.getByText('Select Trading Mode')).toBeInTheDocument();
    });

    it('has correct password label in production mode', () => {
      render(<Login {...defaultProps} />);

      const productionButton = screen.getByText('PRODUCTION');
      fireEvent.click(productionButton);

      expect(screen.getByText('Authorization Password')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles rapid mode switching', () => {
      render(<Login {...defaultProps} />);

      const demoButton = screen.getByText('DEMO MODE');
      const productionButton = screen.getByText('PRODUCTION');

      // Rapid switching
      fireEvent.click(productionButton);
      fireEvent.click(demoButton);
      fireEvent.click(productionButton);
      fireEvent.click(demoButton);

      // Should end in demo mode
      expect(demoButton.parentElement?.parentElement?.className).toContain('bg-cyan-500');
    });

    it('clears password when switching modes', () => {
      render(<Login {...defaultProps} />);

      const productionButton = screen.getByText('PRODUCTION');
      fireEvent.click(productionButton);

      const passwordInput = screen.getByPlaceholderText(
        'Enter production password'
      ) as HTMLInputElement;
      fireEvent.change(passwordInput, { target: { value: 'some-password' } });

      // Switch to demo and back to production
      const demoButton = screen.getByText('DEMO MODE');
      fireEvent.click(demoButton);
      fireEvent.click(productionButton);

      // Password should be cleared
      const newPasswordInput = screen.getByPlaceholderText(
        'Enter production password'
      ) as HTMLInputElement;
      expect(newPasswordInput.value).toBe('');
    });

    it('handles form submission via enter key', async () => {
      render(<Login {...defaultProps} />);

      const form = screen.getByText('ENTER DEMO MODE').closest('form');
      fireEvent.submit(form!);

      await waitFor(() => {
        expect(mockOnLogin).toHaveBeenCalledWith('demo', undefined);
      });
    });
  });
});
