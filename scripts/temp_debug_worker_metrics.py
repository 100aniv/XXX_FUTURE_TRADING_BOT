#!/usr/bin/env python3
"""Worker 메트릭 추출 디버깅"""

from database import get_db_connection

# 최근 job_id 가져오기
with get_db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT job_id
            FROM tuning.results
            ORDER BY created_at DESC
            LIMIT 1
        """)
        job_id = cur.fetchone()[0]
        
        print(f"최근 job_id: {job_id}\n")
        
        # Worker가 사용하는 SQL과 동일한 쿼리
        sql_trades_detailed = """
        SELECT
            pnl,
            pnl_pct,
            ts_close as exit_time
        FROM trading.trades
        WHERE trial_id = %s
          AND status = 'CLOSED'
        ORDER BY ts_close ASC
        """
        
        cur.execute(sql_trades_detailed, (job_id,))
        trades_rows = cur.fetchall()
        
        print(f"SQL 쿼리 결과: {len(trades_rows)}건")
        print(f"SQL: WHERE trial_id = '{job_id}' AND status = 'CLOSED'\n")
        
        if trades_rows:
            print("거래 상세:")
            for i, row in enumerate(trades_rows, 1):
                print(f"  {i}. pnl={row[0]}, pnl_pct={row[1]}, exit_time={row[2]}")
        else:
            print("⚠️ 거래 없음!")
            
            # 디버깅: trial_id 없이 조회
            cur.execute("""
                SELECT COUNT(*), 
                       SUM(CASE WHEN status='CLOSED' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN trial_id IS NULL THEN 1 ELSE 0 END)
                FROM trading.trades
                WHERE created_at > NOW() - INTERVAL '10 minutes'
            """)
            result = cur.fetchone()
            print(f"\n최근 10분 내 거래:")
            print(f"  - 총: {result[0]}")
            print(f"  - CLOSED: {result[1]}")
            print(f"  - trial_id NULL: {result[2]}")
