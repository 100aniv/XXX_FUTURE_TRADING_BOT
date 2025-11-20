#!/usr/bin/env python3
"""PHASE20-1 결과 검증"""
import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# .env 로드
load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    port=int(os.getenv('DB_PORT', '5433')),
    database=os.getenv('DB_NAME', 'trading_db'),
    user=os.getenv('DB_USER', 'trading_user'),
    password=os.getenv('DB_PASSWORD', 'trading_pw_2024')
)
cursor = conn.cursor()

print("=" * 70)
print("📊 PHASE20-1 PAPER MODE TRADES ANALYSIS")
print("=" * 70)

# Paper 모드 거래 조회
cursor.execute("""
    SELECT 
        COUNT(*) as total_trades,
        SUM(CASE WHEN side='LONG' THEN 1 ELSE 0 END) as long_trades,
        SUM(CASE WHEN side='SHORT' THEN 1 ELSE 0 END) as short_trades,
        ROUND(AVG(pnl)::numeric, 2) as avg_pnl,
        ROUND(SUM(pnl)::numeric, 2) as total_pnl,
        ROUND(MIN(pnl)::numeric, 2) as min_pnl,
        ROUND(MAX(pnl)::numeric, 2) as max_pnl
    FROM trading.trades 
    WHERE mode = 'paper'
""")

result = cursor.fetchone()
print(f"✅ Total Trades: {result[0]}")
print(f"✅ LONG: {result[1]}, SHORT: {result[2]}")
print(f"✅ Avg PnL: ${result[3]}, Total PnL: ${result[4]}")
print(f"✅ Min PnL: ${result[5]}, Max PnL: ${result[6]}")

# Acceptance Criteria 검증
print("\n" + "=" * 70)
print("✅ ACCEPTANCE CRITERIA CHECK")
print("=" * 70)

trades_count = result[0]
if trades_count >= 3:
    print(f"✅ Trade Count >= 3: {trades_count} PASS")
else:
    print(f"❌ Trade Count >= 3: {trades_count} FAIL")

print("\n" + "=" * 70)
print("📈 RECENT 10 TRADES")
print("=" * 70)

cursor.execute("""
    SELECT 
        id, symbol, side, entry_price, exit_price, qty, pnl, created_at
    FROM trading.trades 
    WHERE mode = 'paper'
    ORDER BY created_at DESC 
    LIMIT 10
""")

for row in cursor.fetchall():
    print(f"ID: {row[0]}, {row[1]} {row[2]}, Entry: ${row[3]}, Exit: ${row[4]}, Qty: {row[5]}, PnL: ${row[6]}, Time: {row[7]}")

cursor.close()
conn.close()

print("\n" + "=" * 70)
print("✅ PHASE20-1 Result Check Complete")
print("=" * 70)
