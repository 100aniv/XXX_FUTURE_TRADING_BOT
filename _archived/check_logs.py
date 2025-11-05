#!/usr/bin/env python3
"""로그 확인 스크립트"""
import os

log_file = 'logs/application/2025-10-21.log'

if os.path.exists(log_file):
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print("=" * 80)
    print("📊 최근 로그 분석")
    print("=" * 80)
    
    # Manual/Paper/Trading Engine 관련
    print("\n[1] 시스템 시작 로그:")
    for line in lines:
        if any(keyword in line for keyword in ['Manual 모드', 'Paper 모드', 'Trading Engine']):
            print(line.strip())
    
    # 버퍼 초기화
    print("\n[2] 버퍼 초기화:")
    buffer_lines = [l for l in lines if '버퍼 초기화' in l]
    for line in buffer_lines[-10:]:
        print(line.strip())
    
    # WebSocket 연결
    print("\n[3] WebSocket:")
    ws_lines = [l for l in lines if 'WebSocket' in l]
    for line in ws_lines[-5:]:
        print(line.strip())
    
    # 에러
    print("\n[4] 최근 에러:")
    error_lines = [l for l in lines if 'ERROR' in l]
    for line in error_lines[-10:]:
        print(line.strip())
    
    print("\n" + "=" * 80)
    print(f"✅ 총 {len(lines)}줄 로그 분석 완료")
else:
    print(f"❌ 로그 파일 없음: {log_file}")
