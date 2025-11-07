#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
회귀 테스트: Import 경로 검증

common/performance.py 제거 후 모든 import가 정상 동작하는지 확인
"""

import unittest
import sys
import os

# 프로젝트 루트 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestRegressionImports(unittest.TestCase):
    """Import 경로 회귀 테스트"""
    
    def test_01_engine_imports(self):
        """execution/engine.py import 테스트"""
        try:
            # engine.py의 import들이 정상 동작하는지 확인
            from monitoring.telemetry_profiler import start_monitoring
            from monitoring.performance_monitor import calculate_performance_scores
            from monitoring import MonitoringFacade, init_monitoring
            print("✅ engine.py import 정상")
        except Exception as e:
            self.fail(f"❌ engine.py import 실패: {e}")
    
    def test_02_messaging_imports(self):
        """common/messaging.py import 테스트"""
        try:
            from monitoring.performance_monitor import get_performance_report
            print("✅ messaging.py import 정상")
        except Exception as e:
            self.fail(f"❌ messaging.py import 실패: {e}")
    
    def test_03_websocket_collector_imports(self):
        """collectors/websocket_collector.py import 테스트"""
        try:
            from monitoring.performance_monitor import backfill_stats, connection_stats
            print("✅ websocket_collector.py import 정상")
        except Exception as e:
            self.fail(f"❌ websocket_collector.py import 실패: {e}")
    
    def test_04_no_common_performance(self):
        """common/performance.py가 삭제되었는지 확인"""
        import os
        perf_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'common',
            'performance.py'
        )
        self.assertFalse(
            os.path.exists(perf_path),
            "❌ common/performance.py가 아직 존재합니다"
        )
        print("✅ common/performance.py 삭제 확인")
    
    def test_05_monitoring_exports(self):
        """monitoring 패키지 export 확인"""
        try:
            from monitoring.performance_monitor import (
                calculate_performance_scores,
                get_performance_report,
                BackfillStats,
                ConnectionStats,
                SystemPerformanceMonitor,
                QueueHealth,
                LatencyTracker,
                backfill_stats,
                connection_stats,
                system_monitor,
                queue_health,
                latency_tracker
            )
            print("✅ monitoring.performance_monitor exports 정상")
        except Exception as e:
            self.fail(f"❌ monitoring.performance_monitor export 실패: {e}")
    
    def test_06_telemetry_exports(self):
        """telemetry_profiler 패키지 export 확인"""
        try:
            from monitoring.telemetry_profiler import (
                PerformanceMonitor,
                TelemetryProfiler,
                performance,
                telemetry_profiler,
                measure_time,
                start_monitoring,
                stop_monitoring,
                get_performance_summary,
                export_performance,
                print_performance_summary
            )
            print("✅ monitoring.telemetry_profiler exports 정상")
        except Exception as e:
            self.fail(f"❌ monitoring.telemetry_profiler export 실패: {e}")
    
    def test_07_function_compatibility(self):
        """함수 호출 호환성 테스트"""
        try:
            from monitoring.performance_monitor import calculate_performance_scores, get_performance_report
            from monitoring.telemetry_profiler import start_monitoring, stop_monitoring
            
            # 점수 계산
            scores = calculate_performance_scores()
            self.assertIn('overall_score', scores)
            self.assertIn('grade', scores)
            
            # 리포트 생성
            report = get_performance_report('TEST')
            self.assertIsInstance(report, str)
            self.assertIn('TEST', report)
            
            # 모니터링 시작/중지
            start_monitoring(interval=1.0)
            stop_monitoring()
            
            print("✅ 함수 호출 호환성 정상")
        except Exception as e:
            self.fail(f"❌ 함수 호출 실패: {e}")
    
    def test_08_global_instances(self):
        """전역 인스턴스 접근 테스트"""
        try:
            from monitoring.performance_monitor import (
                backfill_stats,
                connection_stats,
                system_monitor,
                queue_health,
                latency_tracker
            )
            from monitoring.telemetry_profiler import performance, telemetry_profiler
            
            # 인스턴스 타입 확인
            self.assertIsNotNone(backfill_stats)
            self.assertIsNotNone(connection_stats)
            self.assertIsNotNone(system_monitor)
            self.assertIsNotNone(queue_health)
            self.assertIsNotNone(latency_tracker)
            self.assertIsNotNone(performance)
            self.assertIsNotNone(telemetry_profiler)
            
            print("✅ 전역 인스턴스 접근 정상")
        except Exception as e:
            self.fail(f"❌ 전역 인스턴스 접근 실패: {e}")


if __name__ == "__main__":
    # 테스트 실행
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRegressionImports)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 결과 요약
    print("\n" + "="*60)
    print("📊 회귀 테스트 결과 (Import)")
    print("="*60)
    print(f"총 테스트: {result.testsRun}개")
    print(f"성공: {result.testsRun - len(result.failures) - len(result.errors)}개")
    print(f"실패: {len(result.failures)}개")
    print(f"에러: {len(result.errors)}개")
    
    if result.wasSuccessful():
        print("\n✅ 모든 회귀 테스트 통과!")
        print("   common/performance.py 제거 후 import 경로가 정상 동작합니다.")
    else:
        print("\n❌ 일부 테스트 실패")
    
    print("="*60)
    
    # 종료 코드
    sys.exit(0 if result.wasSuccessful() else 1)
