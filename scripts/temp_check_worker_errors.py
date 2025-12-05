#!/usr/bin/env python3
"""Worker 에러 로그 확인"""

from database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT job_id, error_message, error_trace, created_at
            FROM tuning.worker_errors
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        rows = cur.fetchall()
        
        if not rows:
            print("⚠️ 에러 로그 없음")
        else:
            for row in rows:
                print(f"\n{'='*60}")
                print(f"job_id: {row[0]}")
                print(f"created_at: {row[3]}")
                print(f"\nerror_message:")
                print(row[1])
                print(f"\nerror_trace:")
                print(row[2])
