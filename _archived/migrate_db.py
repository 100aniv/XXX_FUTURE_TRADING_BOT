#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DB Migration Script
===================
bot_id 컬럼 제거
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db")

def main():
    print("="*60)
    print("DB 마이그레이션: bot_id 제거")
    print("="*60)
    
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # bot_id 제거
        print("\n1. bot_id 컬럼 제거...")
        cur.execute("ALTER TABLE monitoring.signals DROP COLUMN IF EXISTS bot_id")
        conn.commit()
        print("✅ 완료")
        
        # 확인
        print("\n2. 현재 컬럼 확인...")
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema='monitoring' AND table_name='signals'
            ORDER BY ordinal_position
        """)
        
        columns = cur.fetchall()
        print("현재 컬럼:")
        for col_name, col_type in columns:
            print(f"  - {col_name}: {col_type}")
        
        # 데이터 확인
        print("\n3. 기존 데이터 확인...")
        cur.execute("SELECT COUNT(*) FROM monitoring.signals")
        count = cur.fetchone()[0]
        print(f"총 신호 개수: {count}개")
        
        cur.close()
        conn.close()
        
        print("\n" + "="*60)
        print("✅ 마이그레이션 완료!")
        print("="*60)
        
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()
