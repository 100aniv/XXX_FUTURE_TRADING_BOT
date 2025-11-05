#!/usr/bin/env python3
"""
signals 테이블만 간단히 생성
"""
from dotenv import load_dotenv
load_dotenv()

print("🗄️  signals 테이블 생성...")

from common.database import get_db_connection

sql = """
-- signals 테이블 생성 (간단 버전)
CREATE TABLE IF NOT EXISTS signals(
  signal_id        TEXT PRIMARY KEY,
  strategy_id      TEXT NOT NULL,
  bot_id           TEXT NOT NULL,
  symbol           TEXT NOT NULL,
  timeframe        TEXT NOT NULL,
  candle_closed_at TIMESTAMPTZ NOT NULL,
  direction        TEXT NOT NULL,
  confidence       NUMERIC,
  entry_price      NUMERIC,
  sl_price         NUMERIC,
  tp_price         NUMERIC,
  atr              NUMERIC,
  leverage         INTEGER,
  features         JSONB,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(strategy_id, symbol, timeframe, candle_closed_at)
);

CREATE INDEX IF NOT EXISTS idx_signals_created ON signals (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals (symbol, created_at DESC);
"""

try:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        cursor.close()
    print("✅ signals 테이블 생성 완료!")
except Exception as e:
    print(f"❌ 실패: {e}")
