-- PR12: Paper/Live 모드 분리를 위한 mode 컬럼 추가
-- 작성일: 2025-11-08
-- 목적: Paper 모드와 Live 모드의 거래/포지션을 완전히 분리

-- ============================================
-- 1. trading.trades 테이블에 mode 컬럼 추가
-- ============================================
ALTER TABLE trading.trades 
ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'paper' CHECK (mode IN ('paper', 'live', 'backtest'));

-- 기존 데이터는 paper로 설정
UPDATE trading.trades SET mode = 'paper' WHERE mode IS NULL;

-- mode를 NOT NULL로 변경
ALTER TABLE trading.trades ALTER COLUMN mode SET NOT NULL;

-- mode 인덱스 추가 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_trades_mode_status ON trading.trades (mode, status, ts_open DESC);

-- ============================================
-- 2. trading.positions 테이블에 mode 컬럼 추가
-- ============================================
ALTER TABLE trading.positions 
ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'paper' CHECK (mode IN ('paper', 'live', 'backtest'));

-- 기존 데이터는 paper로 설정
UPDATE trading.positions SET mode = 'paper' WHERE mode IS NULL;

-- mode를 NOT NULL로 변경
ALTER TABLE trading.positions ALTER COLUMN mode SET NOT NULL;

-- UNIQUE 제약 조건 업데이트 (mode 포함)
ALTER TABLE trading.positions DROP CONSTRAINT IF EXISTS positions_symbol_side_strategy_id_key;
ALTER TABLE trading.positions ADD CONSTRAINT positions_symbol_side_strategy_mode_key 
  UNIQUE(symbol, side, strategy_id, mode);

-- mode 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_positions_mode ON trading.positions (mode, symbol);

-- ============================================
-- 3. monitoring.signals 테이블에 mode 컬럼 추가
-- ============================================
ALTER TABLE monitoring.signals 
ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'paper' CHECK (mode IN ('paper', 'live', 'backtest'));

-- 기존 데이터는 paper로 설정
UPDATE monitoring.signals SET mode = 'paper' WHERE mode IS NULL;

-- mode를 NOT NULL로 변경
ALTER TABLE monitoring.signals ALTER COLUMN mode SET NOT NULL;

-- mode 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_signals_mode ON monitoring.signals (mode, strategy_id, candle_closed_at DESC);

-- ============================================
-- 4. trading.decisions 테이블에 mode 컬럼 추가
-- ============================================
ALTER TABLE trading.decisions 
ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'paper' CHECK (mode IN ('paper', 'live', 'backtest'));

-- 기존 데이터는 paper로 설정
UPDATE trading.decisions SET mode = 'paper' WHERE mode IS NULL;

-- mode를 NOT NULL로 변경
ALTER TABLE trading.decisions ALTER COLUMN mode SET NOT NULL;

-- mode 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_decisions_mode ON trading.decisions (mode, symbol, candle_closed_at DESC);

-- ============================================
-- 5. reporting.daily_pnl 테이블에 mode 컬럼 추가
-- ============================================
ALTER TABLE reporting.daily_pnl 
ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'paper' CHECK (mode IN ('paper', 'live', 'backtest'));

-- 기존 데이터는 paper로 설정
UPDATE reporting.daily_pnl SET mode = 'paper' WHERE mode IS NULL;

-- mode를 NOT NULL로 변경
ALTER TABLE reporting.daily_pnl ALTER COLUMN mode SET NOT NULL;

-- PRIMARY KEY 재정의 (mode 포함)
ALTER TABLE reporting.daily_pnl DROP CONSTRAINT IF EXISTS daily_pnl_pkey;
ALTER TABLE reporting.daily_pnl ADD CONSTRAINT daily_pnl_pkey 
  PRIMARY KEY(date, strategy_id, COALESCE(symbol, ''), mode);

-- 완료 메시지
DO $$
BEGIN
  RAISE NOTICE '✅ PR12: mode 컬럼 추가 완료!';
  RAISE NOTICE '   - trading.trades: mode 컬럼 추가 및 인덱스 생성';
  RAISE NOTICE '   - trading.positions: mode 컬럼 추가 및 UNIQUE 제약 업데이트';
  RAISE NOTICE '   - monitoring.signals: mode 컬럼 추가';
  RAISE NOTICE '   - trading.decisions: mode 컬럼 추가';
  RAISE NOTICE '   - reporting.daily_pnl: mode 컬럼 추가 및 PRIMARY KEY 업데이트';
  RAISE NOTICE '   ⚠️  Paper/Live 모드가 완전히 분리되었습니다!';
END $$;
