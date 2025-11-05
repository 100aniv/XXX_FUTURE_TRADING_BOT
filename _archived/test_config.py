#!/usr/bin/env python3
"""설정 로드 테스트"""
from common.config import load_config

cfg = load_config()
print("=" * 60)
print("✅ config.yml 로드 테스트")
print("=" * 60)
print(f"mode: {cfg.get('mode', 'unknown')}")
print(f"symbols.mode: {cfg.get('symbols', {}).get('mode', 'unknown')}")
print(f"symbols.manual: {cfg.get('symbols', {}).get('manual', [])}")
print(f"timeframe: {cfg.get('timeframe', 'unknown')}")
print(f"capital.initial: {cfg.get('capital', {}).get('initial', 0)}")
print("=" * 60)
print("✅ 설정 로드 성공!")
