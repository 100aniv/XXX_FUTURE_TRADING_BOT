#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""기능 모듈 검증 스크립트"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("기능 모듈 검증 (Phase 2)")
print("=" * 80)

issues = []
warnings = []

# 2.1 Portfolio Manager
print("\n📋 2.1 Portfolio Manager")
print("-" * 80)

pm_file = Path(__file__).parent / 'execution' / 'portfolio_manager.py'
if pm_file.exists():
    content = pm_file.read_text(encoding='utf-8')
    
    # config 사용 확인
    if 'config.get(' in content:
        print("   ✅ config 기반 설정")
    else:
        issues.append("❌ PortfolioManager: config 미사용")
    
    # 주요 메서드 확인
    methods = ['can_open_position', 'add_position', 'remove_position', 'update_equity']
    for method in methods:
        if f'def {method}' in content:
            print(f"   ✅ {method}() 존재")
        else:
            issues.append(f"❌ PortfolioManager: {method}() 없음")
    
    # 하드코딩 확인
    if content.count('config.get(') < 5:
        warnings.append("⚠️ PortfolioManager: config.get() 사용 빈도 낮음 (하드코딩 의심)")
    
    print("   ✅ PortfolioManager 검증 완료")

# 2.2 Risk Manager
print("\n📋 2.2 Risk Manager")
print("-" * 80)

rm_file = Path(__file__).parent / 'execution' / 'risk_manager.py'
if rm_file.exists():
    content = rm_file.read_text(encoding='utf-8')
    
    # config 사용 확인
    if 'config.get(' in content:
        print("   ✅ config 기반 설정")
    else:
        issues.append("❌ RiskManager: config 미사용")
    
    # 주요 메서드 확인
    methods = ['check', 'update_pnl', 'flash_guard_check']
    for method in methods:
        if f'def {method}' in content:
            print(f"   ✅ {method}() 존재")
        else:
            warnings.append(f"⚠️ RiskManager: {method}() 없음")
    
    # Flash Guard 확인
    if 'flash_guard' in content or 'Flash Guard' in content:
        print("   ✅ Flash Guard 구현됨")
    else:
        warnings.append("⚠️ RiskManager: Flash Guard 미구현")
    
    # 연속 손실 쿨다운
    if 'consecutive' in content or 'cooldown' in content:
        print("   ✅ 연속 손실 쿨다운 구현됨")
    else:
        warnings.append("⚠️ RiskManager: 연속 손실 쿨다운 미구현")
    
    print("   ✅ RiskManager 검증 완료")

# 2.3 Position Sizer
print("\n📋 2.3 Position Sizer")
print("-" * 80)

ps_file = Path(__file__).parent / 'execution' / 'position_sizer.py'
if ps_file.exists():
    content = ps_file.read_text(encoding='utf-8')
    
    # config 사용 확인
    if 'config.get(' in content:
        print("   ✅ config 기반 설정")
    else:
        issues.append("❌ PositionSizer: config 미사용")
    
    # calculate 메서드 확인
    if 'def calculate(' in content:
        print("   ✅ calculate() 존재")
    else:
        issues.append("❌ PositionSizer: calculate() 없음")
    
    # 청산가 버퍼 확인
    if 'liq_buffer' in content or 'liquidation' in content:
        print("   ✅ 청산가 버퍼 구현됨")
    else:
        warnings.append("⚠️ PositionSizer: 청산가 버퍼 미구현")
    
    print("   ✅ PositionSizer 검증 완료")

# 2.4 TP Manager
print("\n📋 2.4 TP Manager")
print("-" * 80)

tp_file = Path(__file__).parent / 'execution' / 'tp_manager.py'
if tp_file.exists():
    content = tp_file.read_text(encoding='utf-8')
    
    # config 사용 확인
    if 'config.get(' in content:
        print("   ✅ config 기반 설정")
    else:
        issues.append("❌ TPManager: config 미사용")
    
    # calculate_tp_levels 메서드 확인
    if 'def calculate_tp_levels(' in content:
        print("   ✅ calculate_tp_levels() 존재")
    else:
        issues.append("❌ TPManager: calculate_tp_levels() 없음")
    
    # 트레일링 스톱 확인
    if 'trail' in content:
        print("   ✅ 트레일링 스톱 구현됨")
    else:
        warnings.append("⚠️ TPManager: 트레일링 스톱 미구현")
    
    print("   ✅ TPManager 검증 완료")

# 2.5 MTF (Multi-Timeframe)
print("\n📋 2.5 MTF 확인")
print("-" * 80)

# indicators 폴더에서 MTF 관련 파일 찾기
indicators_dir = Path(__file__).parent / 'indicators'
mtf_files = list(indicators_dir.glob('*mtf*.py'))

if mtf_files:
    print(f"   ✅ MTF 파일 발견: {len(mtf_files)}개")
    for mtf_file in mtf_files:
        print(f"      - {mtf_file.name}")
    
    # MTF 캐시 확인
    for mtf_file in mtf_files:
        content = mtf_file.read_text(encoding='utf-8')
        if 'cache' in content.lower():
            print(f"   ✅ {mtf_file.name}: 캐시 메커니즘 있음")
else:
    warnings.append("⚠️ MTF 파일 없음 (indicators/*mtf*.py)")

# engine.py에서 MTF 활용 확인
engine_file = Path(__file__).parent / 'execution' / 'engine.py'
if engine_file.exists():
    content = engine_file.read_text(encoding='utf-8')
    if 'mtf' in content.lower():
        print("   ✅ engine.py: MTF 활용 중")
    else:
        warnings.append("⚠️ engine.py: MTF 미활용")

print("\n\n" + "=" * 80)
print("📊 Phase 2 검증 결과")
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

print("\n" + "=" * 80)

sys.exit(1 if issues else 0)
