#!/usr/bin/env python3
with open('logs/application/2025-10-23.log', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    
# 최근 100줄에서 MultiSymbol 관련 라인 찾기
for line in lines[-500:]:
    if 'MultiSymbol' in line or '최종 심볼' in line or '멀티 심볼' in line:
        print(line.strip())
