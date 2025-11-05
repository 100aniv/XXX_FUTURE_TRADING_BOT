-- 트레이딩 시스템 데이터베이스 초기화
-- 작성일: 2025-10-14
-- 버전: v1.0

-- 스키마 생성
CREATE SCHEMA IF NOT EXISTS monitoring;
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS reporting;

-- ============================================
-- 1. monitoring.signals (모니터링 신호)
-- ============================================
-- 리팩토링 (2025-10-19): bot_id 제거 (옛날 3봇 시스템 유물)
CREATE TABLE IF NOT EXISTS monitoring.signals(
  signal_id        TEXT PRIMARY KEY,
  strategy_id      TEXT NOT NULL,              -- 'trend' | 'reversion' | 'breakout' | 'scalping' | 'daytrade' | 'swing'
  symbol           TEXT NOT NULL,
  timeframe        TEXT NOT NULL,
  candle_closed_at TIMESTAMPTZ NOT NULL,       -- 캔들 종료 시각 (UTC)
  direction        TEXT NOT NULL CHECK (direction IN ('LONG', 'SHORT', 'FLAT')),  -- 매수/매도 방향
  confidence       NUMERIC CHECK (confidence >= 0 AND confidence <= 1),
  entry_price      NUMERIC,
  sl_price         NUMERIC,
  tp_price         NUMERIC,
  atr              NUMERIC,
  leverage         INTEGER,
  features         JSONB,                      -- RSI, MACD, 레짐 등
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  -- ⭐ 멱등키: 동일 전략/심볼/타임프레임/캔들에 대해 1건만
  UNIQUE(strategy_id, symbol, timeframe, candle_closed_at)
);

CREATE INDEX idx_signals_strategy_ts ON monitoring.signals (strategy_id, candle_closed_at DESC);
CREATE INDEX idx_signals_symbol_ts ON monitoring.signals (symbol, candle_closed_at DESC);
CREATE INDEX idx_signals_created ON monitoring.signals (created_at DESC);

-- ============================================
-- 2. trading.decisions (통합 결정)
-- ============================================
CREATE TABLE IF NOT EXISTS trading.decisions(
  decision_id      TEXT PRIMARY KEY,
  symbol           TEXT NOT NULL,
  timeframe        TEXT NOT NULL,
  candle_closed_at TIMESTAMPTZ NOT NULL,
  chosen_side      TEXT NOT NULL,              -- 'LONG' | 'SHORT' | 'FLAT'
  chosen_size      NUMERIC NOT NULL,
  score            NUMERIC NOT NULL,
  weights          JSONB NOT NULL,
  from_signals     JSONB NOT NULL,
  reason           TEXT,
  entry_price      NUMERIC,                    -- ⭐ 앙상블 진입가
  sl_price         NUMERIC,                    -- ⭐ 앙상블 손절가
  tp_price         NUMERIC,                    -- ⭐ 앙상블 익절가
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  -- ⭐ 멱등키: 동일 심볼/타임프레임/캔들에 대해 1건만
  UNIQUE(symbol, timeframe, candle_closed_at)
);

CREATE INDEX idx_decisions_symbol_ts ON trading.decisions (symbol, candle_closed_at DESC);
CREATE INDEX idx_decisions_side ON trading.decisions (chosen_side, candle_closed_at DESC);

