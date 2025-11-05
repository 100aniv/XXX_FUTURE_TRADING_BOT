-- Add trial_id column to trading.trades table
-- Migration: 2025-11-01
-- Purpose: 백테스트 세그먼트 구분을 위한 trial_id 지원

BEGIN;

-- Add trial_id column if not exists
ALTER TABLE trading.trades 
ADD COLUMN IF NOT EXISTS trial_id VARCHAR(100);

-- Add index for trial_id filtering
CREATE INDEX IF NOT EXISTS idx_trades_trial_id 
ON trading.trades(trial_id) 
WHERE trial_id IS NOT NULL;

-- Add composite index for common queries
CREATE INDEX IF NOT EXISTS idx_trades_trial_status 
ON trading.trades(trial_id, status) 
WHERE trial_id IS NOT NULL;

-- Update comment
COMMENT ON COLUMN trading.trades.trial_id IS '백테스트 trial 식별자 (예: trial_0001_seg1, WFA_2024Q1_IS)';

COMMIT;

-- Verify
SELECT column_name, data_type, character_maximum_length, is_nullable
FROM information_schema.columns 
WHERE table_schema = 'trading' 
  AND table_name = 'trades' 
  AND column_name = 'trial_id';

-- Check indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'trading'
  AND tablename = 'trades'
  AND indexname LIKE '%trial%';
