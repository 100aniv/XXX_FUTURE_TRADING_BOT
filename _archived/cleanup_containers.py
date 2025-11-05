#!/usr/bin/env python3
"""
Docker 컨테이너 정리 스크립트
============================
기존 봇들 중지 및 삭제
"""
import subprocess
import sys

print("="*60)
print("🗑️  Docker 컨테이너 정리")
print("="*60)

# 삭제할 컨테이너 목록
containers_to_remove = [
    "signal_bot_trend",
    "signal_bot_reversion", 
    "signal_bot_breakout",
    "signal_bot_ensemble",
    "trading_manager",
    "signal_bot_scalp",
    "signal_bot_daytrade",
    "signal_bot_intraday",
    "signal_bot_swing",
]

print("\n현재 실행 중인 컨테이너:")
subprocess.run(["docker", "ps", "-a"], shell=True)

print("\n" + "="*60)
print("정리 시작...")
print("="*60)

removed = 0
for container in containers_to_remove:
    try:
        # 중지
        result_stop = subprocess.run(
            ["docker", "stop", container],
            capture_output=True,
            text=True,
            shell=True
        )
        
        # 삭제
        result_rm = subprocess.run(
            ["docker", "rm", container],
            capture_output=True,
            text=True,
            shell=True
        )
        
        if result_rm.returncode == 0:
            print(f"✅ {container} 삭제 완료")
            removed += 1
        else:
            print(f"⏭️  {container} 없음")
    except Exception as e:
        print(f"⚠️  {container} 처리 실패: {e}")

print("\n" + "="*60)
print(f"✅ 정리 완료! ({removed}개 컨테이너 삭제)")
print("="*60)

print("\n유지된 컨테이너:")
subprocess.run(["docker", "ps", "-a"], shell=True)

print("\n" + "="*60)
print("다음 단계:")
print("  docker-compose up -d")
print("="*60)
