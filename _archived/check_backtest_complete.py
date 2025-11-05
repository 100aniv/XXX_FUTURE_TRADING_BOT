#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""백테스트 완료 확인"""
import subprocess
import time

print("=" * 80)
print("📊 백테스트 상태 확인")
print("=" * 80)

# Docker 컨테이너 상태
result = subprocess.run(
    ['docker', 'ps', '-a', '--filter', 'name=trading_bot_backtest'],
    capture_output=True,
    text=True
)

if 'Exited' in result.stdout:
    print("✅ 백테스트 완료!")
    
    # 로그 확인
    result = subprocess.run(
        ['docker', 'logs', 'trading_bot_backtest', '--tail', '100'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )
    
    lines = result.stdout.split('\n')
    
    # 완료 관련 라인만 필터링
    for line in lines:
        if any(keyword in line for keyword in [
            'Trading Engine 종료',
            '총 캔들',
            '진입 거래',
            '종료 거래',
            'HTML 리포트',
            'ERROR',
            'CRITICAL'
        ]):
            print(line)
    
    # HTML 리포트 찾기
    from pathlib import Path
    reports = list(Path('reports/backtest').glob('*.html'))
    if reports:
        latest = sorted(reports)[-1]
        print(f"\n📊 HTML 리포트: {latest}")
    
elif 'Up' in result.stdout:
    print("⏳ 백테스트 실행 중...")
    
    # 최근 로그 확인
    result = subprocess.run(
        ['docker', 'logs', 'trading_bot_backtest', '--tail', '10'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )
    
    print("\n최근 로그:")
    print(result.stdout[-500:])
    
else:
    print("❌ 컨테이너 없음")

print("\n" + "=" * 80)
