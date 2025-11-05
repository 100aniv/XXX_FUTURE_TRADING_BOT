#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WFA(Walk-Forward Analysis) 블록 생성
====================================
BACKTEST_PERIODS.md 요구사항:
- Reversion(15m): Train 6~12주 → OOS 2~4주, 6~8회 롤링
- 대표 레짐 블록 사용 (2024년)
"""
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# 경로 설정
data_dir = Path(__file__).parent.parent / 'data'
input_file = data_dir / 'BTCUSDT_5m_2024-01-01_2024-12-31.csv'

print("="*80)
print("📊 WFA 블록 생성 (BACKTEST_PERIODS.md 준수)")
print("="*80)

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

df[time_col] = pd.to_datetime(df[time_col])
print(f"   타임스탬프 컬럼: {time_col}")
print(f"   총 캔들: {len(df):,}개\n")

# WFA 블록 정의 (Train 8주 → OOS 3주, 6회 롤링)
# 2024년 대표 레짐 커버
wfa_blocks = [
    {
        'name': 'WFA_01',
        'train_start': '2024-01-01',
        'train_end': '2024-02-25',    # 8주
        'oos_start': '2024-02-26',
        'oos_end': '2024-03-17',      # 3주
        'regime': 'ETF_APPROVAL',     # 2024-01-10 ETF 승인
    },
    {
        'name': 'WFA_02',
        'train_start': '2024-02-26',
        'train_end': '2024-04-21',    # 8주
        'oos_start': '2024-04-22',
        'oos_end': '2024-05-12',      # 3주
        'regime': 'HALVING',          # 2024-04-19/20 반감기
    },
    {
        'name': 'WFA_03',
        'train_start': '2024-04-22',
        'train_end': '2024-06-16',    # 8주
        'oos_start': '2024-06-17',
        'oos_end': '2024-07-07',      # 3주
        'regime': 'POST_HALVING',
    },
    {
        'name': 'WFA_04',
        'train_start': '2024-06-17',
        'train_end': '2024-08-11',    # 8주
        'oos_start': '2024-08-12',
        'oos_end': '2024-09-01',      # 3주
        'regime': 'SUMMER_RANGE',
    },
    {
        'name': 'WFA_05',
        'train_start': '2024-08-12',
        'train_end': '2024-10-06',    # 8주
        'oos_start': '2024-10-07',
        'oos_end': '2024-10-27',      # 3주
        'regime': 'Q4_VOLATILITY',
    },
    {
        'name': 'WFA_06',
        'train_start': '2024-10-07',
        'train_end': '2024-12-01',    # 8주
        'oos_start': '2024-12-02',
        'oos_end': '2024-12-22',      # 3주
        'regime': 'YEAR_END',
    },
]

print("📂 WFA 블록 생성 중...\n")

# 블록별 파일 생성
for block in wfa_blocks:
    name = block['name']
    regime = block['regime']
    
    # Train 데이터
    train_mask = (df[time_col] >= block['train_start']) & (df[time_col] <= block['train_end'])
    train_df = df[train_mask].copy()
    train_file = data_dir / f"BTCUSDT_5m_{name}_TRAIN_{regime}.csv"
    train_df.to_csv(train_file, index=False)
    
    # OOS 데이터
    oos_mask = (df[time_col] >= block['oos_start']) & (df[time_col] <= block['oos_end'])
    oos_df = df[oos_mask].copy()
    oos_file = data_dir / f"BTCUSDT_5m_{name}_OOS_{regime}.csv"
    oos_df.to_csv(oos_file, index=False)
    
    print(f"✅ {name} ({regime})")
    print(f"   Train: {len(train_df):,}개 ({block['train_start']} ~ {block['train_end']})")
    print(f"   OOS:   {len(oos_df):,}개 ({block['oos_start']} ~ {block['oos_end']})")
    print(f"   파일: {train_file.name}, {oos_file.name}\n")

# 요약 저장
summary_file = data_dir / 'WFA_BLOCKS_SUMMARY.csv'
summary_df = pd.DataFrame(wfa_blocks)
summary_df.to_csv(summary_file, index=False)
print(f"✅ 요약: {summary_file.name}\n")

print("="*80)
print("✅ WFA 블록 생성 완료!")
print(f"   총 {len(wfa_blocks)}개 블록 (Train 8주 → OOS 3주)")
print("   대표 레짐: ETF 승인, 반감기, 변동성, 레인지 등")
print("="*80)
