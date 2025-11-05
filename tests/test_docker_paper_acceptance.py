#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker Paper 수용 테스트

10분 구동 후 다음을 확인:
1. FlowGuardian 이벤트 emit 동작
2. 스냅샷 생성
3. PostgreSQL 연결
4. Redis 사용 (websocket_collector)
5. 로그 생성
"""

import unittest
import sys
import os
from datetime import datetime

# 프로젝트 루트 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestDockerPaperAcceptance(unittest.TestCase):
    """Docker Paper 수용 테스트"""
    
    def test_01_monitoring_imports(self):
        """monitoring 패키지 import 테스트"""
        try:
            from monitoring import FlowGuardian, init_guardian
            from monitoring.performance_monitor import (
                calculate_performance_scores,
                get_performance_report,
                backfill_stats,
                connection_stats,
                system_monitor,
                queue_health,
                latency_tracker
            )
            from monitoring.telemetry_profiler import (
                performance,
                telemetry_profiler,
                measure_time,
                start_monitoring,
                stop_monitoring
            )
            print("✅ monitoring 패키지 import 성공")
        except Exception as e:
            self.fail(f"❌ monitoring 패키지 import 실패: {e}")
    
    def test_02_analytics_imports(self):
        """analytics 패키지 import 테스트"""
        try:
            from analytics.trade_analyzer import TradeAnalyzer
            from analytics.strategy_evaluator import StrategyEvaluator
            from analytics.report_generator import ReportGenerator
            print("✅ analytics 패키지 import 성공")
        except Exception as e:
            self.fail(f"❌ analytics 패키지 import 실패: {e}")
    
    def test_03_execution_engine_imports(self):
        """execution/engine.py import 테스트 (FlowGuardian 통합)"""
        try:
            # engine.py는 FlowGuardian을 사용하므로 import 확인
            from execution.engine import Engine
            print("✅ execution/engine.py import 성공 (FlowGuardian 통합)")
        except Exception as e:
            self.fail(f"❌ execution/engine.py import 실패: {e}")
    
    def test_04_websocket_collector_imports(self):
        """collectors/websocket_collector.py import 테스트 (Redis 사용)"""
        try:
            from collectors.websocket_collector import WebSocketCollector
            print("✅ collectors/websocket_collector.py import 성공 (Redis 사용)")
        except Exception as e:
            self.fail(f"❌ collectors/websocket_collector.py import 실패: {e}")
    
    def test_05_performance_functions(self):
        """성능 함수 동작 테스트"""
        try:
            from monitoring.performance_monitor import (
                calculate_performance_scores,
                get_performance_report
            )
            
            # 성능 점수 계산
            scores = calculate_performance_scores()
            self.assertIn('overall_score', scores)
            self.assertIn('grade', scores)
            
            # 성능 리포트 생성
            report = get_performance_report('TEST_STRATEGY')
            self.assertIsInstance(report, str)
            self.assertIn('TEST_STRATEGY', report)
            
            print(f"✅ 성능 함수 동작 확인: {scores['grade']} ({scores['overall_score']:.0f}/100)")
        except Exception as e:
            self.fail(f"❌ 성능 함수 테스트 실패: {e}")
    
    def test_06_telemetry_profiler(self):
        """telemetry_profiler 동작 테스트"""
        try:
            from monitoring.telemetry_profiler import telemetry_profiler, profile
            
            # 프로파일링 테스트
            with profile("test_event"):
                import time
                time.sleep(0.01)
            
            summary = telemetry_profiler.get_summary()
            self.assertIn('test_event', summary)
            
            print(f"✅ telemetry_profiler 동작 확인: {len(summary)}개 이벤트")
        except Exception as e:
            self.fail(f"❌ telemetry_profiler 테스트 실패: {e}")
    
    def test_07_backfill_stats(self):
        """BackfillStats 동작 테스트"""
        try:
            from monitoring.performance_monitor import backfill_stats
            
            # 백필 통계 기록
            backfill_stats.record_gap("BTCUSDT")
            backfill_stats.record_recovery("BTCUSDT", recovered=5, failed=0)
            
            report = backfill_stats.get_report()
            self.assertEqual(report['total_gaps'], 1)
            self.assertEqual(report['total_recovered'], 5)
            
            print(f"✅ BackfillStats 동작 확인: {report}")
        except Exception as e:
            self.fail(f"❌ BackfillStats 테스트 실패: {e}")
    
    def test_08_connection_stats(self):
        """ConnectionStats 동작 테스트"""
        try:
            from monitoring.performance_monitor import connection_stats
            
            # 연결 통계 기록
            connection_stats.record_connect()
            connection_stats.record_heartbeat()
            connection_stats.record_disconnect("test_disconnect")
            
            report = connection_stats.get_report()
            self.assertEqual(report['total_connects'], 1)
            self.assertEqual(report['total_disconnects'], 1)
            
            print(f"✅ ConnectionStats 동작 확인: {report}")
        except Exception as e:
            self.fail(f"❌ ConnectionStats 테스트 실패: {e}")
    
    def test_09_queue_health(self):
        """QueueHealth 동작 테스트"""
        try:
            from monitoring.performance_monitor import queue_health
            
            # 큐 상태 기록
            queue_health.record_sample("candle_queue", size=50, maxsize=100, drops=0)
            
            report = queue_health.get_report("candle_queue")
            self.assertEqual(report['size'], 50)
            self.assertEqual(report['maxsize'], 100)
            
            print(f"✅ QueueHealth 동작 확인: {report}")
        except Exception as e:
            self.fail(f"❌ QueueHealth 테스트 실패: {e}")
    
    def test_10_latency_tracker(self):
        """LatencyTracker 동작 테스트"""
        try:
            from monitoring.performance_monitor import latency_tracker
            
            # 레이턴시 기록
            latency_tracker.record(10.5)
            latency_tracker.record(12.3)
            latency_tracker.record(9.8)
            
            report = latency_tracker.get_report()
            self.assertEqual(report['sample_count'], 3)
            self.assertIn('api_latency_ms_p50', report)
            
            print(f"✅ LatencyTracker 동작 확인: {report}")
        except Exception as e:
            self.fail(f"❌ LatencyTracker 테스트 실패: {e}")
    
    def test_11_log_generation(self):
        """로그 생성 확인"""
        try:
            import logging
            from common.logger import setup_logger
            
            logger = setup_logger("test_acceptance")
            logger.info("✅ 테스트 로그 생성 확인")
            
            print("✅ 로그 생성 확인")
        except Exception as e:
            self.fail(f"❌ 로그 생성 테스트 실패: {e}")
    
    def test_12_config_loading(self):
        """설정 로딩 확인"""
        try:
            from common.config import load_config
            
            config = load_config()
            self.assertIsNotNone(config)
            self.assertIn('strategies', config)
            
            print(f"✅ 설정 로딩 확인: {len(config.get('strategies', {}))}개 전략")
        except Exception as e:
            self.fail(f"❌ 설정 로딩 테스트 실패: {e}")


if __name__ == "__main__":
    # 테스트 실행
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDockerPaperAcceptance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 결과 요약
    print("\n" + "="*70)
    print("📊 Docker Paper 수용 테스트 결과")
    print("="*70)
    print(f"총 테스트: {result.testsRun}개")
    print(f"성공: {result.testsRun - len(result.failures) - len(result.errors)}개")
    print(f"실패: {len(result.failures)}개")
    print(f"에러: {len(result.errors)}개")
    
    if result.wasSuccessful():
        print("\n✅ 모든 Docker Paper 수용 테스트 통과!")
        print("   다음 단계: Docker 환경에서 10분 구동 테스트")
        print("   - FlowGuardian 이벤트 emit 확인")
        print("   - PostgreSQL DB 연결 확인")
        print("   - Redis 사용 확인 (websocket_collector)")
        print("   - 로그 및 스냅샷 생성 확인")
    else:
        print("\n❌ 일부 테스트 실패")
        print("   import 경로 또는 환경 설정을 확인하세요.")
    
    print("="*70)
    
    # 종료 코드
    sys.exit(0 if result.wasSuccessful() else 1)
