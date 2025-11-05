#!/usr/bin/env python3
with open('logs/application/2025-10-23.log', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    
# 파일 시작 부분에서 심볼 관련 라인 찾기
print("=== 로그 시작 부분 (첫 100줄에서 심볼 관련) ===")
for i, line in enumerate(lines[:100]):
    if '심볼' in line or 'symbol' in line.lower() or 'MultiSymbol' in line:
        print(f"[{i}] {line.strip()}")

print("\n=== 최근 로그 (마지막 100줄에서 Trading Engine) ===")
for i, line in enumerate(lines[-100:]):
    if 'Trading Engine' in line or '총 캔들' in line or '진입 거래' in line:
        print(f"[{len(lines)-100+i}] {line.strip()}")
