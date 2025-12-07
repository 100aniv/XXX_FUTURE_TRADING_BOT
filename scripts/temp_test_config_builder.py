#!/usr/bin/env python3
"""
PHASE28-4: build_tuning_config() 테스트
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tuning.utils.config_builder import build_tuning_config
import json

# Test params
params = {
    'rsi_long_threshold': 42,
    'rsi_short_threshold': 58,
    'bb_std_main': 1.2,
    'bb_std_strong': 1.5,
    'momentum_lookback': 5,
    'momentum_threshold': 0.001,
    'use_adx': True,
    'adx_period': 14,
    'adx_trend_threshold': 20,
    'rr': 1.5,
    'atr_mult_sl': 1.5,
    'max_hold_minutes': 60
}

# Build config
config = build_tuning_config(
    base_config_path='configs/backtest/phase28_2_btc5m_tuning_base.yml',
    strategy_params=params,
    trial_id='test_job_123',
    run_id='test_run_456',
    mode='backtest',
    period_override=None
)

print("=" * 80)
print("Config Build Test")
print("=" * 80)

print("\n[1] trial_id:", config.get('trial_id'))
print("[2] run_id:", config.get('run_id'))
print("[3] mode:", config.get('mode'))

strategy_selector = config.get('strategy', {}).get('selector', 'UNKNOWN')
print(f"\n[4] strategy.selector: {strategy_selector}")

# Check strategies section
strategies = config.get('strategies', {})
if strategy_selector in strategies:
    strategy_cfg = strategies[strategy_selector]
    print(f"\n[5] strategies.{strategy_selector} keys: {list(strategy_cfg.keys())}")
    print(f"\n[6] strategies.{strategy_selector} params:")
    for key, value in params.items():
        actual = strategy_cfg.get(key)
        match = "✅" if actual == value else f"❌ (actual={actual})"
        print(f"  {key}: {value} {match}")
else:
    print(f"\n[ERROR] strategies.{strategy_selector} NOT FOUND!")

# Check top-level (after merge_strategy_config would run)
print("\n[7] Top-level params (before merge_strategy_config):")
for key in ['rsi_long_threshold', 'rsi_short_threshold', 'bb_std_main']:
    value = config.get(key, 'NOT_SET')
    print(f"  {key}: {value}")

print("\n" + "=" * 80)
print("✅ Config build completed")
print("=" * 80)
