#!/usr/bin/env python3
"""최근 job의 메트릭 상세 확인"""

from database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        # 최근 3개 job의 결과
        cur.execute("""
            SELECT job_id, trade_count, pnl, sharpe_ratio, metrics_json
            FROM tuning.results
            ORDER BY created_at DESC
            LIMIT 3
        """)
        results = cur.fetchall()
        
        print("최근 3개 job의 tuning.results:")
        for r in results:
            job_id, trades, pnl, sharpe, metrics = r
            print(f"\njob_id: {job_id}")
            print(f"  trade_count: {trades}")
            print(f"  pnl: {pnl}")
            print(f"  sharpe: {sharpe}")
            print(f"  metrics_json: {metrics}")
        
        # 같은 job_id의 trading.trades 확인
        print("\n" + "="*80)
        for r in results:
            job_id = r[0]
            cur.execute("""
                SELECT COUNT(*), SUM(CASE WHEN status='CLOSED' THEN 1 ELSE 0 END)
                FROM trading.trades
                WHERE trial_id = %s
            """, (job_id,))
            trade_result = cur.fetchone()
            total, closed = trade_result
            print(f"\njob_id: {job_id}")
            print(f"  trading.trades: total={total}, closed={closed}")
