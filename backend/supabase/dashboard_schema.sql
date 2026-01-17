-- Sentient Alpha Trading System - Additional Schema for Dashboard & Monitoring
-- Run this in your Supabase SQL Editor (in addition to existing schema.sql)

-- 1. Agent Heartbeats Table
-- Tracks live status of all 14 agents
CREATE TABLE IF NOT EXISTS agent_heartbeats (
    agent_id INT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    last_active TIMESTAMPTZ DEFAULT NOW()
);

-- 2. System Status Table
-- Used by circuit breakers and kill switches
CREATE TABLE IF NOT EXISTS system_status (
    id INT PRIMARY KEY DEFAULT 1,
    status TEXT DEFAULT 'ACTIVE',
    reason TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default system status
INSERT INTO system_status (id, status, reason, updated_at)
VALUES (1, 'ACTIVE', 'System initialized', NOW())
ON CONFLICT (id) DO NOTHING;

-- 3. Balance History Table
-- Tracks vault balance over time for PnL calculations
CREATE TABLE IF NOT EXISTS balance_history (
    id SERIAL PRIMARY KEY,
    balance_cents BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster date-based queries
CREATE INDEX IF NOT EXISTS idx_balance_history_created_at 
ON balance_history(created_at DESC);

-- 4. Enable Row Level Security (RLS) - Optional but recommended
ALTER TABLE agent_heartbeats ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE balance_history ENABLE ROW LEVEL SECURITY;

-- Create policies to allow service role access
CREATE POLICY "Allow service role full access to agent_heartbeats"
ON agent_heartbeats FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "Allow service role full access to system_status"
ON system_status FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "Allow service role full access to balance_history"
ON balance_history FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Success message
SELECT 'Dashboard schema created successfully!' AS status;
