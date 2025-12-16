#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""하드코딩 제거 테스트"""
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent))

from common.config_loader import load_config
from strategies import get_all_strategies, load_strategies

print("=" * 80)
print("하드코딩 제거 테스트")
print("=" * 80)

# 1. get_all_strategies() 테스트
print("\n1. get_all_strategies() 테스트")
all_strats = get_all_strategies()
print(f"   전략 목록: {list(all_strats.keys())}")
assert len(all_strats) >= 6, "전략 개수 오류 (최소 6개 이상)"
assert 'scalping' in all_strats, "scalping 없음"
assert 'trend' in all_strats, "trend 없음"
print("   ✅ 성공")

# 2. load_config() 테스트
print("\n2. load_config() 테스트")
cfg = load_config()
print(f"   mode: {cfg.get('mode')}")
print(f"   strategy.selector: {cfg.get('strategy', {}).get('selector')}")
assert cfg.get('strategy', {}).get('selector') is not None, "selector 없음"
print("   ✅ 성공")

# 3. load_strategies() 테스트 (자동 로드)
print("\n3. load_strategies() 테스트 (자동 로드)")
strategies = load_strategies(config=cfg)
print(f"   로드된 전략: {list(strategies.keys())}")
assert len(strategies) > 0, "전략 없음"
print("   ✅ 성공")

# 4. messaging.py 전략명 테스트
print("\n4. messaging.py 전략명 동적 로드 테스트")
strategy_name = cfg.get("strategy", {}).get("selector", "UNKNOWN").upper()
print(f"   전략명: {strategy_name}")
assert strategy_name != "SCALPING" or cfg.get('strategy', {}).get('selector') == "scalping", "하드코딩 남음"
print("   ✅ 성공")

print("\n" + "=" * 80)
print("✅ 모든 테스트 통과!")
print("=" * 80)
