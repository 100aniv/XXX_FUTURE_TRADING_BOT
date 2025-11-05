#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Execution 모듈 종합 검증
- 중복 import
- 하드코딩
- config 로딩
- 환경변수 사용
"""
import os
import re
from pathlib import Path

execution_dir = Path('execution')
issues = []
warnings = []

print("=" * 80)
print("🔍 Execution 모듈 종합 검증")
print("=" * 80)

# 1. 중복 import 검사
print("\n[1] 중복 import 검사")
print("-" * 80)

for py_file in execution_dir.rglob('*.py'):
    if '__pycache__' in str(py_file):
        continue
    
    with open(py_file, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # import 문 추출
    imports = {}
    for i, line in enumerate(lines, 1):
        if line.strip().startswith('from ') or line.strip().startswith('import '):
            # 주석 제거
            code_line = line.split('#')[0].strip()
            if not code_line:
                continue
            
            # import 추출
            if 'from' in code_line:
                match = re.match(r'from\s+(\S+)\s+import', code_line)
                if match:
                    module = match.group(1)
                    if module in imports:
                        issues.append({
                            'file': str(py_file),
                            'line': i,
                            'type': 'DUPLICATE_IMPORT',
                            'detail': f"중복 import: {module} (이전: L{imports[module]})"
                        })
                    else:
                        imports[module] = i

print(f"검사 완료: {len(list(execution_dir.rglob('*.py')))}개 파일")

# 2. 하드코딩 검사
print("\n[2] 하드코딩 검사")
print("-" * 80)

hardcoded_patterns = [
    (r'\b(10000|50000|100000)\b', 'HARDCODED_NUMBER', '하드코딩된 숫자 (자본/금액)'),
    (r'leverage\s*=\s*\d+', 'HARDCODED_LEVERAGE', '하드코딩된 레버리지'),
    (r'max_positions\s*=\s*\d+', 'HARDCODED_POSITIONS', '하드코딩된 포지션 수'),
    (r"['\"]BTCUSDT['\"]", 'HARDCODED_SYMBOL', '하드코딩된 심볼'),
    (r"['\"]scalping['\"]", 'HARDCODED_STRATEGY', '하드코딩된 전략명'),
]

for py_file in execution_dir.rglob('*.py'):
    if '__pycache__' in str(py_file):
        continue
    
    with open(py_file, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        # 주석과 문자열 제외
        code_line = line.split('#')[0]
        
        for pattern, issue_type, desc in hardcoded_patterns:
            if re.search(pattern, code_line):
                # 예외: config.get(), 로깅 메시지, 주석 내부는 허용
                if 'config.get' in code_line or 'logger.' in code_line or 'print(' in code_line:
                    continue
                if '"""' in line or "'''" in line:
                    continue
                
                warnings.append({
                    'file': str(py_file),
                    'line': i,
                    'type': issue_type,
                    'detail': f"{desc}: {code_line.strip()}"
                })

print(f"검사 완료")

# 3. config 로딩 검사
print("\n[3] config 로딩 패턴 검사")
print("-" * 80)

for py_file in execution_dir.rglob('*.py'):
    if '__pycache__' in str(py_file):
        continue
    
    with open(py_file, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        # 잘못된 config 접근
        if re.search(r"config\['[^']+'\]\['[^']+'\]\['[^']+'\]", line):
            warnings.append({
                'file': str(py_file),
                'line': i,
                'type': 'DEEP_CONFIG_ACCESS',
                'detail': f"깊은 config 접근 (get() 권장): {line.strip()}"
            })
        
        # get() 없이 직접 접근
        if re.search(r"config\['[^']+'\](?!\s*\.get)", line) and 'config.get' not in line:
            if '=' not in line.split('#')[0]:  # 할당문이 아닌 경우만
                warnings.append({
                    'file': str(py_file),
                    'line': i,
                    'type': 'UNSAFE_CONFIG_ACCESS',
                    'detail': f"안전하지 않은 config 접근: {line.strip()}"
                })

print(f"검사 완료")

# 4. 환경변수 사용 검사
print("\n[4] 환경변수 사용 검사")
print("-" * 80)

for py_file in execution_dir.rglob('*.py'):
    if '__pycache__' in str(py_file):
        continue
    
    with open(py_file, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        # os.getenv 사용 (execution에서는 config를 통해 받아야 함)
        if 'os.getenv' in line or 'os.environ' in line:
            warnings.append({
                'file': str(py_file),
                'line': i,
                'type': 'DIRECT_ENV_ACCESS',
                'detail': f"직접 환경변수 접근 (config 통해 받기 권장): {line.strip()}"
            })

print(f"검사 완료")

# 5. 결과 출력
print("\n" + "=" * 80)
print("📊 검증 결과")
print("=" * 80)

if issues:
    print(f"\n❌ Critical Issues: {len(issues)}개")
    for issue in issues:
        print(f"\n  파일: {issue['file']}")
        print(f"  라인: {issue['line']}")
        print(f"  타입: {issue['type']}")
        print(f"  상세: {issue['detail']}")
else:
    print("\n✅ Critical Issues: 없음")

if warnings:
    print(f"\n⚠️  Warnings: {len(warnings)}개")
    for warning in warnings[:10]:  # 처음 10개만
        print(f"\n  파일: {warning['file']}")
        print(f"  라인: {warning['line']}")
        print(f"  타입: {warning['type']}")
        print(f"  상세: {warning['detail']}")
    
    if len(warnings) > 10:
        print(f"\n  ... 외 {len(warnings) - 10}개")
else:
    print("\n✅ Warnings: 없음")

print("\n" + "=" * 80)
print(f"총 검사 파일: {len(list(execution_dir.rglob('*.py')))}개")
print(f"Critical Issues: {len(issues)}개")
print(f"Warnings: {len(warnings)}개")
print("=" * 80)
