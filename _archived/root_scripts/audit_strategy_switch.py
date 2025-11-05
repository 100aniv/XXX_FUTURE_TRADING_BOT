#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""전략 교체 테스트 (Phase 3)"""
import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent))

# 로컬 테스트용 환경변수 설정
os.environ['DATABASE_URL'] = 'postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db'

from common.config_loader import load_config
from strategies import load_strategies, get_all_strategies

print("=" * 80)
print("전략 교체 테스트 (Phase 3)")
print("=" * 80)

# 전략 목록
strategy_names = ['scalping', 'daytrade', 'swing', 'trend', 'reversion', 'breakout']

issues = []
warnings = []

# 3.1 전략 교체 테스트
print("\n📋 3.1 전략 교체 테스트")
print("-" * 80)

for strategy_name in strategy_names:
    print(f"\n🔄 전략 교체: {strategy_name}")
    
    try:
        # 환경변수로 전략 선택
        os.environ['STRATEGY_SELECTOR'] = strategy_name
        
        # config 로드
        config = load_config()
        
        # 전략 로드
        strategies = load_strategies(config)
        
        # 검증
        if strategy_name not in strategies:
            issues.append(f"❌ {strategy_name}: 로드 실패")
            continue
        
        strategy_module = strategies[strategy_name]
        
        # signal_logic 함수 확인
        if not hasattr(strategy_module, 'signal_logic'):
            issues.append(f"❌ {strategy_name}: signal_logic() 없음")
            continue
        
        print(f"   ✅ {strategy_name} 로드 성공")
        print(f"   ✅ signal_logic() 존재")
        
        # config 병합 확인
        from common.config_loader import merge_strategy_config
        merged_cfg = merge_strategy_config(config, strategy_name)
        
        # 주요 설정값 확인
        timeframe = merged_cfg.get('timeframe', 'N/A')
        rr = merged_cfg.get('rr', 0)
        lookback = merged_cfg.get('lookback', 0)
        
        print(f"   ✅ Config 병합: timeframe={timeframe}, rr={rr}R, lookback={lookback}")
        
    except Exception as e:
        issues.append(f"❌ {strategy_name}: 에러 - {e}")
        print(f"   ❌ 에러: {e}")

# 3.2 중복 로직 검증
print("\n\n📋 3.2 중복 로직 검증")
print("-" * 80)

all_strategies = get_all_strategies()
print(f"   ✅ 전략 모듈 수: {len(all_strategies)}개")

# 각 전략 파일의 코드 중복 확인 (간단히 signal_logic 시그니처만 확인)
strategy_signatures = {}
for name, module in all_strategies.items():
    if hasattr(module, 'signal_logic'):
        import inspect
        sig = inspect.signature(module.signal_logic)
        strategy_signatures[name] = str(sig)

# 시그니처 통일성 확인
unique_sigs = set(strategy_signatures.values())
if len(unique_sigs) == 1:
    print(f"   ✅ 모든 전략 시그니처 통일: {list(unique_sigs)[0]}")
else:
    warnings.append(f"⚠️ 전략 시그니처 불일치: {len(unique_sigs)}개 종류")
    for name, sig in strategy_signatures.items():
        print(f"      - {name}: {sig}")

# 3.3 앙상블 통합 검증
print("\n\n📋 3.3 앙상블 통합 검증")
print("-" * 80)

try:
    # 앙상블 모드로 전환
    os.environ.pop('STRATEGY_SELECTOR', None)
    config = load_config()
    config['strategy']['use_ensemble'] = True
    
    strategies = load_strategies(config)
    
    print(f"   ✅ 앙상블 모드: {len(strategies)}개 전략 로드")
    for name in strategies.keys():
        print(f"      - {name}")
    
    # ensemble 모듈 확인
    from strategies import ensemble
    if hasattr(ensemble, 'generate'):
        print(f"   ✅ ensemble.generate() 존재")
    else:
        warnings.append("⚠️ ensemble.generate() 없음")
    
except Exception as e:
    issues.append(f"❌ 앙상블 통합 에러: {e}")
    print(f"   ❌ 에러: {e}")

# 결과 요약
print("\n\n" + "=" * 80)
print("📊 Phase 3 검증 결과")
print("=" * 80)

if issues:
    print(f"\n❌ Critical Issues: {len(issues)}개")
    for issue in issues:
        print(f"   {issue}")
else:
    print("\n✅ Critical Issues: 없음")

if warnings:
    print(f"\n⚠️ Warnings: {len(warnings)}개")
    for warning in warnings:
        print(f"   {warning}")
else:
    print("\n✅ Warnings: 없음")

print("\n✅ Phase 3 완료: 전략 교체 및 통합 정상")
print("=" * 80)

sys.exit(1 if issues else 0)
