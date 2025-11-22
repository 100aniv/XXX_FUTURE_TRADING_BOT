import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="trading_db",
    user="trading_user",
    password="trading_pw_2024"
)
cur = conn.cursor()
cur.execute("SELECT COUNT(*), SUM(CASE WHEN side::text='1' THEN 1 ELSE 0 END), SUM(CASE WHEN side::text='-1' THEN 1 ELSE 0 END) FROM trading.trades")
result = cur.fetchone()
print(f"Total Trades: {result[0]}")
print(f"LONG: {result[1]}")
print(f"SHORT: {result[2]}")
conn.close()
