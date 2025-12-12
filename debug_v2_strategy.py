#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug btc15m_core_v2 strategy signal generation"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from strategies.btc15m_core_v2 import signal_logic
from common.backtest_indicators import add_core_v1_indicators

# Load sample data
data_file = "data/BTCUSDT_15m_2024-01-01_2024-12-31.csv"
df = pd.read_csv(data_file)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp')

# Filter to 7D gate period
df = df[(df['timestamp'] >= '2024-11-01') & (df['timestamp'] <= '2024-11-07')]
print(f"Loaded {len(df)} candles from 2024-11-01 to 2024-11-07")

# Add indicators
config = {
    'indicators': {
        'rsi': {'length': 14},
        'ema': {'fast': 5, 'mid': 20, 'slow': 200},
        'atr': {'length': 14},
        'adx': {'period': 14},
        'volume': {'ma_length': 20},
        'bollinger_bands': {'length': 20, 'std': 2.0}
    },
    'regime_detection': {
        'min_confidence_trend': 0.35,
        'min_confidence_range': 0.40,
        'chop_threshold': 20,
        'hysteresis_candles': 5
    }
}

df = add_core_v1_indicators(df, config)

# Check indicators
print(f"\nIndicators present: {[col for col in df.columns if col not in ['timestamp', 'open', 'high', 'low', 'close', 'volume']]}")
print(f"RSI_14 range: {df['rsi_14'].min():.2f} - {df['rsi_14'].max():.2f}")
print(f"ADX_14 range: {df['adx_14'].min():.2f} - {df['adx_14'].max():.2f}")
print(f"EMA_20 present: {'ema_20' in df.columns}")
print(f"BB columns: {[col for col in df.columns if 'bb_' in col]}")

# Test signal generation on last 10 candles
print(f"\n{'='*80}")
print("Testing signal generation on last 10 candles:")
print(f"{'='*80}\n")

for i in range(len(df) - 10, len(df)):
    df_slice = df.iloc[:i+1].copy()
    
    try:
        signal = signal_logic(df_slice, config, None, None, None)
        
        ts = df_slice.iloc[-1]['timestamp']
        close = df_slice.iloc[-1]['close']
        
        print(f"[{i-len(df)+11:2d}] {ts} | Close: {close:.2f} | Signal: {signal.get('side', 'NONE'):5s} | Reason: {signal.get('reason', 'N/A')}")
        
        if signal.get('side'):
            print(f"     --> Entry: {signal['entry']:.2f}, SL: {signal['sl']:.2f}, TP1: {signal['tp1']:.2f}, Regime: {signal['regime']}")
    
    except Exception as e:
        print(f"[{i-len(df)+11:2d}] ERROR: {e}")

print(f"\n{'='*80}")
print("Debug complete")
print(f"{'='*80}")
