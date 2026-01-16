// API Configuration
// NOTE: RSA Private keys are excluded for client-side security.
// Gemini API Key is retrieved from process.env.API_KEY per standard.

export const CONFIG = {
    // Agent 2: Scout
    GROQ_API_KEY: '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',
    
    // Agent 10: Historian
    SUPABASE_URL: 'https://db.sbxiiwvkiqmmmmdlqaev.supabase.co',
    SUPABASE_KEY: 'sb_publishable_5PtMghlyPMhL_agZUMPSNg_GFP9rOA7',
    
    // Agent 1/7/8: Kalshi Environments
    KALSHI: {
        PROD_API: 'https://api.elections.kalshi.com/trade-api/v2', // Specialized Election Endpoint
        SANDBOX_API: 'https://demo-api.kalshi.co/trade-api/v2'     // Paper Trading Endpoint
    },
    
    // Agent 3: Signal Interceptor
    RAPID_API_KEY: '379b9cd0ccmshdebb9b9fbf7ddc9p1dc678jsnfcdac3d8081a'
};
