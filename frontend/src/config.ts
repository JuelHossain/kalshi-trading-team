import { SHARED_CONFIG } from '@shared/config';

// API Configuration for Frontend (Public/Exposed values only)
export const CONFIG = {
  ...SHARED_CONFIG,

  // Scout / Analyst
  GROQ_API_KEY: process.env.GROQ_API_KEY || '',
  GEMINI_API_KEY: process.env.GEMINI_API_KEY || '',

  // Historian
  SUPABASE_URL: process.env.SUPABASE_URL || '',
  SUPABASE_KEY: process.env.SUPABASE_KEY || '',

  // Kalshi Environments
  KALSHI: {
    ...SHARED_CONFIG.KALSHI,
    DEMO_KEY_ID: process.env.KALSHI_DEMO_KEY_ID || '',
    PROD_KEY_ID: process.env.KALSHI_PROD_KEY_ID || '',
    // Private keys strictly excluded from frontend build
  },

  // Signal Interceptor
  RAPID_API_KEY: process.env.RAPID_API_KEY || '',
};
