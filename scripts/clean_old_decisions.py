#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
오래된 decisions 정리
"""
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
        # entry_price가 None인 오래된 decisions 삭제
        print("1. entry_price가 None인 decisions 삭제...")
        cur.execute("""
            DELETE FROM trading.decisions
            WHERE entry_price IS NULL OR sl_price IS NULL OR tp_price IS NULL
        """)
        deleted = cur.rowcount
        print(f"✅ {deleted}건 삭제")
        
        # 1시간 이상 된 미실행 decisions 삭제
        print("\n2. 1시간 이상 된 미실행 decisions 삭제...")
        cur.execute("""
            DELETE FROM trading.decisions
            WHERE executed = FALSE
              AND created_at < NOW() - INTERVAL '1 hour'
        """)
        deleted = cur.rowcount
        print(f"✅ {deleted}건 삭제")
        
        conn.commit()
        print("\n✅ 정리 완료!")
        
except Exception as e:
    print(f"❌ 에러: {e}")
    conn.rollback()
finally:
    conn.close()
