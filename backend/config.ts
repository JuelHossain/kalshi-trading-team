import { SHARED_CONFIG } from '../shared/config';

export const CONFIG = {
    ...SHARED_CONFIG,

    // Scout
    GROQ_API_KEY: process.env.GROQ_API_KEY || '',
    GEMINI_API_KEY: process.env.GEMINI_API_KEY || process.env.API_KEY || '',

    // Historian
    SUPABASE_URL: process.env.SUPABASE_URL || '',
    SUPABASE_KEY: process.env.SUPABASE_KEY || '',

    // Kalshi Environments
    KALSHI: {
        ...SHARED_CONFIG.KALSHI,
        DEMO_KEY_ID: process.env.KALSHI_DEMO_KEY_ID || '',
        DEMO_PRIVATE_KEY: process.env.KALSHI_DEMO_PRIVATE_KEY || '',
        PROD_KEY_ID: process.env.KALSHI_PROD_KEY_ID || '',
        PROD_PRIVATE_KEY: process.env.KALSHI_PROD_PRIVATE_KEY || '',
        EMAIL: process.env.KALSHI_EMAIL || '',
        PASSWORD: process.env.KALSHI_PASSWORD || ''
    },

    // Signal Interceptor
    RAPID_API_KEY: process.env.RAPID_API_KEY || '',

    // Agent 1: The Ghost (Controls)
    KILL_SWITCH: process.env.KILL_SWITCH === 'true',
    MAINTENANCE_WINDOW: {
        ENABLED: true,
        START_HOUR: 23,
        START_MINUTE: 55
    }
};