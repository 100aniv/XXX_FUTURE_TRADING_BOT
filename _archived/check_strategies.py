#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""전략 사용 현황 확인"""
import psycopg2
from psycopg2.extras import RealDictCursor

print("=" * 80)
print("📊 전략 사용 현황 확인")
print("=" * 80)

conn = psycopg2.connect(
    host='localhost', port=5433, database='trading_db',
    user='trading_user', password='trading_pw_2024'
)

try:
    # 1. 거래에서 사용된 strategy_id
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                strategy_id,
                COUNT(*) as count
            FROM trading.trades
            WHERE ts_open >= NOW() - INTERVAL '1 day'
            GROUP BY strategy_id
            ORDER BY count DESC
        """)
        trades = cur.fetchall()
        
        print("\n📊 거래에 사용된 전략:")
        for t in trades:
            print(f"   {t['strategy_id']}: {t['count']}건")
    
    # 2. 신호 테이블 확인
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                strategy_id,
                COUNT(*) as count
            FROM monitoring.signals
            WHERE candle_closed_at >= NOW() - INTERVAL '1 day'
            GROUP BY strategy_id
            ORDER BY count DESC
        """)
        signals = cur.fetchall()
        
        print("\n📊 신호가 생성된 전략:")
        for s in signals:
            print(f"   {s['strategy_id']}: {s['count']}건")
    
    # 3. ensemble 결정 테이블
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT symbol) as symbols
            FROM trading.decisions
            WHERE candle_closed_at >= NOW() - INTERVAL '1 day'
        """)
        decisions = cur.fetchone()
        
        print(f"\n📊 앙상블 결정:")
        print(f"   총 {decisions['total']}건")
        print(f"   심볼 {decisions['symbols']}개")
    
    # 4. 신호 샘플 확인
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                signal_id,
                strategy_id,
                symbol,
                direction,
                confidence,
                candle_closed_at
            FROM monitoring.signals
            WHERE candle_closed_at >= NOW() - INTERVAL '1 day'
            ORDER BY candle_closed_at DESC
            LIMIT 20
        """)
        samples = cur.fetchall()
        
        print(f"\n📊 최근 신호 샘플 (20건):")
        for s in samples:
            print(f"   {s['candle_closed_at'].strftime('%H:%M')}: {s['strategy_id']:10s} {s['direction']:5s} conf={s['confidence']:.2f}")

except Exception as e:
    print(f"\n❌ 오류: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()

print("=" * 80)
