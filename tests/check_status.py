#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
현재 시스템 상태 체크
"""
import psycopg2
from datetime import datetime, timedelta

DB_URL = "postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db"

def check_db():
    """DB 상태 확인"""
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        print("=" * 60)
        print("📊 DATABASE STATUS CHECK")
        print("=" * 60)
        
        # 1. 최근 24시간 신호 수
        cur.execute("""
            SELECT strategy_id, COUNT(*) as count
            FROM monitoring.signals
            WHERE created_at > NOW() - INTERVAL '24 hours'
            GROUP BY strategy_id
            ORDER BY count DESC
        """)
        signals = cur.fetchall()
        
        print("\n🔔 최근 24시간 신호 (monitoring.signals):")
        total_signals = 0
        for strategy, count in signals:
            print(f"  • {strategy}: {count}개")
            total_signals += count
        print(f"  ✅ 총 신호: {total_signals}개")
        
        # 2. 앙상블 결정 수
        cur.execute("""
            SELECT COUNT(*) as count
            FROM trading.decisions
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """)
        decisions = cur.fetchone()[0]
        print(f"\n🎯 최근 24시간 앙상블 결정 (trading.decisions): {decisions}개")
        
        # 3. 실제 거래 수
        cur.execute("""
            SELECT COUNT(*) as count
            FROM trading.trades
        """)
        trades = cur.fetchone()[0]
        print(f"\n💰 총 거래 수 (trading.trades): {trades}개")
        
        # 4. 최근 신호 5개
        cur.execute("""
            SELECT strategy_id, symbol, direction, confidence, created_at
            FROM monitoring.signals
            ORDER BY created_at DESC
            LIMIT 5
        """)
        recent = cur.fetchall()
        
        print("\n📝 최근 신호 5개:")
        for row in recent:
            strat, sym, dir, conf, created = row
            print(f"  • {created.strftime('%m-%d %H:%M')} | {strat:10s} | {sym:8s} | {dir:5s} | {conf:.2f}")
        
        # 5. 최근 앙상블 결정 5개
        cur.execute("""
            SELECT symbol, action, confidence, created_at
            FROM trading.decisions
            ORDER BY created_at DESC
            LIMIT 5
        """)
        recent_decisions = cur.fetchall()
        
        print("\n🎯 최근 앙상블 결정 5개:")
        if recent_decisions:
            for row in recent_decisions:
                sym, act, conf, created = row
                print(f"  • {created.strftime('%m-%d %H:%M')} | {sym:8s} | {act:5s} | {conf:.2f}")
        else:
            print("  (없음)")
        
        print("\n" + "=" * 60)
        
        cur.close()
        conn.close()
        
        return {
            'signals': total_signals,
            'decisions': decisions,
            'trades': trades
        }
        
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}")
        return None

if __name__ == "__main__":
    check_db()
