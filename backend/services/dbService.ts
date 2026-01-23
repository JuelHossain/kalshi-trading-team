import { createClient } from '@supabase/supabase-js';
import { CONFIG } from '../config';

const supabaseUrl = CONFIG.SUPABASE_URL || process.env.SUPABASE_URL;
const supabaseKey = CONFIG.SUPABASE_KEY || process.env.SUPABASE_KEY;

export const supabase = (supabaseUrl && supabaseKey)
    ? createClient(supabaseUrl, supabaseKey)
    : null;

export const logToDb = async (table: string, data: any) => {
    if (!supabase) {
        console.warn(`[DB Service] Supabase Offline. Skipping log to ${table}.`);
        return;
    }
    const { error } = await supabase.from(table).insert([data]);
    if (error) console.error(`[DB Service] Error inserting into ${table}:`, error);
};


export const sendHeartbeat = async (agentId: number, name: string, status: string = 'ACTIVE') => {
    if (!supabase) return;

    const { error } = await supabase
        .from('agent_heartbeats')
        .upsert({
            agent_id: agentId,
            agent_name: name,
            status: status,
            last_active: new Date().toISOString()
        }, { onConflict: 'agent_id' });

    if (error) console.error(`[DB Service] Heartbeat Failed for Agent ${agentId}:`, error);
};

export const getPnLHistory = async (hours: number = 24) => {
    if (!supabase) return [];
    
    const startTime = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();
    
    // Assuming balance_history has created_at and balance_cents
    const { data, error } = await supabase
        .from('balance_history')
        .select('created_at, balance_cents')
        .gte('created_at', startTime)
        .order('created_at', { ascending: true });
        
    if (error) {
        console.error("[DB Service] Failed to fetch PnL history:", error);
        return [];
    }
    
    return data.map((d: any) => ({
        timestamp: d.created_at,
        balance: d.balance_cents / 100
    }));
};

export const getDailyPnL = async (days: number = 365) => {
    if (!supabase) return [];
    
    const startTime = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
    
    // For heatmap, we need daily close balances.
    // This is a simplification; ideally we'd use a postgres view or aggregate query.
    // Fetching all might be heavy, but for <365 days it's likely okay for now.
    const { data, error } = await supabase
        .from('balance_history')
        .select('created_at, balance_cents')
        .gte('created_at', startTime)
        .order('created_at', { ascending: true });
        
    if (error) {
        console.error("[DB Service] Failed to fetch Daily PnL:", error);
        return [];
    }
    
    return data;
};

