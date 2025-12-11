#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PHASE29-6: 최신 백테스트 trade trial_id 확인"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from common.database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        # 최신 10개 backtest trade
        cur.execute("""
            SELECT trade_id, trial_id, strategy_id, pnl, ts_close
            FROM trading.trades
            WHERE mode='backtest' AND status='CLOSED'
            ORDER BY ts_close DESC
            LIMIT 10
        """)
        
        print("최신 10개 backtest trade:")
        for row in cur.fetchall():
            tid = row[1] if row[1] else 'NULL'
            print(f"  {row[0][:12]}... trial_id={tid[:30]:30} pnl={row[3]:8.2f}")
        
        # 최근 5분 내 backtest trade
        cur.execute("""
            SELECT COUNT(*), COUNT(trial_id), STRING_AGG(DISTINCT trial_id, ', ')
            FROM trading.trades
            WHERE mode='backtest' AND ts_close > NOW() - INTERVAL '10 minutes'
        """)
        row = cur.fetchone()
        print(f"\n최근 10분 backtest: {row[0]}건, trial_id 있음: {row[1]}건")
        print(f"trial_id 목록: {row[2] if row[2] else 'None'}")
