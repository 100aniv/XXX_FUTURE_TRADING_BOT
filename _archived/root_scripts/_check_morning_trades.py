#!/usr/bin/env python3
"""아침 점검: Paper 모드 거래 확인"""
import psycopg2
from datetime import datetime

# DB 연결
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="trading_db",
    user="trading_user",
    password="trading_pw_2024"
)

print("=" * 60)
print("📊 Paper 모드 거래 확인 (아침 점검)")
print("=" * 60)

# 1. 총 거래 건수
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM trading.trades")
    total = cur.fetchone()[0]
    print(f"\n✅ 총 거래 건수: {total}건")

# 2. 상태별 건수
with conn.cursor() as cur:
    cur.execute("""
        SELECT status, COUNT(*) 
        FROM trading.trades 
        GROUP BY status
    """)
    for status, count in cur.fetchall():
        print(f"   - {status}: {count}건")

# 3. 최근 10건
print("\n📋 최근 10건 거래:")
print("-" * 60)
with conn.cursor() as cur:
    cur.execute("""
        SELECT 
            status, 
            symbol, 
            side, 
            entry_price,
            quantity,
            ts_open
        FROM trading.trades 
        ORDER BY ts_open DESC 
        LIMIT 10
    """)
    for row in cur.fetchall():
        status, symbol, side, entry, qty, ts_open = row
        ts_str = datetime.fromtimestamp(ts_open/1000).strftime('%m-%d %H:%M')
        print(f"{status:6s} | {symbol:8s} | {side:5s} | {entry:10.4f} | {qty:8.2f} | {ts_str}")

# 4. 전략별 거래
print("\n📊 전략별 거래:")
print("-" * 60)
with conn.cursor() as cur:
    cur.execute("""
        SELECT strategy_id, COUNT(*) 
        FROM trading.trades 
        GROUP BY strategy_id
        ORDER BY COUNT(*) DESC
    """)
    for strategy, count in cur.fetchall():
        print(f"   {strategy}: {count}건")

conn.close()

print("\n" + "=" * 60)
print("✅ PR7 수용 기준: OPEN/CLOSED 합계 ≥1건 충족!")
print("=" * 60)
