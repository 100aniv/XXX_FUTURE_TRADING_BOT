#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""상세 백테스트 분석"""
import psycopg2
from psycopg2.extras import RealDictCursor

print("=" * 80)
print("📊 상세 백테스트 분석")
print("=" * 80)

conn = psycopg2.connect(
    host='localhost', port=5433, database='trading_db',
    user='trading_user', password='trading_pw_2024'
)

try:
    # 1. 거래 빈도
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                DATE(ts_open) as date,
                COUNT(*) as trades,
                ROUND(SUM(pnl)::numeric, 2) as daily_pnl
            FROM trading.trades
            WHERE ts_open >= NOW() - INTERVAL '30 days'
              AND status = 'CLOSED'
            GROUP BY DATE(ts_open)
            ORDER BY date DESC
            LIMIT 20
        """)
        daily = cur.fetchall()
        
        print("\n📅 일별 거래 빈도:")
        for d in daily[:10]:
            print(f"   {d['date']}: {d['trades']}건, PnL ${d['daily_pnl']}")
    
    # 2. TP vs SL 비율
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                exit_reason,
                COUNT(*) as count,
                ROUND(AVG(pnl)::numeric, 2) as avg_pnl
            FROM trading.trades
            WHERE ts_open >= NOW() - INTERVAL '1 day'
              AND status = 'CLOSED'
            GROUP BY exit_reason
            ORDER BY count DESC
        """)
        exits = cur.fetchall()
        
        print("\n🚪 청산 이유:")
        for e in exits:
            print(f"   {e['exit_reason']}: {e['count']}건, 평균 PnL ${e['avg_pnl']}")
    
    # 3. 포지션 홀딩 시간
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                ROUND(AVG(EXTRACT(EPOCH FROM (ts_close - ts_open)) / 60)::numeric, 1) as avg_minutes,
                ROUND(MIN(EXTRACT(EPOCH FROM (ts_close - ts_open)) / 60)::numeric, 1) as min_minutes,
                ROUND(MAX(EXTRACT(EPOCH FROM (ts_close - ts_open)) / 60)::numeric, 1) as max_minutes
            FROM trading.trades
            WHERE ts_open >= NOW() - INTERVAL '1 day'
              AND status = 'CLOSED'
              AND ts_close IS NOT NULL
        """)
        duration = cur.fetchone()
        
        if duration:
            print(f"\n⏱️ 포지션 홀딩 시간:")
            print(f"   평균: {duration['avg_minutes']}분")
            print(f"   최소: {duration['min_minutes']}분")
            print(f"   최대: {duration['max_minutes']}분")
    
    # 4. 연속 손실
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT pnl, ts_open
            FROM trading.trades
            WHERE ts_open >= NOW() - INTERVAL '1 day'
              AND status = 'CLOSED'
            ORDER BY ts_open DESC
            LIMIT 50
        """)
        trades = cur.fetchall()
        
        max_streak = 0
        current_streak = 0
        for t in trades:
            if t['pnl'] < 0:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        print(f"\n📉 최대 연속 손실: {max_streak}건")
    
    # 5. 승/패 PnL 분포
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                ROUND(AVG(CASE WHEN pnl > 0 THEN pnl ELSE 0 END)::numeric, 2) as avg_win,
                ROUND(AVG(CASE WHEN pnl < 0 THEN pnl ELSE 0 END)::numeric, 2) as avg_loss,
                ROUND(AVG(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) / 
                      NULLIF(-AVG(CASE WHEN pnl < 0 THEN pnl ELSE 0 END), 0), 2) as win_loss_ratio
            FROM trading.trades
            WHERE ts_open >= NOW() - INTERVAL '1 day'
              AND status = 'CLOSED'
        """)
        ratio = cur.fetchone()
        
        if ratio:
            print(f"\n💰 승/패 비율:")
            print(f"   평균 수익: ${ratio['avg_win']}")
            print(f"   평균 손실: ${ratio['avg_loss']}")
            print(f"   Win/Loss Ratio: {ratio['win_loss_ratio']}")

except Exception as e:
    print(f"\n❌ 오류: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()

print("=" * 80)
