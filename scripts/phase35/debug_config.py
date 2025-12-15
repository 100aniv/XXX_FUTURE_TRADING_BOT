#!/usr/bin/env python3
import sys
import yaml
import json
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

config_path = project_root / "configs" / "phase35" / "phase35_2_iter3_ssot.yaml"

with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("=" * 80)
print("Config 구조 디버깅")
print("=" * 80)

print("\n1. Root level 'ensemble' 존재:", 'ensemble' in config)
if 'ensemble' in config:
    print("   ensemble:", config['ensemble'])

print("\n2. 'strategies' 존재:", 'strategies' in config)
if 'strategies' in config:
    print("   strategies keys:", list(config['strategies'].keys()))
    if 'phase35_ensemble_v1' in config['strategies']:
        print("   phase35_ensemble_v1 keys:", list(config['strategies']['phase35_ensemble_v1'].keys()))
        if 'params' in config['strategies']['phase35_ensemble_v1']:
            params = config['strategies']['phase35_ensemble_v1']['params']
            print("   params keys:", list(params.keys()))
            if 'ensemble' in params:
                print("   params.ensemble:", params['ensemble'])

print("\n3. Deep merge 시뮬레이션")
strategy_name = config.get('strategy', {}).get('selector', 'phase35_ensemble_v1')
strategy_params = config.get('strategies', {}).get(strategy_name, {}).get('params', {})

print(f"   strategy_name: {strategy_name}")
print(f"   strategy_params keys: {list(strategy_params.keys())}")

def deep_merge(base, custom):
    merged = base.copy()
    for key, value in custom.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged

merged = deep_merge(config, strategy_params)
print(f"\n4. Merged config 'ensemble' 존재:", 'ensemble' in merged)
if 'ensemble' in merged:
    print("   merged.ensemble:", merged['ensemble'])

print("\n5. 전략 초기화 시뮬레이션")
from strategies.phase35_ensemble_v1 import Phase35EnsembleV1

strategy = Phase35EnsembleV1(merged)
print(f"   _cooldown_bars: {strategy._cooldown_bars}")
print(f"   _min_votes: {strategy._min_votes}")
print(f"   _confidence_threshold: {strategy._confidence_threshold}")
