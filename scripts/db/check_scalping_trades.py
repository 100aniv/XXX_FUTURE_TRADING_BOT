#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check scalping trades"""
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="trading_db",
    user="trading_user",
    password="trading_pw_2024"
)

cur = conn.cursor()

# 최근 거래 확인
sql = """
SELECT strategy_id, symbol, side, entry_price, exit_price, pnl, exit_reason, 
       created_at, quantity
FROM trading.trades 
WHERE strategy_id='scalping' 
ORDER BY created_at DESC 
LIMIT 20;
"""

cur.execute(sql)
rows = cur.fetchall()

print("\n" + "="*100)
print("📊 SCALPING 최근 거래 내역")
print("="*100)

if not rows:
    print("❌ 거래 내역 없음")
else:
    for row in rows:
        strategy_id, symbol, side, entry, exit_price, pnl, reason, created_at, qty = row
        exit_str = f"{exit_price:10.2f}" if exit_price is not None else "      N/A"
        pnl_str = f"{pnl:8.2f}" if pnl is not None else "    N/A"
        print(f"\n심볼: {symbol:12} | {side:5} | Entry: {entry:10.2f} | Exit: {exit_str} | PnL: {pnl_str}")
        print(f"  수량: {qty:10.4f} | 사유: {reason or 'N/A'} | 시간: {created_at}")

# 통계
cur.execute("""
SELECT 
    COUNT(*) as total_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
    SUM(pnl) as total_pnl,
    AVG(pnl) as avg_pnl
FROM trading.trades 
WHERE strategy_id='scalping' AND status='CLOSED';
""")

stats = cur.fetchone()
total, wins, losses, total_pnl, avg_pnl = stats

print("\n" + "="*100)
print("📈 SCALPING 통계")
print("="*100)
print(f"총 거래: {total}건")
print(f"승: {wins}건 | 패: {losses}건")
print(f"승률: {(wins/total*100) if total > 0 else 0:.1f}%")
print(f"총 PnL: ${total_pnl:.2f}")
print(f"평균 PnL: ${avg_pnl:.2f}")

# 연속 손실 확인
cur.execute("""
SELECT pnl, symbol, exit_reason, created_at
FROM trading.trades
WHERE strategy_id='scalping' AND status='CLOSED'
ORDER BY created_at DESC
LIMIT 10;
""")

print("\n" + "="*100)
print("🔴 최근 10건 거래 (손실 패턴 분석)")
print("="*100)

consecutive_losses = 0
for pnl, symbol, reason, created_at in cur.fetchall():
    status = "❌ 손실" if pnl < 0 else "✅ 이익"
    print(f"{status} | ${pnl:7.2f} | {symbol:12} | {reason or 'N/A':20} | {created_at}")
    if pnl < 0:
        consecutive_losses += 1
    else:
        break

print(f"\n🚨 연속 손실: {consecutive_losses}회")

cur.close()
conn.close()
