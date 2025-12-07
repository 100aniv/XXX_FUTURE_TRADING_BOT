#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        # 완료된 results 수
        cur.execute("SELECT COUNT(*) FROM tuning.results WHERE run_id LIKE 'phase28_3_%'")
        results_count = cur.fetchone()[0]
        print(f"완료된 results: {results_count}")
        
        # Run별 jobs
        cur.execute("""
            SELECT run_id, 
                   COUNT(*) as total,
                   SUM(CASE WHEN status='COMPLETED' THEN 1 ELSE 0 END) as completed,
                   SUM(CASE WHEN status='PENDING' THEN 1 ELSE 0 END) as pending
            FROM tuning.jobs 
            WHERE run_id LIKE 'phase28_3_%' 
            GROUP BY run_id 
            ORDER BY run_id
        """)
        print("\nRun별 jobs 상태:")
        for row in cur.fetchall():
            print(f"  {row[0]}: {row[2]}/{row[1]} completed, {row[3]} pending")
