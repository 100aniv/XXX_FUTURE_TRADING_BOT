#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze scalping issue in detail"""
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="trading_db",
    user="trading_user",
    password="trading_pw_2024"
)

cur = conn.cursor()

print("\n" + "="*100)
print("🔍 SCALPING 문제 분석")
print("="*100)

# 1. Status별 거래 수
cur.execute("""
SELECT status, COUNT(*) 
FROM trading.trades 
WHERE strategy_id='scalping'
GROUP BY status;
""")

print("\n📊 Status별 거래 수:")
for status, count in cur.fetchall():
    print(f"  {status}: {count}건")

# 2. CLOSED된 거래 중 최근 10건
cur.execute("""
SELECT symbol, side, entry_price, exit_price, pnl, quantity, exit_reason, created_at
FROM trading.trades
WHERE strategy_id='scalping' AND status='CLOSED'
ORDER BY created_at DESC
LIMIT 10;
""")

print("\n📋 CLOSED 거래 최근 10건:")
for symbol, side, entry, exit_p, pnl, qty, reason, created_at in cur.fetchall():
    exit_str = f"{exit_p:.2f}" if exit_p is not None else "N/A"
    pnl_str = f"{pnl:.2f}" if pnl is not None else "N/A"
    print(f"  {symbol:12} | {side:5} | Entry: {entry:.2f} | Exit: {exit_str:10} | PnL: {pnl_str:10} | {reason or 'N/A'}")

# 3. 실제로 청산된 거래의 통계
cur.execute("""
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
    SUM(pnl) as total_pnl,
    MIN(pnl) as min_pnl,
    MAX(pnl) as max_pnl,
    AVG(pnl) as avg_pnl
FROM trading.trades
WHERE strategy_id='scalping' 
AND status='CLOSED'
AND exit_price IS NOT NULL;
""")

stats = cur.fetchone()
if stats and stats[0] > 0:
    total, wins, losses, total_pnl, min_pnl, max_pnl, avg_pnl = stats
    print("\n📈 실제 청산된 거래 통계:")
    print(f"  총: {total}건")
    print(f"  승: {wins}건 | 패: {losses}건")
    print(f"  승률: {(wins/total*100) if total > 0 else 0:.1f}%")
    print(f"  총 PnL: ${total_pnl:.2f}")
    print(f"  평균 PnL: ${avg_pnl:.2f}")
    print(f"  최대 이익: ${max_pnl:.2f}")
    print(f"  최대 손실: ${min_pnl:.2f}")
else:
    print("\n⚠️ 실제 청산된 거래가 없습니다!")

# 4. 손실 원인 분석
cur.execute("""
SELECT exit_reason, COUNT(*), AVG(pnl)
FROM trading.trades
WHERE strategy_id='scalping' 
AND status='CLOSED'
AND pnl < 0
GROUP BY exit_reason
ORDER BY COUNT(*) DESC;
""")

print("\n🔴 손실 원인 분석:")
for reason, count, avg_pnl in cur.fetchall():
    print(f"  {reason or 'UNKNOWN':30} | {count:4}건 | 평균 손실: ${avg_pnl:.2f}")

# 5. 포지션 크기 분석
cur.execute("""
SELECT 
    MIN(quantity) as min_qty,
    MAX(quantity) as max_qty,
    AVG(quantity) as avg_qty,
    MIN(entry_price * quantity) as min_value,
    MAX(entry_price * quantity) as max_value,
    AVG(entry_price * quantity) as avg_value
FROM trading.trades
WHERE strategy_id='scalping'
AND status='CLOSED';
""")

qty_stats = cur.fetchone()
if qty_stats:
    print("\n📏 포지션 크기 분석:")
    print(f"  수량: MIN={qty_stats[0]:.2f} | MAX={qty_stats[1]:.2f} | AVG={qty_stats[2]:.2f}")
    print(f"  가치: MIN=${qty_stats[3]:.2f} | MAX=${qty_stats[4]:.2f} | AVG=${qty_stats[5]:.2f}")

# 6. 최근 활동 확인
cur.execute("""
SELECT 
    DATE(created_at) as trade_date,
    COUNT(*) as trades,
    SUM(CASE WHEN status='CLOSED' THEN 1 ELSE 0 END) as closed,
    SUM(pnl) as daily_pnl
FROM trading.trades
WHERE strategy_id='scalping'
GROUP BY DATE(created_at)
ORDER BY trade_date DESC
LIMIT 7;
""")

print("\n📅 최근 7일 활동:")
for trade_date, trades, closed, daily_pnl in cur.fetchall():
    pnl_str = f"${daily_pnl:.2f}" if daily_pnl is not None else "N/A"
    print(f"  {trade_date} | 총: {trades:4}건 | CLOSED: {closed:4}건 | PnL: {pnl_str}")

cur.close()
conn.close()

print("\n" + "="*100)
