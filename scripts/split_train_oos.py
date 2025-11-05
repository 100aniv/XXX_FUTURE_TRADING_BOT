#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Train/OOS 데이터 분리 스크립트
================================
2024년 데이터를 Train/OOS로 분리

Input: BTCUSDT_5m_2024-01-01_2024-12-31.csv
Output:
  - BTCUSDT_5m_2024-01-01_2024-09-30_TRAIN.csv (9개월)
  - BTCUSDT_5m_2024-10-01_2024-12-31_OOS.csv (3개월)
"""
import pandas as pd
from pathlib import Path
from datetime import datetime

# 경로 설정
data_dir = Path(__file__).parent.parent / 'data'
input_file = data_dir / 'BTCUSDT_5m_2024-01-01_2024-12-31.csv'

# 분리 기준일
train_end = '2024-09-30 23:55:00'
oos_start = '2024-10-01 00:00:00'

print("="*60)
print("📂 Train/OOS 데이터 분리")
print("="*60)

# 데이터 로드
print(f"\n📥 로드: {input_file.name}")
df = pd.read_csv(input_file)

# 타임스탬프 컬럼 확인
time_col = None
for col in ['timestamp', 'time', 'closed_at', 'open_time']:
    if col in df.columns:
        time_col = col
        break

if not time_col:
    print("❌ 타임스탬프 컬럼을 찾을 수 없습니다!")
    exit(1)

print(f"   타임스탬프 컬럼: {time_col}")
print(f"   총 캔들: {len(df):,}개\n")

# 타임스탬프 변환
df[time_col] = pd.to_datetime(df[time_col])

# Train 분리
train_df = df[df[time_col] <= train_end].copy()
train_file = data_dir / 'BTCUSDT_5m_2024-01-01_2024-09-30_TRAIN.csv'
train_df.to_csv(train_file, index=False)
print(f"✅ Train: {len(train_df):,}개 캔들")
print(f"   기간: {train_df[time_col].iloc[0]} ~ {train_df[time_col].iloc[-1]}")
print(f"   파일: {train_file.name}\n")

# OOS 분리
oos_df = df[df[time_col] >= oos_start].copy()
oos_file = data_dir / 'BTCUSDT_5m_2024-10-01_2024-12-31_OOS.csv'
oos_df.to_csv(oos_file, index=False)
print(f"✅ OOS: {len(oos_df):,}개 캔들")
print(f"   기간: {oos_df[time_col].iloc[0]} ~ {oos_df[time_col].iloc[-1]}")
print(f"   파일: {oos_file.name}\n")

# 검증
total_split = len(train_df) + len(oos_df)
if total_split == len(df):
    print("✅ 분리 검증 성공: Train + OOS = 원본")
else:
    print(f"⚠️  분리 검증 실패: Train({len(train_df)}) + OOS({len(oos_df)}) != 원본({len(df)})")

# 비율 확인
train_pct = len(train_df) / len(df) * 100
oos_pct = len(oos_df) / len(df) * 100
print(f"\n📊 비율:")
print(f"   Train: {train_pct:.1f}%")
print(f"   OOS: {oos_pct:.1f}%")

print("\n" + "="*60)
print("✅ 분리 완료!")
print("="*60)
