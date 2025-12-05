#!/usr/bin/env python3
"""Worker 에러 로그 테이블 생성"""

from database import get_db_connection

sql = """
CREATE TABLE IF NOT EXISTS tuning.worker_errors (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(50),
    error_message TEXT,
    error_trace TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
"""

with get_db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(sql)

print("✅ tuning.worker_errors 테이블 생성 완료")
