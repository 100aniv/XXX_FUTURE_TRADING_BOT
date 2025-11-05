#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전체 플로우 테스트 - 시간 범위 늘려서
✅ 업데이트: execution 모듈 사용
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

os.environ['DATABASE_URL'] = 'postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db'
os.environ['STRATEGY_SELECTOR'] = 'daytrade'
os.environ['TRADING_MODE'] = 'backtest'
os.environ['EQUITY_USDT'] = '10000'
os.environ['RISK_PER_TRADE'] = '0.01'

print("=" * 70)
print("전체 플로우 테스트")
print("=" * 70)

# 1. 최근 1시간 내 신호 조회 (시간 범위 확대)
print("\n[1] 신호 조회 중...")

DB_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DB_URL)

with conn.cursor(cursor_factory=RealDictCursor) as cur:
    cur.execute("""
        SELECT 
            signal_id, strategy_id, symbol, direction, confidence,
            entry_price, sl_price, tp_price, created_at
        FROM monitoring.signals
        WHERE strategy_id = 'daytrade'
          AND created_at > NOW() - INTERVAL '1 hour'
          AND direction != 'FLAT'
        ORDER BY created_at DESC
        LIMIT 5
    """)
    signals = cur.fetchall()
    
    print(f"   최근 1시간 내 신호: {len(signals)}개")
    
    if not signals:
        # 전체에서 최근 5개
        cur.execute("""
            SELECT 
                signal_id, strategy_id, symbol, direction, confidence,
                entry_price, sl_price, tp_price, created_at
            FROM monitoring.signals
            WHERE strategy_id = 'daytrade'
              AND direction != 'FLAT'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        signals = cur.fetchall()
        print(f"   ⚠️  대신 전체 최근 신호 {len(signals)}개 사용")

conn.close()

if not signals:
    print("\n❌ 신호가 없습니다!")
    exit(1)

# 2. Trading Manager로 주문 실행 테스트
print("\n[2] Trading Executor 테스트...")

# ✅ 새로운 execution 모듈 import
from execution import TradingExecutor

executor = TradingExecutor(mode='backtest')

for idx, sig in enumerate(signals[:2], 1):  # 처음 2개만
    print(f"\n  [{idx}] {sig['symbol']} {sig['direction']}")
    print(f"      Entry: {sig['entry_price']}, SL: {sig['sl_price']}, TP: {sig['tp_price']}")
    
    # 주문 신호 생성
    order_signal = {
        'symbol': sig['symbol'],
        'side': sig['direction'],
        'entry_price': float(sig['entry_price']),
        'sl_price': float(sig['sl_price']),
        'tp_price': float(sig['tp_price']),
        'confidence': float(sig['confidence'])
    }
    
    try:
        # 주문 실행
        order = executor.execute_order(order_signal)
        
        if order:
            print(f"      ✅ 주문 실행 성공!")
            print(f"         Order ID: {order.get('order_id')}")
            print(f"         Qty: {order.get('qty')}")
            print(f"         Fill Price: {order.get('fill_price')}")
        else:
            print(f"      ❌ 주문 실행 실패")
    except Exception as e:
        print(f"      ❌ 에러: {e}")

print("\n" + "=" * 70)
print("테스트 완료!")
print("=" * 70)
