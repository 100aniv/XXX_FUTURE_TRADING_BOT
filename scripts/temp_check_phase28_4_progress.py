#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-4: Bayesian Search Round 1 진행 상황 실시간 체크
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection

def main():
    print("=" * 100)
    print("PHASE28-4 Bayesian Search Round 1 Progress")
    print("=" * 100)
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 최근 PHASE28-4 trials 조회
            cur.execute("""
                SELECT 
                    run_id,
                    job_id,
                    sharpe_ratio,
                    trade_count,
                    pnl,
                    win_rate,
                    max_drawdown,
                    created_at
                FROM tuning.results
                WHERE run_id LIKE 'phase28_4_%'
                ORDER BY created_at DESC
                LIMIT 50
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("\nNo PHASE28-4 trials completed yet. Trials in progress...\n")
                print("=" * 100)
                return
            
            print(f"\nCompleted Trials: {len(rows)}\n")
            print(f"{'#':<4} {'Run ID':<35} | {'Job ID':<18} | {'Sharpe':>9} | {'Trades':>7} | {'PnL':>10} | {'Win%':>6} | {'MDD%':>7} | {'Time'}")
            print("-" * 140)
            
            for idx, r in enumerate(rows, 1):
                run_id = r[0][:33] + ".." if len(r[0]) > 33 else r[0]
                job_id = r[1][:16] + ".." if len(r[1]) > 16 else r[1]
                sharpe = f"{r[2]:.4f}" if r[2] is not None else "N/A"
                trades = r[3] if r[3] is not None else 0
                pnl = f"${float(r[4]):.2f}" if r[4] is not None else "N/A"
                win_rate = f"{float(r[5])*100:.1f}%" if r[5] is not None else "N/A"
                mdd = f"{float(r[6])*100:.1f}%" if r[6] is not None else "N/A"
                created = r[7].strftime("%H:%M:%S") if r[7] else "N/A"
                
                print(f"{idx:<4} {run_id:<35} | {job_id:<18} | {sharpe:>9} | {trades:>7} | {pnl:>10} | {win_rate:>6} | {mdd:>7} | {created}")
            
            # 통계
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    AVG(sharpe_ratio) as avg_sharpe,
                    MAX(sharpe_ratio) as best_sharpe,
                    MIN(sharpe_ratio) as worst_sharpe,
                    SUM(trade_count) as total_trades,
                    COUNT(DISTINCT run_id) as unique_runs
                FROM tuning.results
                WHERE run_id LIKE 'phase28_4_%'
            """)
            
            stats = cur.fetchone()
            print("\n" + "=" * 100)
            print("Summary Statistics:")
            print(f"  Total Trials Completed: {stats[0]}")
            print(f"  Unique Run IDs: {stats[5]}")
            avg_sharpe = float(stats[1]) if stats[1] is not None else 0.0
            best_sharpe = float(stats[2]) if stats[2] is not None else 0.0
            worst_sharpe = float(stats[3]) if stats[3] is not None else 0.0
            total_trades = int(stats[4]) if stats[4] is not None else 0
            print(f"  Avg Sharpe Ratio: {avg_sharpe:.4f}")
            print(f"  Best Sharpe: {best_sharpe:.4f}")
            print(f"  Worst Sharpe: {worst_sharpe:.4f}")
            print(f"  Total Trades Across All Trials: {total_trades}")
            print("=" * 100)

if __name__ == '__main__':
    main()
