import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

export type AuthMode = 'demo' | 'production';

interface LoginProps {
  onLogin: (mode: AuthMode, password?: string) => Promise<void>;
  authError: string | null;
  isAuthenticating: boolean;
}

const Login: React.FC<LoginProps> = ({ onLogin, authError, isAuthenticating }) => {
  const [selectedMode, setSelectedMode] = useState<AuthMode>('demo');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  // Clear errors when mode changes
  useEffect(() => {
    setLocalError(null);
    setPassword('');
    setShowPassword(false);
  }, [selectedMode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    // Validate production mode password
    if (selectedMode === 'production') {
      if (!password.trim()) {
        setLocalError('Password is required for Production Mode');
        return;
      }
      if (password !== '993728') {
        setLocalError('Invalid password');
        return;
      }
    }

    await onLogin(selectedMode, selectedMode === 'production' ? password : undefined);
  };

  const isProduction = selectedMode === 'production';

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-6 bg-grid-pattern relative overflow-hidden">
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl animate-pulse"></div>
        <div
          className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/5 rounded-full blur-3xl animate-pulse"
          style={{ animationDelay: '1s' }}
        ></div>
      </div>

      {/* Production Mode Warning Banner */}
      {isProduction && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          className="absolute top-0 left-0 right-0 bg-red-600 text-white py-3 px-6 text-center z-50"
        >
          <div className="flex items-center justify-center gap-3">
            <span className="text-xl animate-pulse">⚠️</span>
            <span className="font-bold tracking-widest uppercase text-sm">
              REAL MONEY TRADING - PROCEED WITH CAUTION
            </span>
            <span className="text-xl animate-pulse">⚠️</span>
          </div>
        </motion.div>
      )}

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className={`glass-panel w-full max-w-md p-8 rounded-2xl animate-scale-in shadow-2xl relative z-10 ${
          isProduction
            ? 'border-red-500/30 shadow-[0_0_50px_rgba(239,68,68,0.15)]'
            : 'border-emerald-500/20 shadow-[0_0_50px_rgba(16,185,129,0.1)]'
        }`}
      >
        {/* Logo */}
        <div className="flex justify-center mb-6">
          <motion.div
            whileHover={{ scale: 1.05 }}
            className={`w-16 h-16 rounded-2xl flex items-center justify-center shadow-lg ${
              isProduction
                ? 'bg-gradient-to-br from-red-400 to-red-700 shadow-[0_0_30px_rgba(239,68,68,0.3)]'
                : 'bg-gradient-to-br from-emerald-400 to-emerald-700 shadow-[0_0_30px_rgba(16,185,129,0.3)]'
            }`}
          >
            <span className="text-black font-black font-tech text-3xl">S</span>
          </motion.div>
        </div>

        {/* Title */}
        <h1
          className={`text-3xl font-tech font-bold text-center mb-2 tracking-tighter ${
            isProduction ? 'text-red-400' : 'text-gradient-emerald'
          }`}
        >
          SENTIENT ALPHA
        </h1>
        <p className="text-gray-500 text-center text-[10px] mb-8 font-mono tracking-[0.3em] uppercase opacity-70">
          Proprietary Trading Command Node
        </p>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Mode Selection */}
          <div>
            <label
              className={`text-[10px] font-mono mb-3 block uppercase tracking-widest ${
                isProduction ? 'text-red-400/70' : 'text-emerald-500/70'
              }`}
            >
              Select Trading Mode
            </label>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setSelectedMode('demo')}
                disabled={isAuthenticating}
                className={`flex-1 py-3 px-4 rounded-xl text-[11px] font-bold transition-all duration-300 border ${
                  selectedMode === 'demo'
                    ? 'bg-cyan-500 text-black border-cyan-500 shadow-lg shadow-cyan-500/20'
                    : 'bg-white/5 text-gray-400 border-white/10 hover:bg-white/10 hover:text-gray-300'
                } ${isAuthenticating ? 'cursor-not-allowed opacity-50' : ''}`}
              >
                <div className="flex flex-col items-center gap-1">
                  <span className="text-lg">🧪</span>
                  <span>DEMO MODE</span>
                </div>
              </button>
              <button
                type="button"
                onClick={() => setSelectedMode('production')}
                disabled={isAuthenticating}
                className={`flex-1 py-3 px-4 rounded-xl text-[11px] font-bold transition-all duration-300 border ${
                  selectedMode === 'production'
                    ? 'bg-red-500 text-white border-red-500 shadow-lg shadow-red-500/20'
                    : 'bg-white/5 text-gray-400 border-white/10 hover:bg-white/10 hover:text-gray-300'
                } ${isAuthenticating ? 'cursor-not-allowed opacity-50' : ''}`}
              >
                <div className="flex flex-col items-center gap-1">
                  <span className="text-lg">💰</span>
                  <span>PRODUCTION</span>
                </div>
              </button>
            </div>
          </div>

          {/* Mode Description */}
          <div
            className={`p-4 rounded-xl border text-[11px] font-mono ${
              isProduction
                ? 'bg-red-500/5 border-red-500/20 text-red-300'
                : 'bg-cyan-500/5 border-cyan-500/20 text-cyan-300'
            }`}
          >
            {isProduction ? (
              <div className="space-y-2">
                <p className="font-bold uppercase tracking-wider">Production Environment</p>
                <ul className="space-y-1 text-gray-400">
                  <li>• Real Kalshi API (live markets)</li>
                  <li>• Actual monetary transactions</li>
                  <li>• Requires authorization password</li>
                </ul>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="font-bold uppercase tracking-wider">Demo Environment</p>
                <ul className="space-y-1 text-gray-400">
                  <li>• Kalshi Demo API (paper trading)</li>
                  <li>• No real money at risk</li>
                  <li>• No password required</li>
                </ul>
              </div>
            )}
          </div>

          {/* Password Input (Production Only) */}
          {isProduction && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
            >
              <label className="text-[10px] font-mono text-red-400/70 mb-2 block uppercase tracking-widest">
                Authorization Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isAuthenticating}
                  className="w-full bg-black/40 border border-red-500/30 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-red-500/60 font-mono transition-all placeholder:text-gray-700 text-white"
                  placeholder="Enter production password"
                  autoFocus
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 text-xs"
                >
                  {showPassword ? '🙈' : '👁️'}
                </button>
              </div>
            </motion.div>
          )}

          {/* Error Display */}
          {(authError || localError) && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-[10px] text-red-400 bg-red-500/5 p-3 rounded-xl border border-red-500/20 font-mono flex gap-3"
            >
              <span className="shrink-0">⚠️</span>
              <span>{authError || localError}</span>
            </motion.div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isAuthenticating}
            className={`w-full py-4 rounded-xl font-bold tracking-[0.15em] text-sm transition-all duration-300 relative overflow-hidden group ${
              isProduction
                ? 'bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-900/20'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-900/20'
            } ${isAuthenticating ? 'cursor-not-allowed opacity-70' : 'hover:scale-[1.02] active:scale-[0.98]'}`}
          >
            <div
              className={`absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:animate-[shimmer_2s_infinite] pointer-events-none ${isAuthenticating ? 'hidden' : ''}`}
            ></div>
            <span className="relative z-10 flex items-center justify-center gap-3">
              {isAuthenticating ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                  AUTHENTICATING...
                </>
              ) : (
                <>
                  {isProduction ? '🔓 UNLOCK PRODUCTION' : 'ENTER DEMO MODE'}
                  <span className="group-hover:translate-x-1 transition-transform">→</span>
                </>
              )}
            </span>
          </button>

          {/* Footer */}
          <p className="text-[8px] text-gray-700 text-center font-mono uppercase tracking-widest">
            {isProduction
              ? 'RSA-SHA256 Encrypted Session • Real Funds at Risk'
              : 'RSA-SHA256 Encrypted Session • Demo Environment'}
          </p>
        </form>
      </motion.div>
    </div>
  );
};

export default Login;
