/**
 * The login screen from the design handoff: a centred 360px column, a
 * Demo/Production segmented control, a password field for Production, and
 * the RSA-SHA256 note. The password is never checked here; the engine
 * validates it and answers 401 if it is wrong.
 */
import React, { useEffect, useState } from 'react';
import { Drift } from '../cockpit/Cockpit';
import { AC, ACI, ACS, E, F, G, glassStyle, mix, PALETTES, paletteVars, T1, T4 } from '../cockpit/palette';
import { useCockpit } from '../cockpit/store';

export type AuthMode = 'demo' | 'production';

interface LoginProps {
  onLogin: (mode: AuthMode, password?: string) => Promise<void>;
  authError: string | null;
  isAuthenticating: boolean;
}

const Login: React.FC<LoginProps> = ({ onLogin, authError, isAuthenticating }) => {
  const palette = useCockpit((s) => s.palette);
  const pal = PALETTES[palette];
  const [selectedMode, setSelectedMode] = useState<AuthMode>('demo');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    setLocalError(null);
  }, [selectedMode]);

  const isProduction = selectedMode === 'production';
  const error = localError || authError;

  // The engine requires its AUTH_PASSWORD for every session; the mode only
  // records whether cycles are requested as paper or live. Only presence is
  // checked here -- the engine validates the value and answers 401.
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    if (!password.trim()) {
      setLocalError('Authorization password is required');
      return;
    }
    try {
      await onLogin(selectedMode, password);
    } catch {
      /* the hook surfaces authError */
    }
  };

  const modeBtn = (on: boolean): React.CSSProperties => ({
    flex: 1,
    border: 'none',
    borderRadius: 999,
    padding: '9px 14px',
    fontSize: 12,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background 0.18s',
    background: on ? ACS : 'transparent',
    color: on ? ACI : T4,
  });

  return (
    <div
      style={{
        ...paletteVars(pal),
        position: 'relative',
        height: '100vh',
        width: '100%',
        overflow: 'hidden',
        background: G,
        color: T1,
        fontFamily: 'var(--font-body)',
      }}
    >
      <Drift />
      <div style={{ position: 'relative', zIndex: 1, height: '100%', display: 'flex', alignItems: 'center', overflow: 'hidden' }}>
        <form
          onSubmit={handleSubmit}
          style={{ position: 'relative', zIndex: 2, width: '100%', maxWidth: 360, margin: '0 auto', padding: '0 24px', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}
        >
          <div style={{ width: 44, height: 44, borderRadius: 999, background: ACS, display: 'grid', placeItems: 'center', color: ACI, fontFamily: 'var(--font-heading)', fontSize: 21 }}>S</div>
          <h1 style={{ fontFamily: 'var(--font-heading)', fontWeight: 400, fontSize: 28, lineHeight: 1.1, margin: '22px 0 0', color: T1 }}>Sentient Alpha</h1>
          <div style={{ fontSize: 13, color: T4, marginTop: 6 }}>{isProduction ? 'Signed orders · real funds' : 'Paper fills · nothing at risk'}</div>

          <div role="radiogroup" aria-label="mode" style={{ display: 'flex', gap: 2, padding: 3, borderRadius: 999, marginTop: 28, width: '100%', ...glassStyle(pal) }}>
            <button type="button" role="radio" aria-checked={!isProduction} onClick={() => setSelectedMode('demo')} style={modeBtn(!isProduction)}>
              Demo
            </button>
            <button type="button" role="radio" aria-checked={isProduction} onClick={() => setSelectedMode('production')} style={modeBtn(isProduction)}>
              Production
            </button>
          </div>

          <div style={{ marginTop: 12, width: '100%' }}>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Authorization password"
              aria-label="Authorization password"
              autoComplete="current-password"
              disabled={isAuthenticating}
              style={{ width: '100%', padding: '12px 18px', borderRadius: 999, ...glassStyle(pal), color: T1, fontSize: 14, outline: 'none', textAlign: 'center' }}
            />
          </div>

          {error && (
            <div role="alert" style={{ marginTop: 12, width: '100%', fontSize: 12, fontWeight: 600, color: AC, padding: '9px 14px', borderRadius: 999, background: mix(ACS, 12), border: `1px solid ${mix(ACS, 40, E)}` }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isAuthenticating}
            style={{ width: '100%', marginTop: 12, border: 'none', background: ACS, color: ACI, borderRadius: 999, padding: '13px 30px', fontWeight: 600, fontSize: 15, cursor: isAuthenticating ? 'wait' : 'pointer', opacity: isAuthenticating ? 0.7 : 1 }}
          >
            {isAuthenticating ? 'Connecting…' : isProduction ? 'Authorize' : 'Enter'}
          </button>
          <div style={{ fontSize: 11, color: F, marginTop: 18 }}>RSA-SHA256 signed session</div>
        </form>
      </div>
    </div>
  );
};

export default Login;
