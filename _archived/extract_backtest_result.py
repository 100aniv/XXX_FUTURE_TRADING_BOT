#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""백테스트 결과 추출"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("📊 백테스트 결과 추출")
print("=" * 80)

# DB 연결
conn = psycopg2.connect(
    host='localhost',
    port=5433,
    database='trading_db',
    user='trading_user',
    password='trading_pw_2024'
)

try:
    # 최근 거래 통계
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
                ROUND(AVG(CASE WHEN pnl > 0 THEN 1.0 ELSE 0.0 END) * 100, 2) as win_rate,
                ROUND(SUM(pnl)::numeric, 2) as total_pnl,
                ROUND(AVG(pnl)::numeric, 2) as avg_pnl,
                ROUND(MAX(pnl)::numeric, 2) as max_win,
                ROUND(MIN(pnl)::numeric, 2) as max_loss
            FROM trading.trades
            WHERE ts_open >= NOW() - INTERVAL '1 day'
              AND status = 'CLOSED'
        """)
        stats = cur.fetchone()
        
        if stats and stats['total_trades']:
            print(f"\n✅ 총 거래: {stats['total_trades']}건")
            print(f"   승: {stats['wins']}건 / 패: {stats['losses']}건")
            print(f"   승률: {stats['win_rate']}%")
            print(f"   총 PnL: ${stats['total_pnl']}")
            print(f"   평균 PnL: ${stats['avg_pnl']}")
            print(f"   최대 수익: ${stats['max_win']}")
            print(f"   최대 손실: ${stats['max_loss']}")
        else:
            print("\n❌ 거래 데이터 없음")
    
    # 전략별 통계
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                strategy_id,
                COUNT(*) as trades,
                ROUND(AVG(CASE WHEN pnl > 0 THEN 1.0 ELSE 0.0 END) * 100, 2) as win_rate,
                ROUND(SUM(pnl)::numeric, 2) as total_pnl
            FROM trading.trades
            WHERE ts_open >= NOW() - INTERVAL '1 day'
              AND status = 'CLOSED'
            GROUP BY strategy_id
            ORDER BY total_pnl DESC
        """)
        strategies = cur.fetchall()
        
        if strategies:
            print("\n📊 전략별 성과:")
            for s in strategies:
                print(f"   {s['strategy_id']}: {s['trades']}건, 승률 {s['win_rate']}%, PnL ${s['total_pnl']}")
        
except Exception as e:
    print(f"\n❌ 오류: {e}")
finally:
    conn.close()

print("=" * 80)
