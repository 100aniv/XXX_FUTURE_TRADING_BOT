#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-1-FIX: Strategy Import Sanity Check
============================================

전략 import 실패를 0.5초 내로 즉시 탐지

Exit Codes:
    0: 성공
    1: Import 실패
"""
import sys
import traceback
from pathlib import Path

# Project root 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))


def check_strategy_import(strategy_name: str, module_path: str, class_name: str = None):
    """
    전략 import 및 클래스 존재 확인
    
    Args:
        strategy_name: 전략 이름
        module_path: 모듈 경로 (예: strategies.phase35_ensemble_v1)
        class_name: 클래스 이름 (None이면 모듈만 체크)
    
    Returns:
        bool: 성공 여부
    """
    print(f"[CHECK] {strategy_name}: {module_path}", end=" ")
    
    try:
        # 모듈 import
        module = __import__(module_path, fromlist=[''])
        
        if class_name:
            # 클래스 존재 확인
            if not hasattr(module, class_name):
                print(f"❌ FAIL - Class '{class_name}' not found")
                return False
            
            cls = getattr(module, class_name)
            print(f"✅ OK - {cls.__name__}")
        else:
            print(f"✅ OK - Module loaded")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL")
        print(f"Error: {e}")
        traceback.print_exc()
        return False


def main():
    """메인 함수"""
    print("=" * 80)
    print("PHASE35-1-FIX: Strategy Import Sanity Check")
    print("=" * 80)
    print()
    
    # PHASE35 전략 체크
    checks = [
        ("phase35_ensemble_v1 (module)", "strategies.phase35_ensemble_v1", None),
        ("phase35_ensemble_v1 (class)", "strategies.phase35_ensemble_v1", "Phase35EnsembleV1"),
    ]
    
    all_pass = True
    for name, module_path, class_name in checks:
        result = check_strategy_import(name, module_path, class_name)
        if not result:
            all_pass = False
    
    print()
    print("=" * 80)
    if all_pass:
        print("✅ All checks PASSED")
        return 0
    else:
        print("❌ Some checks FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
