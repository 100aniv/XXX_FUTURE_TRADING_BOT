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
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'trading'
              AND table_name = 'trades'
            ORDER BY ordinal_position
        """)
        rows = cur.fetchall()
        
        print("=" * 80)
        print("trading.trades 스키마")
        print("=" * 80)
        print(f"{'Column Name':<25} {'Data Type':<20} {'Nullable':<10} {'Default'}")
        print("-" * 80)
        for r in rows:
            nullable_flag = "YES" if r[2] == "YES" else "NO ⚠️"
            print(f"{r[0]:<25} {r[1]:<20} {nullable_flag:<10} {r[3]}")
        
        # NOT NULL 컬럼만 따로 출력
        not_null_cols = [r[0] for r in rows if r[2] == 'NO']
        print("=" * 80)
        print(f"\n⚠️  NOT NULL 제약 컬럼 ({len(not_null_cols)}개):")
        for col in not_null_cols:
            print(f"  - {col}")
            
except Exception as e:
    print(f"❌ {e}")
finally:
    conn.close()
