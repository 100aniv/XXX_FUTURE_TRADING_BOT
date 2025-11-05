#!/usr/bin/env python3
"""DB 스키마 확인"""
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="trading_db",
    user="trading_user",
    password="trading_pw_2024"
)

print("=" * 60)
print("🔍 trading.trades 테이블 스키마 확인")
print("=" * 60)

with conn.cursor() as cur:
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'trading' AND table_name = 'trades'
        ORDER BY ordinal_position
    """)
    
    print("\n컬럼 목록:")
    print("-" * 60)
    for col_name, data_type, is_nullable in cur.fetchall():
        nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
        print(f"{col_name:20s} | {data_type:20s} | {nullable}")

print("\n" + "=" * 60)
print("✅ 확인 완료")
print("=" * 60)

conn.close()
