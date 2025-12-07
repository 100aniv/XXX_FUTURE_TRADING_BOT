#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DB 스키마 확인 스크립트
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection

def check_schema():
    """trading.trades 테이블 스키마 확인"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'trading' AND table_name = 'trades'
                ORDER BY ordinal_position
            """)
            columns = cur.fetchall()
            
            print("=" * 80)
            print("📋 trading.trades 테이블 컬럼:")
            print("=" * 80)
            for col in columns:
                print(f"  - {col[0]}: {col[1]}")
            print("=" * 80)

if __name__ == "__main__":
    check_schema()
