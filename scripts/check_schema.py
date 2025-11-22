#!/usr/bin/env python3
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5433,
    database='trading_db',
    user='trading_user',
    password='trading_pw_2024'
)
cur = conn.cursor()

# trades 테이블 스키마
print("=== trading.trades schema ===")
cur.execute("""
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name='trades' AND table_schema='trading' 
ORDER BY ordinal_position
""")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# runs 테이블 스키마
print("\n=== trading.runs schema ===")
cur.execute("""
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name='runs' AND table_schema='trading' 
ORDER BY ordinal_position
""")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# 샘플 데이터
print("\n=== Sample trades (최근 5건) ===")
cur.execute("SELECT * FROM trading.trades ORDER BY created_at DESC LIMIT 5")
cols = [desc[0] for desc in cur.description]
print(f"Columns: {cols}")
for row in cur.fetchall():
    print(f"  {dict(zip(cols, row))}")

conn.close()
