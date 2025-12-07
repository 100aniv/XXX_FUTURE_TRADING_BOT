#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
최근 거래 데이터 확인
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection

def check_recent_trades():
    """최근 거래 데이터 확인"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 최근 거래 조회
            cur.execute("""
                SELECT trial_id, COUNT(*) as trade_count, 
                       MIN(ts_open) as first_trade, MAX(ts_close) as last_trade
                FROM trading.trades
                WHERE ts_open >= '2024-10-01'
                GROUP BY trial_id
                ORDER BY MAX(ts_close) DESC
                LIMIT 10
            """)
            trades = cur.fetchall()
            
            print("=" * 100)
            print("📊 최근 거래 데이터 (2024-10-01 이후):")
            print("=" * 100)
            for t in trades:
                print(f"Trial ID: {t[0]}")
                print(f"  Trade Count: {t[1]}")
                print(f"  First Trade: {t[2]}")
                print(f"  Last Trade: {t[3]}")
                print("-" * 100)
            print("=" * 100)

if __name__ == "__main__":
    check_recent_trades()
