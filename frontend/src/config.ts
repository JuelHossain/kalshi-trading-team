import { SHARED_CONFIG } from '@shared/config';

// API Configuration for Frontend (Public/Exposed values only)
// Vite uses import.meta.env instead of process.env
const env = import.meta.env;

export const CONFIG = {
  ...SHARED_CONFIG,

  // Scout / Analyst
  GROQ_API_KEY: env.VITE_GROQ_API_KEY || '',
  GEMINI_API_KEY: env.VITE_GEMINI_API_KEY || '',

  // Historian
  SUPABASE_URL: env.VITE_SUPABASE_URL || '',
  SUPABASE_KEY: env.VITE_SUPABASE_KEY || '',

  // Kalshi Environments
  KALSHI: {
    ...SHARED_CONFIG.KALSHI,
    DEMO_KEY_ID: env.VITE_KALSHI_DEMO_KEY_ID || '',
    PROD_KEY_ID: env.VITE_KALSHI_PROD_KEY_ID || '',
    // Private keys strictly excluded from frontend build
  },

  // Signal Interceptor
  RAPID_API_KEY: env.VITE_RAPID_API_KEY || '',
};
