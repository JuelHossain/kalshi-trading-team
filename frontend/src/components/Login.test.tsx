import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Login from './Login';

describe('Login', () => {
  const onLogin = vi.fn().mockResolvedValue(undefined);
  const props = { onLogin, authError: null as string | null, isAuthenticating: false };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the title, the mode control and the paper note', () => {
    render(<Login {...props} />);
    expect(screen.getByRole('heading', { name: 'Sentient Alpha' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'Demo' })).toBeChecked();
    expect(screen.getByRole('radio', { name: 'Production' })).not.toBeChecked();
    expect(screen.getByText('Paper fills · nothing at risk')).toBeInTheDocument();
    expect(screen.getByText(/Password checked by the engine/)).toBeInTheDocument();
    expect(screen.getByLabelText('Authorization password')).toBeInTheDocument();
  });

  it('refuses an empty password without calling the engine', async () => {
    render(<Login {...props} />);
    fireEvent.click(screen.getByRole('button', { name: 'Enter' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Authorization password is required');
    expect(onLogin).not.toHaveBeenCalled();
  });

  it('enters demo mode with the engine password', async () => {
    render(<Login {...props} />);
    fireEvent.change(screen.getByLabelText('Authorization password'), { target: { value: 'hunter22' } });
    fireEvent.click(screen.getByRole('button', { name: 'Enter' }));
    await waitFor(() => expect(onLogin).toHaveBeenCalledWith('demo', 'hunter22'));
  });

  it('switches the note and the call to action in production mode', async () => {
    render(<Login {...props} />);
    fireEvent.click(screen.getByRole('radio', { name: 'Production' }));
    expect(screen.getByText('Signed orders · real funds')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Authorization password'), { target: { value: 'hunter22' } });
    fireEvent.click(screen.getByRole('button', { name: 'Authorize' }));
    await waitFor(() => expect(onLogin).toHaveBeenCalledWith('production', 'hunter22'));
  });

  it('never compares the password locally', async () => {
    render(<Login {...props} />);
    fireEvent.change(screen.getByLabelText('Authorization password'), { target: { value: 'anything' } });
    fireEvent.click(screen.getByRole('button', { name: 'Enter' }));
    await waitFor(() => expect(onLogin).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('surfaces the engine error and disables the button while authenticating', () => {
    const { rerender } = render(<Login {...props} authError="Invalid password" />);
    expect(screen.getByRole('alert')).toHaveTextContent('Invalid password');
    rerender(<Login {...props} isAuthenticating />);
    expect(screen.getByRole('button', { name: 'Connecting…' })).toBeDisabled();
    expect(screen.getByLabelText('Authorization password')).toBeDisabled();
  });
});
