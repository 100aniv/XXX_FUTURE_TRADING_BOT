#!/usr/bin/env python3
"""PHASE28-4 DB 정리"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM tuning.results WHERE run_id LIKE 'phase28_4%'")
        results_deleted = cur.rowcount
        
        cur.execute("DELETE FROM tuning.jobs WHERE run_id LIKE 'phase28_4%'")
        jobs_deleted = cur.rowcount
        
        cur.execute("DELETE FROM tuning.runs WHERE run_id LIKE 'phase28_4%'")
        runs_deleted = cur.rowcount
        
        conn.commit()
        
        print(f"DB cleaned:")
        print(f"  - Results deleted: {results_deleted}")
        print(f"  - Jobs deleted: {jobs_deleted}")
        print(f"  - Runs deleted: {runs_deleted}")
