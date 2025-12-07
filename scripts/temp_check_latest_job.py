#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        # Check old PHASE28-4 jobs
        cur.execute("""
            SELECT job_id, run_id, params_json, status, created_at
            FROM tuning.jobs
            WHERE run_id LIKE 'phase28_4_bull_66931bd9%'
               OR run_id LIKE 'phase28_4_bull_e65ea051%'
               OR run_id LIKE 'phase28_4_bull_65923e42%'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        rows = cur.fetchall()
        
        if not rows:
            print("No recent jobs found")
        else:
            for r in rows:
                print(f"\nJob ID: {r[0]}")
                print(f"Run ID: {r[1]}")
                print(f"Params: {r[2]}")
                print(f"Status: {r[3]}")
                print(f"Created: {r[4]}")
