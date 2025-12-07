#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-5: Local Grid Search Round 1 Progress Checker
======================================================
DB에서 PHASE28-5 실행 상태 확인 (임시 스크립트)

Usage:
    python scripts/temp_check_phase28_5_progress.py
"""
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


def check_progress():
    """PHASE28-5 진행 상황 확인"""
    
    # 1. Run 통계
    sql_runs = """
    SELECT
        run_id,
        run_name,
        total_jobs,
        completed_jobs,
        created_at
    FROM tuning.runs
    WHERE run_id LIKE 'phase28_5_%'
    ORDER BY created_at DESC
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_runs)
            runs = cur.fetchall()
    
    if not runs:
        print("❌ No PHASE28-5 runs found")
        return
    
    print("=" * 80)
    print("📊 PHASE28-5 Local Grid Search Round 1 Progress")
    print("=" * 80)
    print(f"\nTotal Runs: {len(runs)}")
    print()
    
    for idx, run in enumerate(runs, 1):
        run_id = run[0]
        run_name = run[1]
        total_jobs = run[2]
        completed_jobs = run[3]
        created_at = run[4]
        
        progress_pct = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        
        print(f"Run {idx}: {run_id}")
        print(f"  Name: {run_name}")
        print(f"  Progress: {completed_jobs}/{total_jobs} ({progress_pct:.1f}%)")
        print(f"  Created: {created_at}")
        print()
    
    # 2. Job 통계
    sql_jobs = """
    SELECT
        status,
        COUNT(*) as count
    FROM tuning.jobs
    WHERE run_id LIKE 'phase28_5_%'
    GROUP BY status
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_jobs)
            job_stats = cur.fetchall()
    
    print("Job Status:")
    for status, count in job_stats:
        print(f"  {status}: {count}")
    print()
    
    # 3. Results 통계 (Sharpe, PnL, Trades)
    sql_results = """
    SELECT
        COUNT(*) as total,
        COUNT(CASE WHEN r.trade_count >= 5 THEN 1 END) as valid_trials,
        MIN(r.sharpe_ratio) as min_sharpe,
        MAX(r.sharpe_ratio) as max_sharpe,
        AVG(r.sharpe_ratio) as avg_sharpe,
        MIN(r.pnl) as min_pnl,
        MAX(r.pnl) as max_pnl,
        AVG(r.pnl) as avg_pnl,
        AVG(r.trade_count) as avg_trades,
        AVG(r.win_rate) as avg_win_rate
    FROM tuning.results r
    JOIN tuning.jobs j ON r.job_id = j.job_id
    WHERE j.run_id LIKE 'phase28_5_%'
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_results)
            result_stats = cur.fetchone()
    
    if result_stats and result_stats[0] > 0:
        total = result_stats[0]
        valid_trials = result_stats[1]
        min_sharpe = result_stats[2] or 0
        max_sharpe = result_stats[3] or 0
        avg_sharpe = result_stats[4] or 0
        min_pnl = result_stats[5] or 0
        max_pnl = result_stats[6] or 0
        avg_pnl = result_stats[7] or 0
        avg_trades = result_stats[8] or 0
        avg_win_rate = result_stats[9] or 0
        
        print("Results Summary:")
        print(f"  Total Trials: {total}")
        print(f"  Valid Trials (trades ≥ 5): {valid_trials}")
        print(f"  Sharpe: [{min_sharpe:.4f}, {max_sharpe:.4f}], Avg: {avg_sharpe:.4f}")
        print(f"  PnL: [{min_pnl:.2f}, {max_pnl:.2f}], Avg: {avg_pnl:.2f}")
        print(f"  Avg Trades: {avg_trades:.1f}")
        print(f"  Avg Win Rate: {avg_win_rate:.2%}")
    else:
        print("Results Summary: No completed trials yet")
    
    print()
    
    # 4. Top-5 Trials
    sql_top = """
    SELECT
        j.job_id,
        j.run_id,
        r.sharpe_ratio,
        r.pnl,
        r.trade_count,
        r.win_rate
    FROM tuning.results r
    JOIN tuning.jobs j ON r.job_id = j.job_id
    WHERE j.run_id LIKE 'phase28_5_%'
      AND r.trade_count >= 5
    ORDER BY r.sharpe_ratio DESC
    LIMIT 5
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_top)
            top_trials = cur.fetchall()
    
    if top_trials:
        print("Top-5 Trials (by Sharpe):")
        for idx, trial in enumerate(top_trials, 1):
            job_id = trial[0]
            run_id = trial[1]
            sharpe = trial[2]
            pnl = trial[3]
            trades = trial[4]
            win_rate = trial[5]
            print(f"  {idx}. job_id={job_id[:12]}... Sharpe={sharpe:.4f}, PnL={pnl:.2f}, Trades={trades}, Win%={win_rate:.2%}")
    else:
        print("Top-5 Trials: No valid trials yet")
    
    print()
    print("=" * 80)


if __name__ == '__main__':
    try:
        check_progress()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
