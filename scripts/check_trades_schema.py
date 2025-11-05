#!/usr/bin/env python3
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT')),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)

try:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_schema = 'trading'
              AND table_name = 'trades'
            ORDER BY ordinal_position
        """)
        rows = cur.fetchall()
        
        print("=" * 60)
        print("trading.trades 스키마")
        print("=" * 60)
        for r in rows:
            print(f"{r[0]:20} {r[1]:20} {r[2]}")
            
except Exception as e:
    print(f"❌ {e}")
finally:
    conn.close()
