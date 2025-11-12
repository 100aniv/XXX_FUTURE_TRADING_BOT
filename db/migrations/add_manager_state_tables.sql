-- PHASE7-2 항목 8: Manager 상태 복원 테이블 추가
-- 작성일: 2025-11-12
-- 목적: Paper 재시작 시 PortfolioManager/RiskManager 상태 복원

-- ============================================
-- 1. trading.portfolio_state (Portfolio Manager 상태)
-- ============================================
CREATE TABLE IF NOT EXISTS trading.portfolio_state (
    mode VARCHAR(10) NOT NULL CHECK (mode IN ('paper', 'live', 'backtest')),
    run_id UUID NOT NULL,
    current_equity NUMERIC NOT NULL,
    daily_pnl NUMERIC NOT NULL DEFAULT 0,
    realized_pnl NUMERIC NOT NULL DEFAULT 0,
    unrealized_pnl NUMERIC NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (mode, run_id, updated_at)
);

-- 인덱스: 최신 상태 조회 최적화
CREATE INDEX IF NOT EXISTS idx_portfolio_state_latest 
ON trading.portfolio_state (mode, run_id, updated_at DESC);

COMMENT ON TABLE trading.portfolio_state IS 'Portfolio Manager 상태 스냅샷 (PHASE7-2 항목 8)';
COMMENT ON COLUMN trading.portfolio_state.mode IS 'paper/live/backtest';
COMMENT ON COLUMN trading.portfolio_state.run_id IS '실행 ID (UUID)';
COMMENT ON COLUMN trading.portfolio_state.current_equity IS '현재 자산';
COMMENT ON COLUMN trading.portfolio_state.daily_pnl IS '일일 손익';
COMMENT ON COLUMN trading.portfolio_state.realized_pnl IS '실현 손익';
COMMENT ON COLUMN trading.portfolio_state.unrealized_pnl IS '미실현 손익';

-- ============================================
-- 2. trading.risk_state (Risk Manager 상태)
-- ============================================
CREATE TABLE IF NOT EXISTS trading.risk_state (
    mode VARCHAR(10) NOT NULL CHECK (mode IN ('paper', 'live', 'backtest')),
    run_id UUID NOT NULL,
    peak_equity NUMERIC NOT NULL,
    current_drawdown NUMERIC NOT NULL DEFAULT 0,
    consecutive_losses INT NOT NULL DEFAULT 0,
    in_cooldown BOOLEAN NOT NULL DEFAULT FALSE,
    cooldown_until TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (mode, run_id, updated_at)
);

-- 인덱스: 최신 상태 조회 최적화
CREATE INDEX IF NOT EXISTS idx_risk_state_latest 
ON trading.risk_state (mode, run_id, updated_at DESC);

COMMENT ON TABLE trading.risk_state IS 'Risk Manager 상태 스냅샷 (PHASE7-2 항목 8)';
COMMENT ON COLUMN trading.risk_state.mode IS 'paper/live/backtest';
COMMENT ON COLUMN trading.risk_state.run_id IS '실행 ID (UUID)';
COMMENT ON COLUMN trading.risk_state.peak_equity IS '최고 자산 (MDD 계산용)';
COMMENT ON COLUMN trading.risk_state.current_drawdown IS '현재 드로다운 (%)';
COMMENT ON COLUMN trading.risk_state.consecutive_losses IS '연속 손실 횟수';
COMMENT ON COLUMN trading.risk_state.in_cooldown IS '쿨다운 상태';
COMMENT ON COLUMN trading.risk_state.cooldown_until IS '쿨다운 종료 시각';

-- 완료 메시지
DO $$
BEGIN
  RAISE NOTICE '✅ Manager 상태 테이블 추가 완료!';
  RAISE NOTICE '   - trading.portfolio_state: Portfolio Manager 상태';
  RAISE NOTICE '   - trading.risk_state: Risk Manager 상태';
END $$;
