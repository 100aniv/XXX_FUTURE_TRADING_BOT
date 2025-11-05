#!/usr/bin/env python3
"""전체 시스템 테스트"""
import os
os.environ['DATABASE_URL'] = 'postgresql://trading_user:trading_pw_2024@postgres:5432/trading_db'
os.environ['STRATEGY_SELECTOR'] = 'trend'
os.environ['TRADING_MODE'] = 'backtest'

import psycopg2
from trading_bot import TradingBot

print("="*60)
print("📊 전체 시스템 테스트")
print("="*60)

# 1. DB 연결 확인
print("\n1️⃣ DB 연결 확인...")
try:
    conn = psycopg2.connect('postgresql://trading_user:trading_pw_2024@postgres:5432/trading_db')
    cur = conn.cursor()
    
    # 최근 1시간 신호
    cur.execute("SELECT COUNT(*) FROM monitoring.signals WHERE created_at > NOW() - INTERVAL '1 hour'")
    signals_count = cur.fetchone()[0]
    print(f"   ✅ 최근 1시간 신호: {signals_count}개")
    
    # 최근 1시간 결정
    cur.execute("SELECT COUNT(*) FROM trading.decisions WHERE created_at > NOW() - INTERVAL '1 hour'")
    decisions_count = cur.fetchone()[0]
    print(f"   ✅ 최근 1시간 결정: {decisions_count}개")
    
    # 최근 신호 상세
    cur.execute("""
        SELECT strategy_id, symbol, direction, created_at 
        FROM monitoring.signals 
        WHERE created_at > NOW() - INTERVAL '10 minutes'
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    recent_signals = cur.fetchall()
    if recent_signals:
        print(f"\n   📋 최근 10분 신호:")
        for sig in recent_signals:
            print(f"      {sig[0]:10s} {sig[1]:10s} {sig[2]:5s} {sig[3]}")
    else:
        print(f"   ⚠️  최근 10분 신호 없음")
    
    conn.close()
except Exception as e:
    print(f"   ❌ DB 연결 실패: {e}")
    exit(1)

# 2. Trading Bot 초기화
print("\n2️⃣ Trading Bot 초기화...")
try:
    bot = TradingBot()
    print(f"   ✅ Trading Bot 초기화 성공")
    print(f"      전략: {bot.strategy}")
    print(f"      모드: {bot.executor.get_mode()}")
except Exception as e:
    print(f"   ❌ Trading Bot 초기화 실패: {e}")
    exit(1)

# 3. 신호 조회 테스트
print("\n3️⃣ 신호 조회 테스트...")
try:
    signals = bot.fetch_signals()
    print(f"   ✅ 신호 조회 성공: {len(signals)}개")
    
    if signals:
        sig = signals[0]
        print(f"\n   📋 첫 번째 신호:")
        print(f"      Symbol: {sig.get('symbol')}")
        print(f"      Direction: {sig.get('direction')}")
        print(f"      Entry: {sig.get('entry_price')}")
except Exception as e:
    print(f"   ❌ 신호 조회 실패: {e}")

# 4. 주문 실행 테스트 (샘플)
print("\n4️⃣ 주문 실행 테스트 (샘플)...")
try:
    test_signal = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 67000.0,
        'sl_price': 66500.0,
        'tp_price': 68000.0,
        'confidence': 0.8
    }
    
    order = bot.executor.execute_order(test_signal)
    
    if order:
        print(f"   ✅ 주문 실행 성공")
        print(f"      Order ID: {order['order_id']}")
        print(f"      Fill Price: {order['fill_price']}")
        print(f"      Qty: {order['qty']}")
    else:
        print(f"   ❌ 주문 실행 실패")
except Exception as e:
    print(f"   ❌ 주문 실행 에러: {e}")

print("\n" + "="*60)
print("✅ 전체 시스템 테스트 완료!")
print("="*60)
