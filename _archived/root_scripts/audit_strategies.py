#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""전략 시스템 검증 스크립트"""
import sys
import re
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("전략 시스템 검증")
print("=" * 80)

# Phase 1: 전략 파일 검토
print("\n📋 Phase 1: 전략 파일 검토")
print("-" * 80)

strategies_dir = Path(__file__).parent / "strategies"
strategy_files = [
    'scalping.py', 'daytrade.py', 'swing.py', 
    'trend.py', 'reversion.py', 'breakout.py'
]

issues = defaultdict(list)
warnings = defaultdict(list)

for strategy_file in strategy_files:
    file_path = strategies_dir / strategy_file
    strategy_name = strategy_file.replace('.py', '')
    
    print(f"\n🔍 검토 중: {strategy_name}")
    
    if not file_path.exists():
        issues[strategy_name].append(f"❌ 파일 없음: {file_path}")
        continue
    
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    # 1.1 하드코딩 검증
    hardcoded_numbers = []
    for i, line in enumerate(lines, 1):
        # config.get 없이 사용되는 숫자 리터럴 찾기 (주석 제외)
        if '//' in line or '#' in line:
            code_part = line.split('#')[0] if '#' in line else line.split('//')[0]
        else:
            code_part = line
        
        # 매직넘버 패턴: 함수 호출, 인덱싱, config.get 제외
        if 'config.get' not in code_part and 'config[' not in code_part:
            # 0.995, 1.005 같은 소수점 숫자
            matches = re.findall(r'\b[0-9]+\.[0-9]+\b', code_part)
            for match in matches:
                if match not in ['0.0', '1.0', '2.0', '0.5']:  # 일반적인 값 제외
                    if 'iloc' not in code_part and 'get(' not in code_part:
                        hardcoded_numbers.append((i, match, line.strip()))
    
    if hardcoded_numbers:
        warnings[strategy_name].append(f"⚠️ 하드코딩 의심 ({len(hardcoded_numbers)}개):")
        for line_num, number, line_content in hardcoded_numbers[:3]:  # 처음 3개만
            warnings[strategy_name].append(f"   Line {line_num}: {number} in '{line_content[:60]}'")
    
    # 1.2 필수 함수 확인
    if 'def signal_logic(' not in content:
        issues[strategy_name].append("❌ signal_logic() 함수 없음")
    else:
        print("   ✅ signal_logic() 존재")
    
    # 1.3 config 파라미터 사용 확인
    config_usage = content.count('config.get(')
    if config_usage == 0:
        warnings[strategy_name].append("⚠️ config.get() 사용 안 함 (모든 값이 하드코딩?)")
    else:
        print(f"   ✅ config.get() 사용: {config_usage}회")
    
    # 1.4 모듈 import 확인
    required_imports = ['pandas', 'typing']
    for req_import in required_imports:
        if f'import {req_import}' not in content and f'from {req_import}' not in content:
            warnings[strategy_name].append(f"⚠️ {req_import} import 없음")
    
    # 1.5 indicators 모듈 활용
    if 'from indicators import' not in content and 'import indicators' not in content:
        warnings[strategy_name].append("⚠️ indicators 모듈 미사용")
    else:
        print("   ✅ indicators 모듈 활용")
    
    # 1.6 common 모듈 활용
    if 'from common' not in content:
        warnings[strategy_name].append("⚠️ common 모듈 미사용")
    else:
        print("   ✅ common 모듈 활용")

# Phase 2: 앙상블 검증
print("\n\n📋 Phase 2: 앙상블 검증")
print("-" * 80)

ensemble_file = strategies_dir / 'ensemble.py'
if ensemble_file.exists():
    content = ensemble_file.read_text(encoding='utf-8')
    
    # get_all_strategies() 활용 확인
    if 'get_all_strategies()' in content:
        print("   ✅ get_all_strategies() 활용")
    else:
        issues['ensemble'].append("❌ get_all_strategies() 미활용 (하드코딩?)")
    
    # 전략 리스트 하드코딩 확인
    hardcoded_list = re.findall(r'\[[\'\"]scalping[\'\"]\s*,', content)
    if hardcoded_list:
        warnings['ensemble'].append("⚠️ 전략 리스트 하드코딩 의심")
    
    print("   ✅ ensemble.py 검증 완료")

# Phase 3: __init__.py 검증
print("\n\n📋 Phase 3: __init__.py 검증")
print("-" * 80)

init_file = strategies_dir / '__init__.py'
if init_file.exists():
    content = init_file.read_text(encoding='utf-8')
    
    if 'def get_all_strategies()' in content:
        print("   ✅ get_all_strategies() 정의됨")
    else:
        issues['__init__'].append("❌ get_all_strategies() 없음")
    
    if 'def load_strategies(' in content:
        print("   ✅ load_strategies() 정의됨")
    else:
        issues['__init__'].append("❌ load_strategies() 없음")

# 결과 요약
print("\n\n" + "=" * 80)
print("📊 검증 결과 요약")
print("=" * 80)

print(f"\n✅ 검증한 전략: {len(strategy_files)}개")

if issues:
    print(f"\n❌ Critical Issues: {sum(len(v) for v in issues.values())}개")
    for strategy, issue_list in issues.items():
        print(f"\n  [{strategy}]")
        for issue in issue_list:
            print(f"    {issue}")
else:
    print("\n✅ Critical Issues: 없음")

if warnings:
    print(f"\n⚠️ Warnings: {sum(len(v) for v in warnings.values())}개")
    for strategy, warning_list in warnings.items():
        print(f"\n  [{strategy}]")
        for warning in warning_list:
            print(f"    {warning}")
else:
    print("\n✅ Warnings: 없음")

# 체크리스트 업데이트
checklist_file = Path(__file__).parent / 'STRATEGY_AUDIT_CHECKLIST.md'
if checklist_file.exists():
    print(f"\n📝 체크리스트 업데이트: {checklist_file.name}")

print("\n" + "=" * 80)

# 종료 코드
sys.exit(1 if issues else 0)
