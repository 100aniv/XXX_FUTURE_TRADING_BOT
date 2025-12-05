#!/usr/bin/env python3
"""PHASE28-2: Tuning 진행 상황 확인 스크립트"""

from database import get_db_connection

def check_tuning_status():
    """Tuning jobs 상태 확인"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Runs 확인
            cur.execute("""
                SELECT run_id, tuning_method, status
                FROM tuning.runs
                WHERE run_id LIKE '%btc5m_baseline_tuning_round1%'
                ORDER BY created_at DESC
            """)
            runs = cur.fetchall()
            
            print("=" * 80)
            print("TUNING RUNS STATUS")
            print("=" * 80)
            for run in runs:
                run_id, method, status = run
                print(f"\nRun: {run_id[:50]}...")
                print(f"  Method: {method}")
                print(f"  Status: {status}")
            
            # Jobs 상태별 집계
            cur.execute("""
                SELECT run_id, status, COUNT(*)
                FROM tuning.jobs
                WHERE run_id LIKE '%btc5m_baseline_tuning_round1%'
                GROUP BY run_id, status
                ORDER BY run_id, status
            """)
            jobs = cur.fetchall()
            
            print("\n" + "=" * 80)
            print("JOBS STATUS BY RUN")
            print("=" * 80)
            for job in jobs:
                run_id, status, count = job
                print(f"{run_id[:50]}... | {status}: {count}")
            
            # Results 확인
            cur.execute("""
                SELECT COUNT(*), AVG(pnl), AVG(sharpe_ratio), AVG(trade_count)
                FROM tuning.results
                WHERE run_id LIKE '%btc5m_baseline_tuning_round1%'
            """)
            result = cur.fetchone()
            
            print("\n" + "=" * 80)
            print("RESULTS SUMMARY")
            print("=" * 80)
            if result and result[0] > 0:
                count, avg_pnl, avg_sharpe, avg_trades = result
                print(f"Total Results: {count}")
                print(f"Avg PnL: {avg_pnl:.2f}")
                print(f"Avg Sharpe: {avg_sharpe:.4f}")
                print(f"Avg Trades: {avg_trades:.1f}")
            else:
                print("No results yet")

if __name__ == "__main__":
    check_tuning_status()
