#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUNING_VIBLE 테스트 (PostgreSQL 기반)
====================================
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

load_dotenv()

from analytics.report_generator import generate_backtest_report
import logging

# 로거 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

print("=" * 80)
print("TUNING_VIBLE 테스트 실행 (PostgreSQL)")
print("=" * 80)

# PostgreSQL에서 전체 데이터 조회
result = generate_backtest_report(
    trial_id=None,  # 전체 데이터
    sinks=["log"]
)

if result.get('status') == 'success':
    print(f"\n✅ 총점: {result.get('total_score', 0):.1f}/100")
    print(f"✅ 거래 수: {result.get('metrics', {}).get('total_trades', 0)}건")
elif result.get('status') == 'no_data':
    print("\n⚠️  거래 데이터 없음")
else:
    print(f"\n❌ 오류: {result.get('error')}")
