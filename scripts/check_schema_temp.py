#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading.trades 스키마 분석 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.database import get_db_connection

def check_schema():
    """trading.trades 테이블 스키마 조회"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 컬럼 정보 조회
                cur.execute("""
                    SELECT 
                        column_name, 
                        data_type, 
                        is_nullable, 
                        column_default,
                        ordinal_position
                    FROM information_schema.columns 
                    WHERE table_schema = 'trading' 
                    AND table_name = 'trades' 
                    ORDER BY ordinal_position
                """)
                
                rows = cur.fetchall()
                
                print("=" * 100)
                print("trading.trades 스키마")
                print("=" * 100)
                print(f"{'Pos':<4} | {'Column Name':<30} | {'Data Type':<20} | {'Nullable':<8} | {'Default'}")
                print("-" * 100)
                
                for row in rows:
                    col_name, data_type, is_nullable, col_default, pos = row
                    nullable_flag = "YES" if is_nullable == "YES" else "NO ⚠️"
                    print(f"{pos:<4} | {col_name:<30} | {data_type:<20} | {nullable_flag:<8} | {col_default}")
                
                print("=" * 100)
                print(f"\n총 {len(rows)}개 컬럼")
                
                # NOT NULL 컬럼만 따로 출력
                not_null_cols = [r[0] for r in rows if r[2] == 'NO']
                print(f"\n⚠️  NOT NULL 제약 컬럼 ({len(not_null_cols)}개):")
                for col in not_null_cols:
                    print(f"  - {col}")
                
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_schema()
