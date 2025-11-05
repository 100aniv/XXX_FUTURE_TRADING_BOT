#!/usr/bin/env python3
"""
DB 초기화 스크립트
"""
from dotenv import load_dotenv
load_dotenv()

print("="*60)
print("🗄️  DB 초기화 시작")
print("="*60)

from common.database import get_db_connection

# SQL 파일 읽기
print("\n📄 init_db.sql 읽는 중...")
with open("init_db.sql", "r", encoding="utf-8") as f:
    sql = f.read()

print(f"✅ SQL 파일 읽기 완료 ({len(sql)} bytes)")

# DB 실행
print("\n💾 DB에 테이블 생성 중...")
try:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        cursor.close()
    
    print("✅ DB 초기화 완료!")
    
    # 테이블 확인
    print("\n📊 생성된 테이블 확인...")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        cursor.close()
    
    print("✅ 테이블 목록:")
    for table in tables:
        print(f"   - {table[0]}")

except Exception as e:
    print(f"❌ DB 초기화 실패: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("✅ 완료!")
print("="*60)
