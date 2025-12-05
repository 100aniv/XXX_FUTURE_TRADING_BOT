#!/usr/bin/env python3
"""최근 백테스트 거래 확인"""

from database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        # 최근 1시간 내 백테스트 거래
        cur.execute("""
            SELECT COUNT(*), 
                   SUM(CASE WHEN status='CLOSED' THEN 1 ELSE 0 END),
                   COUNT(DISTINCT trial_id)
            FROM trading.trades
            WHERE mode='backtest' 
              AND created_at > NOW() - INTERVAL '1 hour'
        """)
        result = cur.fetchone()
        
        print(f"최근 1시간 내 백테스트 거래:")
        print(f"  - 총 거래: {result[0]}")
        print(f"  - 완료: {result[1]}")
        print(f"  - Trial 수: {result[2]}")
        
        # 최근 trial_id 몇 개 확인
        cur.execute("""
            SELECT DISTINCT trial_id
            FROM trading.trades
            WHERE mode='backtest'
              AND created_at > NOW() - INTERVAL '1 hour'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        trial_ids = cur.fetchall()
        
        print(f"\n최근 trial_id:")
        for tid in trial_ids:
            print(f"  - {tid[0]}")
