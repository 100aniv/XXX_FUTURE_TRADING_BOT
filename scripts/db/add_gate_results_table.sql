-- monitoring.gate_results 테이블 추가
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
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_gate_results_ts ON monitoring.gate_results (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_gate_results_status ON monitoring.gate_results (gate_status, timestamp DESC);
