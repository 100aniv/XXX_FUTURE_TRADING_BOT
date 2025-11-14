#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DB CHECK 제약 조건 수정: backtest_raw 모드 추가
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

from database.postgres import get_db_connection

def fix_mode_constraint():
    """trading.trades 테이블의 mode CHECK 제약 조건에 backtest_raw 추가"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                print("=" * 60)
                print("PHASE9 DB FIX: backtest_raw 모드 추가")
                print("=" * 60)
                
                # 1. 기존 제약 조건 확인
                cur.execute("""
                    SELECT conname, pg_get_constraintdef(oid) as definition
                    FROM pg_constraint
                    WHERE conrelid = 'trading.trades'::regclass
                      AND contype = 'c'
                      AND conname = 'trades_mode_check';
                """)
                
                result = cur.fetchone()
                if result:
                    print(f"\n[기존 CHECK 제약]")
                    print(f"Name: {result[0]}")
                    print(f"Definition: {result[1]}")
                else:
                    print("\n⚠️  trades_mode_check 제약 조건을 찾을 수 없습니다.")
                
                # 2. 제약 조건 삭제
                print("\n[STEP 1] 기존 제약 조건 삭제...")
                cur.execute("""
                    ALTER TABLE trading.trades
                    DROP CONSTRAINT IF EXISTS trades_mode_check;
                """)
                conn.commit()
                print("✅ 기존 제약 조건 삭제 완료")
                
                # 3. 새로운 제약 조건 추가 (backtest_raw 포함)
                print("\n[STEP 2] 새로운 제약 조건 추가 (backtest_raw 포함)...")
                cur.execute("""
                    ALTER TABLE trading.trades
                    ADD CONSTRAINT trades_mode_check 
                    CHECK (mode IN ('paper', 'live', 'backtest', 'backtest_clean', 'backtest_raw'));
                """)
                conn.commit()
                print("✅ 새로운 제약 조건 추가 완료")
                
                # 4. 수정된 제약 조건 확인
                cur.execute("""
                    SELECT conname, pg_get_constraintdef(oid) as definition
                    FROM pg_constraint
                    WHERE conrelid = 'trading.trades'::regclass
                      AND contype = 'c'
                      AND conname = 'trades_mode_check';
                """)
                
                result = cur.fetchone()
                print(f"\n[수정된 CHECK 제약]")
                print(f"Name: {result[0]}")
                print(f"Definition: {result[1]}")
                
                print("\n" + "=" * 60)
                print("✅ PHASE9 DB FIX 완료!")
                print("=" * 60)
                
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    fix_mode_constraint()
