#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 5 최종 검증 테스트

1. DB 연결 테스트 (PostgreSQL)
2. analytics 모듈 실제 쿼리 테스트
3. monitoring 모듈 동작 확인
"""

import sys
import os

# 프로젝트 루트 추가
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# .env 파일 로드 (DATABASE_URL 등)
from dotenv import load_dotenv
load_dotenv()


def test_db_connection():
    """PostgreSQL 연결 테스트"""
    print("\n" + "="*60)
    print("1️⃣  PostgreSQL 연결 테스트")
    print("="*60)
    try:
        from common.database import test_db_connection
        result = test_db_connection()
        if result:
            print("✅ PostgreSQL 연결 성공")
            return True
        else:
            print("❌ PostgreSQL 연결 실패")
            return False
    except Exception as e:
        print(f"❌ PostgreSQL 연결 에러: {e}")
        return False


def test_analytics_trade_analyzer():
    """TradeAnalyzer 실제 쿼리 테스트"""
    print("\n" + "="*60)
    print("2️⃣  TradeAnalyzer 쿼리 테스트")
    print("="*60)
    try:
        from analytics.trade_analyzer import TradeAnalyzer
        from datetime import datetime, timedelta
        
        analyzer = TradeAnalyzer()
        
        # 오늘 날짜로 테스트
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"📅 테스트 날짜: {today}")
        
        # 일일 KPI 조회
        daily_kpis = analyzer.get_daily_kpis(today)
        print(f"✅ get_daily_kpis() 호출 성공")
        print(f"   - 거래: {daily_kpis['trades']}건")
        print(f"   - 승률: {daily_kpis['win_rate']:.2%}")
        print(f"   - PnL: ${daily_kpis['pnl_sum']:.2f}")
        
        # 주간 KPI 조회
        monday = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d")
        weekly_kpis = analyzer.get_weekly_kpis(monday)
        print(f"✅ get_weekly_kpis() 호출 성공")
        print(f"   - 거래: {weekly_kpis['trades']}건")
        print(f"   - 승률: {weekly_kpis['win_rate']:.2%}")
        print(f"   - PnL: ${weekly_kpis['pnl_sum']:.2f}")
        
        return True
    except Exception as e:
        print(f"❌ TradeAnalyzer 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_analytics_strategy_evaluator():
    """StrategyEvaluator 실제 쿼리 테스트"""
    print("\n" + "="*60)
    print("3️⃣  StrategyEvaluator 쿼리 테스트")
    print("="*60)
    try:
        from analytics.strategy_evaluator import StrategyEvaluator
        from datetime import datetime, timedelta
        
        evaluator = StrategyEvaluator()
        
        # 최근 7일 데이터로 테스트
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        print(f"📅 테스트 기간: {start_date} ~ {end_date}")
        
        # 전략 비교
        comparisons = evaluator.compare_strategies(
            strategies=None,  # 전체 전략
            start_date=start_date,
            end_date=end_date
        )
        
        print(f"✅ compare_strategies() 호출 성공")
        print(f"   - 전략 수: {len(comparisons)}개")
        
        if comparisons:
            for comp in comparisons[:3]:  # 상위 3개만 출력
                print(f"   - {comp['rank']}위: {comp['strategy']} (점수: {comp['kpi_score']:.1f}, 거래: {comp['trades']}건)")
        else:
            print("   - 데이터 없음 (정상: 초기 상태)")
        
        return True
    except Exception as e:
        print(f"❌ StrategyEvaluator 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_monitoring_modules():
    """monitoring 모듈 동작 확인"""
    print("\n" + "="*60)
    print("4️⃣  Monitoring 모듈 동작 확인")
    print("="*60)
    try:
        from monitoring.performance_monitor import (
            calculate_performance_scores,
            get_performance_report,
            latency_tracker
        )
        
        # 성능 점수 계산
        scores = calculate_performance_scores()
        print(f"✅ calculate_performance_scores() 호출 성공")
        print(f"   - 종합 점수: {scores['overall_score']:.0f}/100 ({scores['grade']})")
        print(f"   - CPU: {scores['cpu_percent']:.1f}%")
        print(f"   - 메모리: {scores['memory_mb']:.0f}MB")
        print(f"   - 레이턴시: {scores['latency_ms']:.1f}ms")
        
        # 성능 리포트 생성
        report = get_performance_report('TEST')
        print(f"✅ get_performance_report() 호출 성공")
        print(f"   - {report}")
        
        # 레이턴시 추적 테스트
        latency_tracker.record(10.5)
        latency_tracker.record(15.3)
        latency_tracker.record(12.1)
        latency_report = latency_tracker.get_report()
        print(f"✅ latency_tracker 동작 확인")
        print(f"   - P50: {latency_report['api_latency_ms_p50']:.1f}ms")
        print(f"   - 샘플: {latency_report['sample_count']}개")
        
        return True
    except Exception as e:
        print(f"❌ Monitoring 모듈 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_flowguardian():
    """FlowGuardian 이벤트 확인"""
    print("\n" + "="*60)
    print("5️⃣  FlowGuardian 이벤트 확인")
    print("="*60)
    try:
        from monitoring import MonitoringFacade, init_monitoring
        from common.config_loader import load_config
        
        # config 로드
        config = load_config()
        print(f"✅ config 로드 성공")
        
        # MonitoringFacade 초기화
        monitoring = init_monitoring(config)
        print(f"✅ MonitoringFacade 초기화 성공")
        
        # 테스트 이벤트 emit
        test_event = {
            "type": "test.event",
            "ts": int(__import__('time').time()),
            "payload": {"message": "Phase 5 테스트"}
        }
        monitoring.emit_event(test_event)
        print(f"✅ MonitoringFacade 이벤트 emit 성공")
        
        # 스냅샷 생성 테스트
        snapshot = monitoring.snapshot()
        print(f"✅ MonitoringFacade 스냅샷 생성 성공 (ts: {snapshot['ts']})")
        
        return True
    except Exception as e:
        print(f"❌ FlowGuardian 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 실행"""
    print("\n" + "="*70)
    print("🔍 Phase 5 Monitoring & Analytics 최종 검증 테스트")
    print("="*70)
    
    results = []
    
    # 1. DB 연결 테스트
    results.append(("DB 연결", test_db_connection()))
    
    # 2. analytics 모듈 테스트
    results.append(("TradeAnalyzer", test_analytics_trade_analyzer()))
    results.append(("StrategyEvaluator", test_analytics_strategy_evaluator()))
    
    # 3. monitoring 모듈 테스트
    results.append(("Monitoring 모듈", test_monitoring_modules()))
    
    # 4. FlowGuardian 테스트
    results.append(("FlowGuardian", test_flowguardian()))
    
    # 결과 요약
    print("\n" + "="*70)
    print("📊 테스트 결과 요약")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{status}: {name}")
    
    print("\n" + "="*70)
    print(f"총 {total}개 테스트 중 {passed}개 통과 ({passed/total*100:.1f}%)")
    print("="*70)
    
    if passed == total:
        print("\n✅ Phase 5 최종 검증 완료!")
        print("   모든 모듈이 정상 동작합니다.")
    else:
        print(f"\n⚠️  {total - passed}개 테스트 실패")
        print("   실패한 항목을 확인하세요.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
