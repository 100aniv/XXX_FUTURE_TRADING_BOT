#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""백테스트 최종 결과"""
import os
from pathlib import Path

print("=" * 80)
print("🎯 백테스트 최종 결과")
print("=" * 80)

app_log = Path("logs/application/2025-10-21.log")
if app_log.exists():
    with open(app_log, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"\n총 로그 라인: {len(lines):,}개")
    
    # 마지막 100줄에서 중요 정보 찾기
    for line in lines[-100:]:
        if any(keyword in line for keyword in [
            "Trading Engine 종료",
            "백테스트 완료",
            "총 캔들",
            "총 거래",
            "종료",
            "완료"
        ]):
            print(line.rstrip())

print("\n" + "=" * 80)
