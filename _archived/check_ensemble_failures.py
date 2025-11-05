#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ensemble 실패 원인 확인"""
import subprocess

print("=" * 80)
print("🔍 Ensemble 실패 로그 확인")
print("=" * 80)

# Docker 로그에서 "Ensemble 오류" 검색
result = subprocess.run(
    ['docker', 'logs', '--tail', '5000', '0d1fea932301_trading_bot_backtest'],
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='ignore'
)

logs = result.stdout

# Ensemble 오류 카운트
ensemble_errors = []
for line in logs.split('\n'):
    if 'Ensemble 오류' in line or 'ensemble' in line.lower() and 'error' in line.lower():
        ensemble_errors.append(line)

print(f"\n📊 Ensemble 오류 발생 횟수: {len(ensemble_errors)}건")

if ensemble_errors:
    print("\n📋 샘플 오류 (최근 10건):")
    for err in ensemble_errors[-10:]:
        print(f"   {err[:150]}")

# DB 연결 오류 체크
db_errors = [line for line in logs.split('\n') if 'db_postgres' in line.lower() or 'database' in line.lower() and 'error' in line.lower()]
if db_errors:
    print(f"\n📊 DB 연결 오류: {len(db_errors)}건")
    print("   샘플:")
    for err in db_errors[:5]:
        print(f"   {err[:150]}")

print("=" * 80)
