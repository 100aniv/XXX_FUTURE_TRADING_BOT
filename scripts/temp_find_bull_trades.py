#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bull 백테스트 거래 찾기
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection

def find_bull_trades():
    """Bull 백테스트 거래 찾기"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1. 최근 생성된 거래 확인
            cur.execute("""
                SELECT trial_id, trade_id, ts_open, ts_close, side, pnl, created_at
                FROM trading.trades
                WHERE created_at >= '2025-12-08 00:40:00'
                ORDER BY created_at DESC
                LIMIT 20
            """)
            
            trades = cur.fetchall()
            
            print("=" * 100)
            print("📊 Bull 백테스트 기간 (2025-12-08 00:40:00 이후) 생성된 거래:")
            print("=" * 100)
            
            if not trades:
                print("❌ 거래 데이터 없음")
            else:
                for t in trades:
                    print(f"Trial ID: {t[0]}")
                    print(f"  Trade ID: {t[1]}")
                    print(f"  Open: {t[2]}")
                    print(f"  Close: {t[3]}")
                    print(f"  Side: {t[4]}")
                    print(f"  PnL: {t[5]}")
                    print(f"  Created: {t[6]}")
                    print("-" * 100)
            
            print("=" * 100)
            
            # 2. run_id로 검색
            run_id = "20251208_004038_5pqx"
            cur.execute("""
                SELECT COUNT(*)
                FROM trading.trades
                WHERE trial_id = %s
            """, (run_id,))
            count = cur.fetchone()[0]
            print(f"\nrun_id '{run_id}'로 조회: {count}건")

if __name__ == "__main__":
    find_bull_trades()
