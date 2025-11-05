#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""전체 모듈 검증 스크립트 (앙상블, 시그널, 익스큐션, 콜렉터)"""
import sys
import re
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("전체 모듈 검증 (앙상블, 시그널, 익스큐션, 콜렉터)")
print("=" * 80)

issues = defaultdict(list)
warnings = defaultdict(list)

# ============================================
# Phase 1: 앙상블 전략 검증
# ============================================
print("\n📋 Phase 1: 앙상블 전략 검증")
print("-" * 80)

ensemble_file = Path(__file__).parent / 'strategies' / 'ensemble.py'
if ensemble_file.exists():
    print("\n🔍 검토 중: ensemble.py")
    content = ensemble_file.read_text(encoding='utf-8')
    
    # 1.1 하드코딩 검증
    if 'get_all_strategies()' in content:
        print("   ✅ get_all_strategies() 활용")
    else:
        issues['ensemble'].append("❌ get_all_strategies() 미활용")
    
    # 전략 리스트 하드코딩 확인
    hardcoded_strategies = re.findall(r'\[[\'\"]scalping[\'\"]\s*,\s*[\'\"]', content)
    if hardcoded_strategies:
        issues['ensemble'].append("❌ 전략 리스트 하드코딩 발견")
    else:
        print("   ✅ 전략 리스트 하드코딩 없음")
    
    # config.get 사용
    config_usage = content.count('config.get(')
    if config_usage > 0:
        print(f"   ✅ config.get() 사용: {config_usage}회")
    else:
        warnings['ensemble'].append("⚠️ config.get() 사용 없음")
    
    # generate 함수 확인
    if 'def generate(' in content:
        print("   ✅ generate() 함수 존재")
    else:
        warnings['ensemble'].append("⚠️ generate() 함수 없음 (통합 방식일 수 있음)")
else:
    issues['ensemble'].append("❌ ensemble.py 파일 없음")

# ============================================
# Phase 2: 시그널 모듈 검증 (indicators/)
# ============================================
print("\n\n📋 Phase 2: 시그널 모듈 검증 (indicators/)")
print("-" * 80)

indicators_dir = Path(__file__).parent / 'indicators'
if indicators_dir.exists():
    indicator_files = list(indicators_dir.glob('*.py'))
    indicator_files = [f for f in indicator_files if f.name != '__init__.py']
    
    print(f"   ✅ indicators 모듈: {len(indicator_files)}개 파일")
    
    for ind_file in indicator_files[:5]:  # 처음 5개만 검증
        print(f"\n   🔍 검토: {ind_file.name}")
        content = ind_file.read_text(encoding='utf-8')
        
        # 하드코딩 확인 (14, 20 같은 일반적인 파라미터는 제외)
        lines = content.split('\n')
        hardcoded_count = 0
        for line in lines:
            if 'def ' in line or 'class ' in line or '#' in line:
                continue
            # 0.995 같은 소수점 매직넘버 찾기
            matches = re.findall(r'\b[0-9]+\.[0-9]{3,}\b', line)
            if matches and 'config' not in line:
                hardcoded_count += len(matches)
        
        if hardcoded_count > 0:
            warnings[ind_file.name].append(f"⚠️ 하드코딩 의심: {hardcoded_count}개")
        
        # 함수 정의 확인
        functions = re.findall(r'def (\w+)\(', content)
        if functions:
            print(f"      ✅ 함수: {len(functions)}개 정의")
else:
    issues['indicators'].append("❌ indicators 디렉토리 없음")

# ============================================
# Phase 3: 익스큐션 모듈 검증 (execution/)
# ============================================
print("\n\n📋 Phase 3: 익스큐션 모듈 검증 (execution/)")
print("-" * 80)

execution_dir = Path(__file__).parent / 'execution'
if execution_dir.exists():
    execution_files = [
        'engine.py',
        'portfolio_manager.py',
        'risk_manager.py',
        'position_sizer.py',
        'tp_manager.py',
        'adapters/__init__.py'
    ]
    
    for exec_file in execution_files:
        file_path = execution_dir / exec_file
        if not file_path.exists():
            warnings[exec_file].append(f"⚠️ 파일 없음: {exec_file}")
            continue
        
        print(f"\n   🔍 검토: {exec_file}")
        content = file_path.read_text(encoding='utf-8')
        
        # config 사용 확인
        config_usage = content.count('config.get(') + content.count('config[')
        if config_usage > 0:
            print(f"      ✅ config 사용: {config_usage}회")
        else:
            warnings[exec_file].append("⚠️ config 미사용")
        
        # 클래스 또는 주요 함수 확인
        classes = re.findall(r'class (\w+)', content)
        functions = re.findall(r'def (\w+)\(', content)
        
        if classes:
            print(f"      ✅ 클래스: {', '.join(classes[:3])}")
        if len(functions) > 0:
            print(f"      ✅ 함수: {len(functions)}개")
        
        # 하드코딩된 숫자 확인 (간단히)
        hardcoded = re.findall(r'= \d+\.\d{3,}(?!\))', content)
        if len(hardcoded) > 3 and 'config' not in content[:1000]:
            warnings[exec_file].append(f"⚠️ 하드코딩 의심: {len(hardcoded)}개")
