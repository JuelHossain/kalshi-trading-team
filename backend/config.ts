// API Configuration
// NOTE: RSA Private keys are excluded for client-side security.
// Gemini API Key is retrieved from process.env.API_KEY per standard.

export const CONFIG = {
    // Agent 2: Scout
    GROQ_API_KEY: process.env.GROQ_API_KEY || '',
    GEMINI_API_KEY: process.env.API_KEY || '', // Added for SystemHealth check

    // Agent 10: Historian
    SUPABASE_URL: process.env.SUPABASE_URL || '',
    SUPABASE_KEY: process.env.SUPABASE_KEY || '',

    // Agent 1/7/8: Kalshi Environments
    KALSHI: {
        PROD_API: 'https://api.elections.kalshi.com/trade-api/v2',
        SANDBOX_API: 'https://demo-api.kalshi.com/trade-api/v2',
        DEMO_KEY_ID: process.env.KALSHI_DEMO_KEY_ID || '',
        DEMO_PRIVATE_KEY: process.env.KALSHI_DEMO_PRIVATE_KEY || '',
        PROD_KEY_ID: process.env.KALSHI_PROD_KEY_ID || '',
        PROD_PRIVATE_KEY: process.env.KALSHI_PROD_PRIVATE_KEY || '',
        EMAIL: process.env.KALSHI_EMAIL || '',
        PASSWORD: process.env.KALSHI_PASSWORD || ''
    },

    // Agent 3: Signal Interceptor
    RAPID_API_KEY: process.env.RAPID_API_KEY || ''
};