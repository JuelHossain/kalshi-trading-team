-- Migration: Create opportunity_queue and execution_queue tables
-- For: Sentient Alpha - Ghost Engine
-- Date: 2026-01-29

-- ============================================
-- OPPORTUNITY QUEUE
-- Stores market opportunities identified by SensesAgent
-- ============================================

CREATE TABLE IF NOT EXISTS public.opportunity_queue (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('YES', 'NO')),
    confidence DECIMAL(3, 2) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    price DECIMAL(10, 4) NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'brain_approved', 'brain_rejected', 'expired')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient querying by status and expiration
CREATE INDEX IF NOT EXISTS idx_opportunity_status ON public.opportunity_queue(status);
CREATE INDEX IF NOT EXISTS idx_opportunity_expires ON public.opportunity_queue(expires_at) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_opportunity_ticker ON public.opportunity_queue(ticker);

-- ============================================
-- EXECUTION QUEUE
-- Stores trade decisions from BrainAgent
-- ============================================

CREATE TABLE IF NOT EXISTS public.execution_queue (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    opportunity_id UUID REFERENCES public.opportunity_queue(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('YES', 'NO')),
    size DECIMAL(10, 2) NOT NULL,
    price DECIMAL(10, 4) NOT NULL,
    rationale TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'executing', 'completed', 'failed', 'cancelled')),
    executed_at TIMESTAMP WITH TIME ZONE,
    execution_result JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient querying
CREATE INDEX IF NOT EXISTS idx_execution_status ON public.execution_queue(status);
CREATE INDEX IF NOT EXISTS idx_execution_opportunity ON public.execution_queue(opportunity_id);

-- ============================================
-- ROW LEVEL SECURITY POLICIES
-- ============================================

-- Enable RLS on both tables
ALTER TABLE public.opportunity_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.execution_queue ENABLE ROW LEVEL SECURITY;

-- Policy: Allow all operations for authenticated users
-- (Adjust based on your actual auth setup)
CREATE POLICY "Enable all operations for authenticated users" ON public.opportunity_queue
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Enable all operations for authenticated users" ON public.execution_queue
    FOR ALL USING (auth.role() = 'authenticated');

-- ============================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for opportunity_queue
DROP TRIGGER IF EXISTS update_opportunity_queue_updated_at ON public.opportunity_queue;
CREATE TRIGGER update_opportunity_queue_updated_at
    BEFORE UPDATE ON public.opportunity_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for execution_queue
DROP TRIGGER IF EXISTS update_execution_queue_updated_at ON public.execution_queue;
CREATE TRIGGER update_execution_queue_updated_at
    BEFORE UPDATE ON public.execution_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================

COMMENT ON TABLE public.opportunity_queue IS 'Stores market opportunities detected by SensesAgent before Brain review';
COMMENT ON TABLE public.execution_queue IS 'Stores trade execution decisions made by BrainAgent for HandAgent to execute';
