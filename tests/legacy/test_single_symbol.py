#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
단일 심볼 테스트 (BTCUSDT만)
"""
import yaml

# config.yml 수정
config_path = 'config.yml'

with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 심볼 모드를 manual로 변경
config['symbols']['mode'] = 'manual'

# manual 심볼을 BTCUSDT만 남김
config['symbols']['manual'] = ['BTCUSDT']

# 포지션 제한을 1개로 (테스트용)
config['portfolio']['max_positions'] = 1

# Risk per trade 줄임 (1% → 0.5%)
if 'scalping' in config['strategies']:
    config['strategies']['scalping']['risk_per_trade'] = 0.005  # 0.5%

# 저장
with open(config_path, 'w', encoding='utf-8') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

print("✅ 테스트 설정 완료:")
print(f"  - 심볼: {config['symbols']['manual']}")
print(f"  - 최대 포지션: {config['portfolio']['max_positions']}")
print(f"  - Risk per trade: {config['strategies']['scalping']['risk_per_trade']*100:.1f}%")
