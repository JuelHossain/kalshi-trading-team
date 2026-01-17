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

