#!/usr/bin/env python3
"""백테스트 완료 대기"""
import subprocess
import time

print("⏳ 백테스트 완료 대기 중...")
print("=" * 80)

while True:
    result = subprocess.run(
        ['docker', 'ps', '-a', '--filter', 'name=trading_bot_backtest', '--format', '{{.Status}}'],
        capture_output=True,
        text=True
    )
    
    status = result.stdout.strip()
    
    if 'Exited' in status:
        print("\n✅ 백테스트 완료!")
        
        # 로그에서 결과 추출
        result = subprocess.run(
            ['docker', 'logs', 'trading_bot_backtest'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        logs = result.stdout
        
        if 'Trading Engine 종료' in logs:
            for line in logs.split('\n'):
                if '총 캔들' in line or '진입 거래' in line or '종료 거래' in line:
                    print(f"   {line.strip()}")
        
        break
    elif 'Up' in status:
        print(".", end="", flush=True)
        time.sleep(10)
    else:
        print(f"\n❌ 상태 불명: {status}")
        break

print("=" * 80)
