#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""백테스트 상태 확인"""
import subprocess

print("=" * 80)
print("📊 Docker 컨테이너 상태")
print("=" * 80)

try:
    result = subprocess.run(
        ['docker', 'logs', 'trading_bot_sim', '--tail', '50'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )
    
    lines = result.stdout.split('\n')
    
    # 중요 라인만 필터링
    important = []
    for line in lines:
        if any(keyword in line for keyword in [
            '백테스트', '완료', '종료', '시작', '캔들', '거래',
            'ERROR', 'CRITICAL', '📊', '✅', '❌'
        ]):
            important.append(line)
    
    for line in important[-30:]:
        print(line)
    
    print("\n" + "=" * 80)
    print(f"총 로그 라인: {len(lines)}")
    print("=" * 80)
    
except Exception as e:
    print(f"❌ 오류: {e}")
