#!/usr/bin/env python3
"""Trial ID 연결 확인"""

from database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        # 최근 tuning.results
        cur.execute("""
            SELECT job_id, run_id, trade_count, pnl, sharpe_ratio
            FROM tuning.results
            ORDER BY created_at DESC
            LIMIT 5
        """)
        results = cur.fetchall()
        
        print("최근 tuning.results:")
        for r in results:
            job_id, run_id, trades, pnl, sharpe = r
            print(f"  job_id={job_id[:20]}... trades={trades} pnl={pnl} sharpe={sharpe}")
        
        # 최근 trading.trades (trial_id 확인)
        cur.execute("""
            SELECT trial_id, COUNT(*), SUM(CASE WHEN status='CLOSED' THEN 1 ELSE 0 END)
            FROM trading.trades
            WHERE mode='backtest'
              AND created_at > NOW() - INTERVAL '30 minutes'
            GROUP BY trial_id
            ORDER BY MAX(created_at) DESC
            LIMIT 5
        """)
        trades = cur.fetchall()
        
        print("\n최근 trading.trades (trial_id별):")
        for t in trades:
            trial_id, total, closed = t
            print(f"  trial_id={trial_id[:20] if trial_id else 'NULL'}... total={total} closed={closed}")
