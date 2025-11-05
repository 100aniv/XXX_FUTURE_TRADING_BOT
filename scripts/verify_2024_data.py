#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2024년 데이터 검증 스크립트
"""
import pandas as pd
from pathlib import Path

data_file = Path(__file__).parent.parent / 'data' / 'BTCUSDT_5m_2024-01-01_2024-12-31.csv'

if not data_file.exists():
    print("❌ 데이터 파일 없음!")
    exit(1)

print(f"📂 파일: {data_file.name}")
print(f"📊 크기: {data_file.stat().st_size / 1024 / 1024:.2f} MB\n")

# 데이터 로드
df = pd.read_csv(data_file)

print(f"✅ 총 캔들 수: {len(df):,}개")
print(f"📋 컬럼: {list(df.columns)}\n")

# 타임스탬프 컬럼 찾기
time_col = None
for col in ['time', 'closed_at', 'timestamp', 'open_time']:
    if col in df.columns:
        time_col = col
        break

if time_col:
    print(f"📅 시작: {df.iloc[0][time_col]}")
    print(f"📅 종료: {df.iloc[-1][time_col]}")
else:
    print(f"⚠️  타임스탬프 컬럼 없음")

# 기대값: 1년 5분봉 = 365 × 24 × 12 = 105,120개
expected = 105120
actual = len(df)
coverage = (actual / expected) * 100

print(f"\n📊 커버리지: {coverage:.1f}% ({actual:,}/{expected:,})")

# NULL 체크
null_counts = df.isnull().sum()
if null_counts.sum() > 0:
    print(f"\n⚠️  NULL 발견:")
    for col, count in null_counts[null_counts > 0].items():
        print(f"   - {col}: {count}개")
else:
    print(f"\n✅ NULL 없음")

# 중복 체크
duplicates = df.duplicated().sum()
if duplicates > 0:
    print(f"⚠️  중복: {duplicates}개")
else:
    print(f"✅ 중복 없음")

print(f"\n{'='*50}")
if coverage >= 95 and null_counts.sum() == 0 and duplicates == 0:
    print("✅ 데이터 품질 양호 - 백테스트 준비 완료")
else:
    print("⚠️  데이터 품질 검토 필요")
