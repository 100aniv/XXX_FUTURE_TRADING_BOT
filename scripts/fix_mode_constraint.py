#!/usr/bin/env python3
"""
trading.trades mode CHECK 제약 수정
backtest_clean 모드 추가
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
        print("=" * 80)
        print("trading.trades mode CHECK 제약 수정")
        print("=" * 80)
        
        # 1. 기존 제약 삭제
        print("\n[1/2] 기존 trades_mode_check 제약 삭제...")
        cur.execute("ALTER TABLE trading.trades DROP CONSTRAINT trades_mode_check")
        print("  ✅ 삭제 완료")
        
        # 2. 새 제약 추가 (backtest_clean 포함)
        print("\n[2/2] 새 trades_mode_check 제약 추가...")
        cur.execute("""
            ALTER TABLE trading.trades 
            ADD CONSTRAINT trades_mode_check 
            CHECK (mode = ANY (ARRAY['paper'::text, 'live'::text, 'backtest'::text, 'backtest_clean'::text]))
        """)
        print("  ✅ 추가 완료")
        
        conn.commit()
        
        # 3. 확인
        print("\n[검증] 새 제약 확인...")
        cur.execute("""
            SELECT pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'trading.trades'::regclass
            AND conname = 'trades_mode_check'
        """)
        result = cur.fetchone()
        print(f"  새 제약: {result[0]}")
        
        print("\n" + "=" * 80)
        print("✅ 제약 수정 완료!")
        print("=" * 80)
        print("\n허용되는 mode 값:")
        print("  - paper")
        print("  - live")
        print("  - backtest")
        print("  - backtest_clean ⭐ NEW")
        
except Exception as e:
    print(f"\n❌ 오류: {e}")
    conn.rollback()
    import traceback
    traceback.print_exc()
finally:
    conn.close()
