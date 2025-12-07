#!/usr/bin/env python3
"""RUNNING 상태로 남은 jobs를 FAILED로 업데이트 (프로세스 중단 시)"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        # RUNNING 상태의 jobs를 FAILED로 변경
        cur.execute("""
            UPDATE tuning.jobs
            SET status = 'FAILED',
                error_message = 'Process terminated unexpectedly',
                completed_at = NOW()
            WHERE run_id LIKE 'phase28_5%' AND status = 'RUNNING'
        """)
        jobs_updated = cur.rowcount
        
        conn.commit()
        
        print(f"Updated {jobs_updated} RUNNING jobs to FAILED")
