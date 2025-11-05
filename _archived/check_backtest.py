#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""백테스트 상태 확인"""
import subprocess
import time

print("=" * 80)
print("📊 백테스트 로그 확인 (30초)")
print("=" * 80)

try:
    # Docker 로그 확인 (마지막 100줄)
    result = subprocess.run(
        ['docker', 'logs', 'trading_bot_sim', '--tail', '100'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
except Exception as e:
    print(f"❌ 오류: {e}")

print("\n" + "=" * 80)
