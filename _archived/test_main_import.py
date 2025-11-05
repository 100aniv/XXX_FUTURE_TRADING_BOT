#!/usr/bin/env python3
"""
Main Import Test
================
main.py가 정상적으로 import 되는지 테스트
"""
print("="*60)
print("main.py Import Test")
print("="*60)

try:
    print("\n1. main.py import...")
    import main
    print("✅ main.py import 성공!")
except Exception as e:
    print(f"❌ main.py import 실패: {e}")
    import traceback
    traceback.print_exc()

print("\n="*60)
print("테스트 완료!")
print("="*60)
