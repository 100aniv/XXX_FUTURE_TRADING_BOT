#!/usr/bin/env python3
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5433,
    dbname='trading',
    user='trading_user',
    password='trading_pass'
)

cur = conn.cursor()

# Check 7D Gate trades
cur.execute("""
    SELECT COUNT(*) as count, MIN(entry_time), MAX(entry_time)
    FROM trading.trades
    WHERE trial_id = 'phase30_3_btc15m_core_v2_7d_gate'
    OR run_id = 'phase30_3_btc15m_core_v2_7d_gate'
""")
result = cur.fetchone()
print(f"7D Gate Trades: {result[0]}, Period: {result[1]} to {result[2]}")

# Check any recent trades
cur.execute("""
    SELECT trial_id, run_id, COUNT(*) as count
    FROM trading.trades
    WHERE entry_time > '2024-11-01'
    GROUP BY trial_id, run_id
    ORDER BY COUNT(*) DESC
    LIMIT 5
""")
print("\nRecent trade runs:")
for row in cur.fetchall():
    print(f"  trial_id={row[0]}, run_id={row[1]}, count={row[2]}")

cur.close()
conn.close()
