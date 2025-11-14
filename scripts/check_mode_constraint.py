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
        # CHECK 제약 조건 조회
        cur.execute("""
            SELECT conname, pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'trading.trades'::regclass
            AND contype = 'c'
        """)
        rows = cur.fetchall()
        
        print("=" * 80)
        print("trading.trades CHECK 제약 조건")
        print("=" * 80)
        for r in rows:
            print(f"\n제약 이름: {r[0]}")
            print(f"제약 정의: {r[1]}")
            
except Exception as e:
    print(f"❌ {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
