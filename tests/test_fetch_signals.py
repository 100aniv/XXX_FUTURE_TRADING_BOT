#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""신호 조회 테스트"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

os.environ['DATABASE_URL'] = 'postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db'

DB_URL = os.environ['DATABASE_URL']

def get_db_connection():
    return psycopg2.connect(DB_URL)

# 1. 최근 5분 내 신호 조회 (trading_manager.py 로직)
sql = """
SELECT 
    signal_id, strategy_id, symbol, timeframe, candle_closed_at,
    direction, confidence, entry_price, sl_price, tp_price,
    atr, leverage, created_at
FROM monitoring.signals
WHERE strategy_id = %s
  AND created_at > NOW() - INTERVAL '5 minutes'
  AND direction != 'FLAT'
ORDER BY created_at ASC
LIMIT 10
"""

print("=" * 60)
print("신호 조회 테스트")
print("=" * 60)

with get_db_connection() as conn:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, ('daytrade',))
        signals = cur.fetchall()
        
        print(f"\n최근 5분 내 daytrade 신호: {len(signals)}개")
        
        if signals:
            for s in signals:
                print(f"\n  Symbol: {s['symbol']}")
                print(f"  Direction: {s['direction']}")
                print(f"  Confidence: {s['confidence']}")
                print(f"  Entry: {s['entry_price']}")
                print(f"  SL: {s['sl_price']}")
                print(f"  TP: {s['tp_price']}")
                print(f"  Created: {s['created_at']}")
        else:
            print("\n⚠️  최근 5분 내 신호 없음!")
            
            # 전체 신호 중 최근 것 확인
            cur.execute("""
                SELECT strategy_id, symbol, direction, confidence, created_at
                FROM monitoring.signals
                WHERE strategy_id = 'daytrade'
                ORDER BY created_at DESC
                LIMIT 5
            """)
            recent = cur.fetchall()
            
            if recent:
                print("\n최근 daytrade 신호 (전체):")
                for r in recent:
                    print(f"  {r['created_at']} | {r['symbol']} | {r['direction']} | {r['confidence']}")
