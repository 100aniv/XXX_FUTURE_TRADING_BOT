#!/usr/bin/env python3
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT')),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)

cur = conn.cursor()

# Total trades
cur.execute("SELECT COUNT(*) FROM trading.trades")
total = cur.fetchone()[0]
print(f"Total trades: {total}")

# By mode
cur.execute("SELECT mode, COUNT(*) FROM trading.trades GROUP BY mode")
by_mode = cur.fetchall()
print(f"\nBy mode:")
for mode, count in by_mode:
    print(f"  {mode}: {count}")

# Paper mode specifically
cur.execute("SELECT COUNT(*) FROM trading.trades WHERE mode = 'paper'")
paper_count = cur.fetchone()[0]
print(f"\nPaper mode (exact match): {paper_count}")

# Latest 5 trades
cur.execute("SELECT trade_id, symbol, strategy_id, mode, side FROM trading.trades ORDER BY ts_open DESC LIMIT 5")
latest = cur.fetchall()
print(f"\nLatest 5 trades:")
for row in latest:
    print(f"  {row}")

cur.close()
conn.close()
