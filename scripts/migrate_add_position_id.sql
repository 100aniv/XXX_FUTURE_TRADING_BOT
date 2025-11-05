-- Migration: Add position_id to trading.trades
-- Date: 2025-10-28
-- Purpose: Link trades to positions for better tracking

-- Add position_id column to trades table
ALTER TABLE trading.trades 
ADD COLUMN IF NOT EXISTS position_id TEXT;

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_trades_position ON trading.trades (position_id);

-- Success message
DO $$
BEGIN
  RAISE NOTICE '✅ Migration completed: position_id added to trading.trades';
END $$;
