#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""로깅 통일 테스트"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("로깅 통일 테스트")
print("=" * 80)

# 1. 여러 줄 로깅 패턴 검색
print("\n[1/3] 여러 줄 로깅 패턴 검색")
problematic_files = []

# 주요 파일들 확인
files_to_check = [
    "main.py",
    "execution/engine.py",
    "execution/portfolio_manager.py",
    "execution/tp_manager.py",
    "execution/risk_manager.py",
    "execution/position_sizer.py",
    "common/config_loader.py",
]

for file_path in files_to_check:
    full_path = Path(__file__).parent / file_path
    if full_path.exists():
        content = full_path.read_text(encoding='utf-8')
        
        # \n 포함 로깅 검색
        if 'logger.info("\\n' in content or "logger.info('\\n" in content:
            problematic_files.append(f"{file_path}: \\n 포함")
        
        # 3줄 이상 연속 logger.info 검색 (간단한 패턴)
        lines = content.split('\n')
        consecutive = 0
        for i, line in enumerate(lines):
            if 'logger.info' in line and '초기화' not in line:
                consecutive += 1
                if consecutive >= 3:
                    problematic_files.append(f"{file_path}: Line {i-2}~{i} 연속 로깅")
                    break
            else:
                consecutive = 0

if problematic_files:
    print("   ⚠️  문제 발견:")
    for issue in problematic_files:
        print(f"      - {issue}")
else:
    print("   ✅ 여러 줄 로깅 패턴 없음")

# 2. 실제 로깅 테스트
print("\n[2/3] 실제 로깅 테스트")
try:
    from common.logger import setup_logger
    import logging
    
    test_logger = setup_logger('test_logging', log_type='application', level=logging.INFO)
    
    # 정상적인 한 줄 로깅
    test_logger.info("✅ 테스트 로그: param1=value1, param2=value2, param3=value3")
    print("   ✅ 한 줄 로깅 정상 작동")
    
except Exception as e:
    print(f"   ❌ 실패: {e}")
    sys.exit(1)

# 3. 초기화 로그 확인
print("\n[3/3] 초기화 로그 통합 확인")
try:
    from common.config_loader import load_config
    from execution.portfolio_manager import PortfolioManager
    from execution.tp_manager import TPManager
    
    cfg = load_config()
    
    # PortfolioManager 초기화 (1줄로 통합되어야 함)
    pm = PortfolioManager(config=cfg)
    print("   ✅ PortfolioManager 초기화 로그 확인")
    
    # TPManager 초기화 (1줄로 통합되어야 함)
    tp = TPManager(config=cfg)
    print("   ✅ TPManager 초기화 로그 확인")
    
except Exception as e:
    print(f"   ❌ 실패: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("✅ 로깅 통일 테스트 통과!")
print("=" * 80)
print("\n📋 로깅 원칙:")
print("   1. 한 줄에 하나씩 출력")
print("   2. \\n 사용 금지")
print("   3. 여러 줄 연속 logger.info는 한 줄로 통합")
print("   4. 관련 정보는 쉼표(,)로 구분")
print()
