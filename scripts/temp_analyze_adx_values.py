#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-9: 실제 데이터에서 ADX 값 분포 확인
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from indicators import add_indicators

# 실제 데이터 로드
data_path = "data/BTCUSDT_5m_2024-01-01_2024-12-31.csv"
df = pd.read_csv(data_path)

# 날짜 필터 (7일 Mini Backtest 기간)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df[(df['timestamp'] >= '2024-10-01') & (df['timestamp'] <= '2024-10-07')]
df = df.rename(columns={'timestamp': 'time'})
df = df.reset_index(drop=True)

print(f"총 캔들 수: {len(df)}")

# 지표 계산
df = add_indicators(
    df,
    use_adx=True,
    adx_period=14,
    atr_len=14,
)

# ADX 통계
print("\n" + "="*80)
print("ADX 통계:")
print(f"ADX 평균: {df['adx_14'].mean():.2f}")
print(f"ADX 중앙값: {df['adx_14'].median():.2f}")
print(f"ADX 최대값: {df['adx_14'].max():.2f}")
print(f"ADX 최소값: {df['adx_14'].min():.2f}")

# ADX threshold 분포
threshold_15 = (df['adx_14'] >= 15).sum()
threshold_20 = (df['adx_14'] >= 20).sum()
threshold_25 = (df['adx_14'] >= 25).sum()
threshold_30 = (df['adx_14'] >= 30).sum()

print("\n" + "="*80)
print("ADX Threshold 분포:")
print(f"ADX >= 15: {threshold_15}개 ({threshold_15/len(df)*100:.1f}%)")
print(f"ADX >= 20: {threshold_20}개 ({threshold_20/len(df)*100:.1f}%)")
print(f"ADX >= 25: {threshold_25}개 ({threshold_25/len(df)*100:.1f}%)")
print(f"ADX >= 30: {threshold_30}개 ({threshold_30/len(df)*100:.1f}%)")

# DI+ vs DI- 분포
di_plus_dominant = (df['plus_di_14'] > df['minus_di_14']).sum()
di_minus_dominant = (df['minus_di_14'] > df['plus_di_14']).sum()

print("\n" + "="*80)
print("DI 분포:")
print(f"DI+ > DI-: {di_plus_dominant}개 ({di_plus_dominant/len(df)*100:.1f}%)")
print(f"DI- > DI+: {di_minus_dominant}개 ({di_minus_dominant/len(df)*100:.1f}%)")

# Regime 시뮬레이션 (ADX >= 15)
adx_trend = df[df['adx_14'] >= 15]
print("\n" + "="*80)
print(f"Trend Regime (ADX >= 15): {len(adx_trend)}개")
if len(adx_trend) > 0:
    bull_trend = adx_trend[adx_trend['plus_di_14'] > adx_trend['minus_di_14']]
    bear_trend = adx_trend[adx_trend['minus_di_14'] > adx_trend['plus_di_14']]
    print(f"  - Bull Trend: {len(bull_trend)}개")
    print(f"  - Bear Trend: {len(bear_trend)}개")

# 샘플 출력
print("\n" + "="*80)
print("ADX >= 15인 캔들 샘플 (처음 5개):")
print(adx_trend[['time', 'close', 'adx_14', 'plus_di_14', 'minus_di_14']].head())
