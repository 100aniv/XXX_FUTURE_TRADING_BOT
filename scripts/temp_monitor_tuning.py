#!/usr/bin/env python3
"""
PHASE28-2: Tuning 진행 상황 모니터링
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import get_db_connection
from datetime import datetime

def main():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 최근 튜닝 결과 확인
            print("\n=== tuning.results (최근 10개) ===")
            cur.execute("""
                SELECT 
                    job_id,
                    run_id,
                    trade_count,
                    pnl,
                    win_rate,
                    sharpe_ratio,
                    created_at
                FROM tuning.results
                ORDER BY created_at DESC
                LIMIT 10
            """)
            results = cur.fetchall()
            if results:
                print(f"{'job_id':<40} {'run_id':<20} {'trades':<8} {'pnl':<10} {'win_rate':<10} {'sharpe':<10} {'created_at'}")
                print("-" * 140)
                for row in results:
                    pnl_val = float(row[3]) if row[3] is not None else 0.0
                    win_rate_val = float(row[4]) if row[4] is not None else 0.0
                    sharpe_val = float(row[5]) if row[5] is not None else 0.0
                    print(f"{row[0]:<40} {row[1]:<20} {row[2]:<8} {pnl_val:<10.2f} {win_rate_val:<10.4f} {sharpe_val:<10.4f} {row[6]}")
            else:
                print("결과 없음")
            
            # 거래 확인
            print("\n=== trading.trades (최근 trial_id별 집계) ===")
            cur.execute("""
                SELECT 
                    trial_id,
                    COUNT(*) as trade_count,
                    SUM(pnl) as total_pnl,
                    MIN(ts_close) as first_trade,
                    MAX(ts_close) as last_trade
                FROM trading.trades
                WHERE trial_id IS NOT NULL
                  AND status = 'CLOSED'
                GROUP BY trial_id
                ORDER BY MAX(ts_close) DESC
                LIMIT 10
            """)
            trades = cur.fetchall()
            if trades:
                print(f"{'trial_id':<40} {'count':<8} {'total_pnl':<12} {'first_trade':<20} {'last_trade'}")
                print("-" * 140)
                for row in trades:
                    print(f"{row[0]:<40} {row[1]:<8} {row[2]:<12.2f} {str(row[3]):<20} {row[4]}")
            else:
                print("거래 없음")
            
            # Worker 에러 확인
            print("\n=== tuning.worker_errors (최근 5개) ===")
            try:
                cur.execute("""
                    SELECT 
                        job_id,
                        error_message,
                        created_at
                    FROM tuning.worker_errors
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                errors = cur.fetchall()
                if errors:
                    for row in errors:
                        print(f"[{row[2]}] job_id={row[0]}")
                        print(f"  Error: {row[1]}")
                        print()
                else:
                    print("에러 없음 ✅")
            except:
                print("worker_errors 테이블 없음 또는 조회 실패")

if __name__ == "__main__":
    main()