-- ============================================
-- 3. trading.trades (거래 기록)
-- ============================================
CREATE TABLE IF NOT EXISTS trading.trades(
  trade_id         TEXT PRIMARY KEY,
  decision_id      TEXT REFERENCES trading.decisions(decision_id),
  symbol           TEXT NOT NULL,
  side             TEXT NOT NULL CHECK (side IN ('LONG', 'SHORT')),
  entry_price      NUMERIC NOT NULL,
  exit_price       NUMERIC,
  quantity         NUMERIC NOT NULL,
  leverage         INTEGER NOT NULL,
  sl_price         NUMERIC,
  tp_price         NUMERIC,
  ts_open          TIMESTAMPTZ NOT NULL,
  ts_close         TIMESTAMPTZ,
  pnl              NUMERIC,
  pnl_pct          NUMERIC,
  fees             NUMERIC DEFAULT 0,
  status           TEXT NOT NULL CHECK (status IN ('OPEN', 'CLOSED', 'CANCELLED')),
  strategy_id      TEXT NOT NULL,
  exit_reason      TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_trades_symbol_ts ON trading.trades (symbol, ts_open DESC);
CREATE INDEX idx_trades_status ON trading.trades (status, ts_open DESC);
CREATE INDEX idx_trades_strategy ON trading.trades (strategy_id, ts_open DESC);

-- ============================================
-- 4. trading.positions (현재 포지션)
-- ============================================
CREATE TABLE IF NOT EXISTS trading.positions(
  position_id      TEXT PRIMARY KEY,
  symbol           TEXT NOT NULL,
  side             TEXT NOT NULL,
  quantity         NUMERIC NOT NULL,
  avg_entry        NUMERIC NOT NULL,
  unrealized_pnl   NUMERIC,
  leverage         INTEGER NOT NULL,
  strategy_id      TEXT NOT NULL,
  opened_at        TIMESTAMPTZ NOT NULL,
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  UNIQUE(symbol, side, strategy_id)
);

CREATE INDEX idx_positions_symbol ON trading.positions (symbol);
CREATE INDEX idx_positions_strategy ON trading.positions (strategy_id);

-- ============================================
-- 5. reporting.strategy_performance (전략 성과)
-- ============================================
CREATE TABLE IF NOT EXISTS reporting.strategy_performance(
  as_of            TIMESTAMPTZ NOT NULL,
  strategy_id      TEXT NOT NULL,
  symbol           TEXT NOT NULL,
  winrate_30d      NUMERIC,
  rr_mean_30d      NUMERIC,
  sharpe_30d       NUMERIC,
  n_trades_30d     INTEGER,
  total_pnl_30d    NUMERIC,
  avg_pnl_30d      NUMERIC,
  latency_ms_p50   INTEGER,
  
  PRIMARY KEY(as_of, strategy_id, symbol)
);

CREATE INDEX idx_perf_latest ON reporting.strategy_performance (strategy_id, symbol, as_of DESC);

-- ============================================
-- 6. reporting.daily_pnl (일별 손익)
-- ============================================
CREATE TABLE IF NOT EXISTS reporting.daily_pnl(
  date             DATE NOT NULL,
  strategy_id      TEXT NOT NULL,
  symbol           TEXT,
  pnl              NUMERIC NOT NULL,
  fees             NUMERIC NOT NULL,
  n_trades         INTEGER NOT NULL,
  win_trades       INTEGER NOT NULL,
  loss_trades      INTEGER NOT NULL,
  
  PRIMARY KEY(date, strategy_id, COALESCE(symbol, ''))
);

CREATE INDEX idx_daily_pnl_date ON reporting.daily_pnl (date DESC);
CREATE INDEX idx_daily_pnl_strategy ON reporting.daily_pnl (strategy_id, date DESC);

-- ============================================
-- 7. trading.executions (집행 기록 - 멱등성)
-- ============================================
CREATE TABLE IF NOT EXISTS trading.executions(
  execution_id     TEXT PRIMARY KEY,
  decision_id      TEXT,
  signal_id        TEXT,
  ts_executed      TIMESTAMPTZ NOT NULL,
  trade_id         TEXT,
  status           TEXT NOT NULL CHECK (status IN ('SUCCESS', 'FAILED', 'SKIPPED')),
  error_msg        TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  -- 중복 실행 방지
  UNIQUE(decision_id, ts_executed)
);

CREATE INDEX idx_executions_decision ON trading.executions (decision_id);
CREATE INDEX idx_executions_signal ON trading.executions (signal_id);
CREATE INDEX idx_executions_ts ON trading.executions (ts_executed DESC);

-- ============================================
-- 8. monitoring.gate_results (FlowGuardian 게이트 결과)
-- ============================================
CREATE TABLE IF NOT EXISTS monitoring.gate_results(
  trial_id         TEXT PRIMARY KEY,
  timestamp        TIMESTAMPTZ NOT NULL DEFAULT now(),
  gate_status      TEXT NOT NULL CHECK (gate_status IN ('READY', 'FAIL')),
  score_total      NUMERIC NOT NULL,
  profit_factor    NUMERIC,
  winrate          NUMERIC,
  exp_score        NUMERIC,
  total_trades     INTEGER,
  metrics          JSONB NOT NULL,
  errors           JSONB,
  
  -- 인덱스
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_gate_results_ts ON monitoring.gate_results (timestamp DESC);
CREATE INDEX idx_gate_results_status ON monitoring.gate_results (gate_status, timestamp DESC);

-- 완료 메시지
DO $$
BEGIN
  RAISE NOTICE '✅ 데이터베이스 스키마 초기화 완료!';
  RAISE NOTICE '   - monitoring 스키마: signals, gate_results';
  RAISE NOTICE '   - trading 스키마: decisions, trades, positions, executions';
  RAISE NOTICE '   - reporting 스키마: strategy_performance, daily_pnl';
END $$;
