#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Breakout 전략 디버깅
"""
import pandas as pd
from indicators import add_indicators

# 백테스트 데이터 로드
df = pd.read_csv('data/BTCUSDT_5m_2025-10-08_2025-10-22.csv')
print(f"컬럼: {df.columns.tolist()}")
# timestamp 컬럼이 있으면 변환
if 'timestamp' in df.columns:
    df['timestamp'] = pd.to_datetime(df['timestamp'])

# 지표 추가
df = add_indicators(df)

# Donchian 돌파 확인
print("=" * 60)
print("Donchian Channel 분석")
print("=" * 60)

# 통계
print(f"\n전체 캔들: {len(df)}")
print(f"DC Upper 범위: {df['dc_upper'].min():.2f} ~ {df['dc_upper'].max():.2f}")
print(f"DC Lower 범위: {df['dc_lower'].min():.2f} ~ {df['dc_lower'].max():.2f}")

# 돌파 확인
upper_breaks = df[df['close'] > df['dc_upper']]
lower_breaks = df[df['close'] < df['dc_lower']]

print(f"\nDC Upper 돌파: {len(upper_breaks)}건")
print(f"DC Lower 돌파: {len(lower_breaks)}건")

# EMA 추세 확인
ema_long = df[df['ema_fast'] > df['ema_slow']]
ema_short = df[df['ema_fast'] < df['ema_slow']]

print(f"\nEMA 상승: {len(ema_long)}건 ({len(ema_long)/len(df)*100:.1f}%)")
print(f"EMA 하락: {len(ema_short)}건 ({len(ema_short)/len(df)*100:.1f}%)")

# 조건 결합
long_signals = df[(df['close'] > df['dc_upper']) & (df['ema_fast'] > df['ema_slow'])]
short_signals = df[(df['close'] < df['dc_lower']) & (df['ema_fast'] < df['ema_slow'])]

print(f"\nLONG 신호: {len(long_signals)}건")
print(f"SHORT 신호: {len(short_signals)}건")

# 샘플 출력
if len(upper_breaks) > 0:
    print("\n상단 돌파 샘플 (처음 5개):")
    print(upper_breaks[['timestamp', 'close', 'dc_upper', 'ema_fast', 'ema_slow']].head())

if len(long_signals) > 0:
    print("\nLONG 신호 샘플:")
    print(long_signals[['timestamp', 'close', 'dc_upper', 'ema_fast', 'ema_slow']].head())
else:
    print("\n❌ LONG 신호 없음!")
    # 가장 근접한 경우 찾기
    df['dc_diff'] = df['close'] - df['dc_upper']
    closest = df.nsmallest(5, 'dc_diff')
    print("\n가장 근접한 경우 (Top 5):")
    print(closest[['timestamp', 'close', 'dc_upper', 'dc_diff', 'ema_fast', 'ema_slow']])
