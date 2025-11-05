#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
테스트: PostgreSQL 기반 백테스트 리포트 생성

주의:
- SQLite 지원 중단
- PostgreSQL trading.trades 테이블에서 데이터 조회
- analytics.report_generator 사용
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 환경변수 로드
load_dotenv()

from analytics.report_generator import generate_backtest_report

report_path = project_root / 'reports' / 'test_backtest_report.html'

print("\n" + "="*80)
print("🎯 PostgreSQL 기반 백테스트 리포트 테스트")
print("="*80)
print(f"📄 리포트 경로: {report_path}")
print(f"🛢️  DB: PostgreSQL (trading.trades)")
print()

try:
    # PostgreSQL에서 백테스트 리포트 생성
    result = generate_backtest_report(
        trial_id=None,  # 전체 데이터 (필터링 없음)
        table_name="trades",
        schema="trading",
        output_file=str(report_path),
        sinks=["log", "html", "json"]
    )
    
    if result.get("status") == "success":
        print(f"✅ 리포트 생성 완료")
        print(f"   - HTML: {result.get('html_path')}")
        print(f"   - JSON: {result.get('json_path')}")
        print(f"   - 총점: {result.get('total_score', 0):.1f}/100")
        print(f"   - 거래 수: {result.get('metrics', {}).get('total_trades', 0)}건")
    elif result.get("status") == "no_data":
        print("⚠️  거래 데이터 없음 - PostgreSQL trading.trades 테이블에 데이터를 추가하세요.")
    else:
        print(f"❌ 오류: {result.get('error')}")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("✅ 테스트 완료")
    print("="*80 + "\n")
    
except Exception as e:
    print(f"\n❌ 예외 발생: {e}")
    import traceback
    traceback.print_exc()
    print("\n💡 팅: PostgreSQL이 실행 중인지 확인하세요 (docker-compose up -d postgres)")
    sys.exit(1)