else:
    issues['execution'].append("❌ execution 디렉토리 없음")

# ============================================
# Phase 4: 콜렉터 모듈 검증 (collectors/)
# ============================================
print("\n\n📋 Phase 4: 콜렉터 모듈 검증 (data collection)")
print("-" * 80)

# WebSocket 콜렉터 확인
collectors_paths = [
    Path(__file__).parent / 'collectors',
    Path(__file__).parent / 'feeds',
    Path(__file__).parent / 'data'
]

collector_found = False
for coll_path in collectors_paths:
    if coll_path.exists():
        print(f"\n   📁 발견: {coll_path.name}/")
        collector_found = True
        
        files = list(coll_path.glob('*.py'))
        files = [f for f in files if f.name != '__init__.py']
        
        print(f"      ✅ 파일: {len(files)}개")
        
        for coll_file in files[:3]:  # 처음 3개만
            print(f"      - {coll_file.name}")
            content = coll_file.read_text(encoding='utf-8')
            
            # WebSocket 관련 확인
            if 'websocket' in content.lower() or 'ws' in content.lower():
                print(f"         ✅ WebSocket 관련 코드 있음")
            
            # config 사용 확인
            if 'config' in content:
                print(f"         ✅ config 사용")

if not collector_found:
    warnings['collectors'].append("⚠️ collectors/feeds/data 디렉토리 없음")

# ============================================
# Phase 5: 모듈 간 통합 검증
# ============================================
print("\n\n📋 Phase 5: 모듈 간 통합 검증")
print("-" * 80)

# engine.py가 모든 모듈을 통합하는지 확인
engine_file = Path(__file__).parent / 'execution' / 'engine.py'
if engine_file.exists():
    content = engine_file.read_text(encoding='utf-8')
    
    modules_to_import = [
        'PortfolioManager',
        'RiskManager',
        'PositionSizer',
        'TPManager',
        'load_strategies'
    ]
    
    print("\n   🔗 engine.py 모듈 통합 확인:")
    for module in modules_to_import:
        if module in content:
            print(f"      ✅ {module} import")
        else:
            warnings['engine'].append(f"⚠️ {module} import 없음")
    
    # Feed 사용 확인
    if 'feed' in content.lower():
        print(f"      ✅ Feed 사용")
    
    # Broker 사용 확인
    if 'broker' in content.lower():
        print(f"      ✅ Broker 사용")

# ============================================
# Phase 6: 공통 모듈 검증 (common/)
# ============================================
print("\n\n📋 Phase 6: 공통 모듈 검증 (common/)")
print("-" * 80)

common_dir = Path(__file__).parent / 'common'
if common_dir.exists():
    common_files = [
        'config_loader.py',
        'logger.py',
        'messaging.py',
        'database.py',
        'calculations.py',
        'symbol_manager.py'
    ]
    
    for common_file in common_files:
        file_path = common_dir / common_file
        if file_path.exists():
            print(f"   ✅ {common_file}")
            
            content = file_path.read_text(encoding='utf-8')
            
            # 주요 함수 확인
            functions = re.findall(r'def (\w+)\(', content)
            if len(functions) > 0:
                print(f"      - 함수: {len(functions)}개")
        else:
            warnings[common_file].append(f"⚠️ {common_file} 없음")

# 결과 요약
print("\n\n" + "=" * 80)
print("📊 전체 모듈 검증 결과")
print("=" * 80)

total_issues = sum(len(v) for v in issues.values())
total_warnings = sum(len(v) for v in warnings.values())

if issues:
    print(f"\n❌ Critical Issues: {total_issues}개")
    for module, issue_list in issues.items():
        print(f"\n  [{module}]")
        for issue in issue_list:
            print(f"    {issue}")
else:
    print("\n✅ Critical Issues: 없음")

if warnings:
    print(f"\n⚠️ Warnings: {total_warnings}개")
    for module, warning_list in warnings.items():
        if warning_list:
            print(f"\n  [{module}]")
            for warning in warning_list[:3]:  # 처음 3개만
                print(f"    {warning}")
else:
    print("\n✅ Warnings: 없음")

print("\n✅ 전체 모듈 검증 완료")
print("=" * 80)

sys.exit(1 if issues else 0)
