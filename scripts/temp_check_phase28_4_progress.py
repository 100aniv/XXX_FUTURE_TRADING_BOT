#!/usr/bin/env python3
"""PHASE28-4 진행 상황 확인"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        # Run 상태
        cur.execute("""
            SELECT run_id, phase, total_jobs, completed_jobs, status
            FROM tuning.runs
            WHERE run_id LIKE 'phase28_4%'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        runs = cur.fetchall()
        
        print("\n" + "="*80)
        print("PHASE28-4 Run Status")
        print("="*80)
        for r in runs:
            print(f"  {r[0]}: {r[3]}/{r[2]} jobs, status={r[4]}")
        
        # Results 개수
        cur.execute("""
            SELECT run_id, COUNT(*) as result_count
            FROM tuning.results
            WHERE run_id LIKE 'phase28_4%'
            GROUP BY run_id
            ORDER BY run_id
        """)
        results = cur.fetchall()
        
        print("\nResults Count:")
        for r in results:
            print(f"  {r[0]}: {r[1]} results")
        
        # 최근 job 상태
        cur.execute("""
            SELECT job_id, run_id, status
            FROM tuning.jobs
            WHERE run_id LIKE 'phase28_4%'
            ORDER BY created_at DESC
            LIMIT 10
        """)
        jobs = cur.fetchall()
        
        print("\nRecent Jobs:")
        for j in jobs:
            print(f"  {j[0]} ({j[1]}): {j[2]}")
        
        # Worker errors
        cur.execute("""
            SELECT job_id, error_trace, created_at
            FROM tuning.worker_errors
            WHERE job_id IN (
                SELECT job_id FROM tuning.jobs
                WHERE run_id LIKE 'phase28_4%'
            )
            ORDER BY created_at DESC
            LIMIT 5
        """)
        errors = cur.fetchall()
        
        if errors:
            print("\nRecent Errors:")
            for e in errors:
                print(f"  Job: {e[0]}")
                print(f"    {e[1][:300]}")
        
        print("="*80 + "\n")
