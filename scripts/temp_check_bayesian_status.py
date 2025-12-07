#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""임시: Bayesian Round 1 상태 확인"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        # 최근 Bayesian Round 1 run 조회
        cur.execute("""
            SELECT run_id, COUNT(*) as trial_count, MAX(created_at) as last_trial
            FROM tuning.results
            WHERE run_id LIKE 'btc5m_bayesian_round1_%'
            GROUP BY run_id
            ORDER BY MAX(created_at) DESC
            LIMIT 5
        """)
        
        rows = cur.fetchall()
        print("=" * 80)
        print("Recent Bayesian Round 1 runs:")
        print("=" * 80)
        for r in rows:
            print(f"  run_id={r[0]}")
            print(f"    trials={r[1]}")
            print(f"    last_trial={r[2]}")
            print()
        
        # 가장 최근 run의 상세 정보
        if rows:
            latest_run_id = rows[0][0]
            print("=" * 80)
            print(f"Latest run details: {latest_run_id}")
            print("=" * 80)
            
            cur.execute("""
                SELECT 
                    job_id,
                    total_trades,
                    sharpe_like_ratio,
                    pnl,
                    max_drawdown,
                    created_at
                FROM tuning.results
                WHERE run_id = %s
                ORDER BY created_at DESC
                LIMIT 10
            """, (latest_run_id,))
            
            trials = cur.fetchall()
            for i, t in enumerate(trials, 1):
                sharpe_val = f"{t[2]:.4f}" if t[2] is not None else "0.0000"
                pnl_val = f"{t[3]:.2f}" if t[3] is not None else "0.00"
                print(f"  Trial {i}: job_id={t[0]}, trades={t[1]}, sharpe={sharpe_val}, pnl={pnl_val}")
