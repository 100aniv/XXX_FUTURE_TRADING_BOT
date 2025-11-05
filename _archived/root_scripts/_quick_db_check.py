#!/usr/bin/env python3
import psycopg2

conn = psycopg2.connect('postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db')
cur = conn.cursor()

# Total
cur.execute('SELECT COUNT(*) FROM trading.trades')
total = cur.fetchone()[0]
print(f'\n✅ Total trades: {total}')

# By status
cur.execute('SELECT status, COUNT(*) FROM trading.trades GROUP BY status ORDER BY COUNT(*) DESC')
rows = cur.fetchall()
if rows:
    print('\n📊 By status:')
    for status, count in rows:
        print(f'   {status}: {count}')
else:
    print('\n⚠️ No trades yet')

# Recent 5
if total > 0:
    cur.execute("""
        SELECT status, symbol, side, entry_price, quantity, ts_open 
        FROM trading.trades 
        ORDER BY ts_open DESC 
        LIMIT 5
    """)
    print('\n📋 Recent 5 trades:')
    for row in cur.fetchall():
        status, symbol, side, entry, qty, ts_open = row
        print(f'   {status:6s} | {symbol:10s} | {side:4s} | {entry:.4f} | {qty:.2f}')

conn.close()
