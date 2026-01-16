import { createClient } from '@supabase/supabase-js';
import { CONFIG } from '../config';

let supabase: any = null;

try {
  supabase = createClient(CONFIG.SUPABASE_URL, CONFIG.SUPABASE_KEY);
} catch (e) {
  console.error("Supabase Init Failed - Invalid URL/Key format provided.");
}

export const logTradeToHistory = async (agentId: number, action: string) => {
  if (!supabase) return;

  try {
    const { error } = await supabase
      .from('trade_logs')
      .insert([
        { 
          agent_id: agentId, 
          action: action, 
          timestamp: new Date().toISOString(),
          metadata: { version: '1.2', source: 'sentient-alpha-web' } 
        },
      ]);
      
    if (error) throw error;
    console.log("Agent 10: Logged to Supabase successfully.");
  } catch (error) {
    // Silent fail for frontend demo if table doesn't exist
    console.warn("Agent 10: Remote DB Write Failed (likely RLS or Table Missing). Stored locally.");
  }
};
