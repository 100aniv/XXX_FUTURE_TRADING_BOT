-- Add leverage column to trading.trades table
-- Migration: 2025-10-20

BEGIN;

-- Add leverage column if not exists
ALTER TABLE trading.trades 
ADD COLUMN IF NOT EXISTS leverage DECIMAL(5,2) DEFAULT 1.0;

-- Update comment
COMMENT ON COLUMN trading.trades.leverage IS '레버리지 배수 (1.0 = 1배)';

COMMIT;

-- Verify
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_schema = 'trading' 
  AND table_name = 'trades' 
  AND column_name = 'leverage';
