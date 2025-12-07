#!/usr/bin/env python3
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT job_id, run_id, error_message, params_json
            FROM tuning.jobs
            WHERE run_id LIKE 'phase28_5%' AND status = 'FAILED'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        failed_jobs = cur.fetchall()
        
        if not failed_jobs:
            print("No failed jobs found")
        else:
            for job in failed_jobs:
                print("=" * 80)
                print(f"Job ID: {job[0]}")
                print(f"Run ID: {job[1]}")
                print(f"Error: {job[2][:500] if job[2] else 'No error message'}")
                print(f"Params: {job[3]}")
                print()
