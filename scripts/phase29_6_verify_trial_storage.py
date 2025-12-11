#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PHASE29-6: trial_id 저장 검증"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from common.database import get_db_connection

TARGET_TRIAL_ID = 'phase29_4_0_btc5m_baseline_v4_month_gate'

with get_db_connection() as conn:
    with conn.cursor() as cur:
        # 해당 trial_id trade 수
        cur.execute("""
            SELECT COUNT(*), COUNT(DISTINCT symbol), MIN(ts_close), MAX(ts_close)
            FROM trading.trades
            WHERE trial_id = %s AND status = 'CLOSED'
        """, (TARGET_TRIAL_ID,))
        
        row = cur.fetchone()
        print(f"✅ trial_id='{TARGET_TRIAL_ID}'")
        print(f"   Trades: {row[0]}")
        print(f"   Symbols: {row[1]}")
        print(f"   Period: {row[2]} ~ {row[3]}")
        
        # Win/Loss 분포
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE pnl > 0) as wins,
                COUNT(*) FILTER (WHERE pnl <= 0) as losses,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl
            FROM trading.trades
            WHERE trial_id = %s AND status = 'CLOSED'
        """, (TARGET_TRIAL_ID,))
        
        row = cur.fetchone()
        print(f"\n   Wins: {row[0]}")
        print(f"   Losses: {row[1]}")
        print(f"   Total PnL: {row[2]:.2f} USDT")
        print(f"   Avg PnL: {row[3]:.2f} USDT")
        print(f"   Win Rate: {row[0]/(row[0]+row[1])*100:.2f}%")
