#!/usr/bin/env python3
import psycopg2
from datetime import datetime

conn = psycopg2.connect('postgresql://postgres:1q2w3e4r!@localhost:5432/trading_db')
cur = conn.cursor()

sql = """
SELECT symbol, side, entry, sl, tp1, exit_price, exit_reason, pnl_pct, ts_open 
FROM trading.trades 
WHERE ts_open >= NOW() - INTERVAL '10 minutes' 
  AND status = 'CLOSED' 
ORDER BY ts_open DESC 
LIMIT 20
"""

cur.execute(sql)
rows = cur.fetchall()

if rows:
    print(f"\n{'='*80}")
    print(f"CLOSED TRADES (Last 10 minutes): {len(rows)} trades")
    print(f"{'='*80}\n")
    
    for row in rows:
        symbol, side, entry, sl, tp1, exit_price, exit_reason, pnl_pct, ts_open = row
        print(f"Symbol: {symbol} | Side: {side}")
        print(f"Entry: {entry:.6f} | SL: {sl:.6f} | TP1: {tp1:.6f}")
        print(f"Exit: {exit_price:.6f} | Reason: {exit_reason}")
        print(f"PnL: {pnl_pct:.2f}% | Time: {ts_open}")
        
        # 검증
        if pnl_pct < -8.0:
            print(f"❌ 8% 초과 손실 발견!")
        if exit_reason == 'TP1' and pnl_pct < 0:
            print(f"❌ TP1 손실 발견!")
        
        print(f"{'-'*80}\n")
else:
    print("No closed trades in last 10 minutes")

conn.close()
