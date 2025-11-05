#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DB에 leverage 컬럼 추가
"""
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

# DB 연결 (.env 파일 사용)
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'trading_bot'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

print(f"DB 연결 시도: {db_config['user']}@{db_config['host']}:{db_config['port']}/{db_config['database']}")

conn = psycopg2.connect(**db_config)

try:
    with conn.cursor() as cur:
        # 1. trading.trades 테이블에 leverage 추가
        print("1. Adding leverage to trading.trades...")
        cur.execute("""
            ALTER TABLE trading.trades 
            ADD COLUMN IF NOT EXISTS leverage DECIMAL(5,2) DEFAULT 1.0;
        """)
        cur.execute("""
            COMMENT ON COLUMN trading.trades.leverage IS '레버리지 배수';
        """)
        
        # 2. trading.decisions 테이블에 leverage 추가 ⭐
        print("2. Adding leverage to trading.decisions...")
        cur.execute("""
            ALTER TABLE trading.decisions 
            ADD COLUMN IF NOT EXISTS leverage DECIMAL(5,2) DEFAULT 1.0;
        """)
        cur.execute("""
            COMMENT ON COLUMN trading.decisions.leverage IS '레버리지 배수';
        """)
        
        # 3. trading.decisions 테이블에 executed 추가 ⭐
        print("3. Adding executed to trading.decisions...")
        cur.execute("""
            ALTER TABLE trading.decisions 
            ADD COLUMN IF NOT EXISTS executed BOOLEAN DEFAULT FALSE;
        """)
        cur.execute("""
            ALTER TABLE trading.decisions 
            ADD COLUMN IF NOT EXISTS executed_at TIMESTAMP;
        """)
        cur.execute("""
            COMMENT ON COLUMN trading.decisions.executed IS '실행 여부';
        """)
        cur.execute("""
            COMMENT ON COLUMN trading.decisions.executed_at IS '실행 시각';
        """)
        
        conn.commit()
        print("✅ 모든 leverage 컬럼 추가 완료!")
        
        # 확인
        for table in ['trades', 'decisions']:
            cur.execute("""
                SELECT column_name, data_type, column_default 
                FROM information_schema.columns 
                WHERE table_schema = 'trading' 
                  AND table_name = %s
                  AND column_name = 'leverage';
            """, (table,))
            
            result = cur.fetchone()
            if result:
                print(f"✅ trading.{table}: {result}")
            else:
                print(f"⚠️ trading.{table}에 leverage 컬럼 없음!")
            
except Exception as e:
    print(f"❌ 에러: {e}")
    conn.rollback()
finally:
    conn.close()
