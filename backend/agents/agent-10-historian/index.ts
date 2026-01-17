import { CONFIG } from '../../config';
import { createClient } from '@supabase/supabase-js';

// Initialize Supabase Client locally for Agent 10
const supabase = (CONFIG.SUPABASE_URL && CONFIG.SUPABASE_KEY)
    ? createClient(CONFIG.SUPABASE_URL, CONFIG.SUPABASE_KEY)
    : null;

export const logTradeToHistory = async (agentId: number, details: string) => {
    if (!supabase) {
        throw new Error("[Agent 10] Supabase Offline. Cannot log trade.");
    }

    const { error } = await supabase
        .from('trade_history')
        .insert([
            {
                agent_id: agentId,
                details: details,
                timestamp: new Date().toISOString()
            }
        ]);

    if (error) {
        console.error("Supabase Log Error:", error);
        throw error;
    }
};
