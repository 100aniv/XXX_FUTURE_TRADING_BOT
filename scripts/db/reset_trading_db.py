#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reset trading database"""
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="trading_db",
    user="trading_user",
    password="trading_pw_2024"
)

cur = conn.cursor()

print("🗑️  Trading DB 초기화 시작...")

# 1. trades 테이블 모든 데이터 삭제
cur.execute("DELETE FROM trading.trades;")
print("✅ trading.trades 삭제 완료")

# 2. signals 테이블 삭제 (있다면)
try:
    cur.execute("DELETE FROM monitoring.signals;")
    print("✅ monitoring.signals 삭제 완료")
except Exception as e:
    print(f"⚠️ monitoring.signals 삭제 실패 (테이블 없을 수 있음): {e}")

# 3. 기타 관련 테이블 삭제 (있다면)
try:
    cur.execute("DELETE FROM trading.positions;")
    print("✅ trading.positions 삭제 완료")
except Exception as e:
    print(f"⚠️ trading.positions 삭제 실패: {e}")

conn.commit()

# 확인
cur.execute("SELECT COUNT(*) FROM trading.trades;")
count = cur.fetchone()[0]
print(f"\n📊 최종 확인: trading.trades 레코드 수 = {count}")

cur.close()
conn.close()

print("\n✅ DB 초기화 완료!")
