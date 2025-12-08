#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-9: Debug Indicators 계산 확인
ADX/DI/ATR 컬럼이 실제로 생성되는지 확인
"""
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from indicators import add_indicators

# 샘플 데이터 생성
data = {
    'time': pd.date_range('2024-01-01', periods=200, freq='5min'),
    'open': [100 + i * 0.1 for i in range(200)],
    'high': [100.5 + i * 0.1 for i in range(200)],
    'low': [99.5 + i * 0.1 for i in range(200)],
    'close': [100 + i * 0.1 for i in range(200)],
    'volume': [1000] * 200
}

df = pd.DataFrame(data)

print("=" * 80)
print("BEFORE add_indicators:")
print(f"Columns: {list(df.columns)}")
print(f"Rows: {len(df)}")

# add_indicators 호출 (use_adx=True)
df_with_indicators = add_indicators(
    df,
    ema_fast=20,
    ema_mid=50,
    ema_slow=200,
    rsi_len=14,
    macd_fast=12,
    macd_slow=26,
    macd_signal=9,
    bb_len=20,
    bb_std=2.0,
    atr_len=14,
    vol_ma_len=30,
    dc_len=20,
    use_adx=True,
    adx_period=14,
)

print("=" * 80)
print("AFTER add_indicators:")
print(f"Columns: {list(df_with_indicators.columns)}")
print(f"Rows: {len(df_with_indicators)}")

# ADX/DI 컬럼 확인
print("=" * 80)
print("ADX/DI 컬럼 확인:")
adx_cols = [c for c in df_with_indicators.columns if 'adx' in c or 'di' in c]
print(f"ADX/DI 컬럼: {adx_cols}")

# ATR 컬럼 확인
print("=" * 80)
print("ATR 컬럼 확인:")
atr_cols = [c for c in df_with_indicators.columns if 'atr' in c]
print(f"ATR 컬럼: {atr_cols}")

# 마지막 10개 행 출력
print("=" * 80)
print("마지막 행 ADX/DI/ATR 값:")
last_row = df_with_indicators.iloc[-1]
if 'adx_14' in last_row.index:
    print(f"adx_14: {last_row['adx_14']:.4f}")
if 'plus_di_14' in last_row.index:
    print(f"plus_di_14: {last_row['plus_di_14']:.4f}")
if 'minus_di_14' in last_row.index:
    print(f"minus_di_14: {last_row['minus_di_14']:.4f}")
if 'atr' in last_row.index:
    print(f"atr: {last_row['atr']:.4f}")

print("=" * 80)
print("✅ 테스트 완료")
