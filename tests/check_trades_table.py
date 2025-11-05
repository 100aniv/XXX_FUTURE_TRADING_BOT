import psycopg2

c = psycopg2.connect('postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db')
cur = c.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='trading' AND table_name='trades' ORDER BY ordinal_position")
cols = cur.fetchall()

print("trading.trades 테이블 컬럼:")
for col in cols:
    print(f"  - {col[0]}")

c.close()
