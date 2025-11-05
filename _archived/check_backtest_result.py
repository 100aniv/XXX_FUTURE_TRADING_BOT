#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""백테스트 결과 확인"""
import os
from pathlib import Path

print("=" * 80)
print("📊 백테스트 결과 확인")
print("=" * 80)

# Application 로그
app_log = Path("logs/application/2025-10-21.log")
if app_log.exists():
    with open(app_log, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print("\n📝 Application 로그 (마지막 50줄):")
    print("-" * 80)
    for line in lines[-50:]:
        if any(x in line for x in ["완료", "종료", "총", "거래", "캔들", "ERROR", "WARNING"]):
            print(line.rstrip())

# Trading 로그
trading_log = Path("logs/trading/2025-10-21.log")
if trading_log.exists():
    with open(trading_log, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print("\n💰 Trading 로그 (마지막 30줄):")
    print("-" * 80)
    for line in lines[-30:]:
        if any(x in line for x in ["거래", "포지션", "PnL", "체크", "LONG", "SHORT"]):
            print(line.rstrip())

print("\n" + "=" * 80)
