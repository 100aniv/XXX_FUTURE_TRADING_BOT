#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitoring & Analytics 모듈 스모크 테스트

목적:
- import 정상 동작 확인
- FlowGuardian Facade 기본 메서드 호출 확인
- snapshot() 스키마 검증
"""

import unittest
import sys
import os

# 프로젝트 루트 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestMonitoringAnalytics(unittest.TestCase):
    """Monitoring & Analytics 모듈 테스트"""
    
    def test_01_import_monitoring(self):
        """monitoring 패키지 import 테스트"""
        try:
            from monitoring import MonitoringFacade, init_monitoring
            from monitoring.performance_monitor import (
                SystemPerformanceMonitor,
                QueueHealth,
                LatencyTracker
            )
            from monitoring.telemetry_profiler import TelemetryProfiler
            print("✅ monitoring 패키지 import 성공")
        except Exception as e:
            self.fail(f"❌ monitoring import 실패: {e}")
    
    def test_02_import_analytics(self):
        """analytics 패키지 import 테스트"""
        try:
            from analytics.trade_analyzer import TradeAnalyzer
            from analytics.strategy_evaluator import StrategyEvaluator
            from analytics.report_generator import ReportGenerator
            print("✅ analytics 패키지 import 성공")
        except Exception as e:
            self.fail(f"❌ analytics import 실패: {e}")
    
    def test_03_flowguardian_init(self):
        """MonitoringFacade 초기화 테스트"""
        from monitoring import MonitoringFacade
        
        config = {
            "monitoring": {
                "flowguardian": {
                    "enabled": True,
                    "sample_interval_sec": 10,
                    "sinks": ["log"],
                    "alerts": {
                        "cpu_pct_warning": 85,
                        "cpu_pct_critical": 95
                    }
                }
            }
        }
        
        guardian = MonitoringFacade(config)
        self.assertTrue(guardian.enabled)
        self.assertEqual(guardian.sample_interval_sec, 10)
        print("✅ FlowGuardian 초기화 성공")
    
    def test_04_emit_event(self):
        """emit_event 동작 테스트"""
        from monitoring import MonitoringFacade
        import time
        
        config = {"monitoring": {"flowguardian": {"enabled": True}}}
        guardian = MonitoringFacade(config)
        
        # 이벤트 발행
        guardian.emit_event({
            "type": "system.performance",
            "ts": time.time(),
            "payload": {"cpu_pct": 10, "mem_mb": 100}
        })
        
        # 캐시 확인
        self.assertIn("system", guardian.mon_cache)
        self.assertEqual(guardian.mon_cache["system"].get("cpu_pct"), 10)
        print("✅ emit_event 동작 확인")
    
    def test_05_sample_system(self):
        """sample_system 동작 테스트"""
        from monitoring import MonitoringFacade
        
        config = {"monitoring": {"flowguardian": {"enabled": True}}}
        guardian = MonitoringFacade(config)
        
        # 시스템 샘플링
        perf = guardian.sample_system()
        
        # 필수 키 확인
        self.assertIn("cpu_pct", perf)
        self.assertIn("mem_mb", perf)
        self.assertIn("avg_latency_ms", perf)
        self.assertIn("score", perf)
        print(f"✅ sample_system 동작 확인: {perf}")
    
    def test_06_snapshot(self):
        """스냅샷 스키마 검증"""
        from monitoring import MonitoringFacade
        import time
        
        config = {"monitoring": {"flowguardian": {"enabled": True}}}
        guardian = MonitoringFacade(config)
        
        # 이벤트 발행
        guardian.emit_event({
            "type": "system.performance",
            "ts": time.time(),
            "payload": {"cpu_pct": 15, "mem_mb": 200}
        })
        
        # 스냅샷 생성
        snapshot = guardian.snapshot()
        
        # 스키마 검증
        self.assertIn("ts", snapshot)
        self.assertIn("monitoring", snapshot)
        self.assertIn("analytics", snapshot)
        
        # monitoring 섹션
        mon = snapshot["monitoring"]
        self.assertIn("system", mon)
        self.assertIn("connection", mon)
        self.assertIn("backfill", mon)
        self.assertIn("queue", mon)
        
        # analytics 섹션
        an = snapshot["analytics"]
        self.assertIn("daily_kpis", an)
        self.assertIn("strategy_rank", an)
        
        print(f"✅ snapshot 스키마 검증 완료")
    
    def test_07_alert_if_needed(self):
        """alert_if_needed 임계값 체크 테스트"""
        from monitoring import MonitoringFacade
        import time
        
        config = {
            "monitoring": {
                "flowguardian": {
                    "enabled": True,
                    "sinks": ["log"],
                    "alerts": {
                        "cpu_pct_warning": 50,  # 낮은 임계값으로 테스트
                        "cpu_pct_critical": 80
                    }
                }
            }
        }
        guardian = MonitoringFacade(config)
        
        # 높은 CPU 이벤트 발행
        guardian.emit_event({
            "type": "system.performance",
            "ts": time.time(),
            "payload": {"cpu_pct": 60, "mem_mb": 200}
        })
        
        snapshot = guardian.snapshot()
        
        # 알림 체크 (예외 발생하지 않으면 성공)
        try:
            guardian.alert_if_needed(snapshot)
            print("✅ alert_if_needed 동작 확인")
        except Exception as e:
            self.fail(f"❌ alert_if_needed 실패: {e}")
    
    def test_08_analytics_modules(self):
        """analytics 모듈 기본 동작 테스트"""
        from analytics.trade_analyzer import TradeAnalyzer
        from analytics.strategy_evaluator import StrategyEvaluator
        from analytics.report_generator import ReportGenerator
        
        # TradeAnalyzer
        analyzer = TradeAnalyzer()
        kpis = analyzer.get_daily_kpis()
        self.assertIn("trades", kpis)
        self.assertIn("win_rate", kpis)
        
        # StrategyEvaluator
        evaluator = StrategyEvaluator()
        comparisons = evaluator.compare_strategies()
        self.assertIsInstance(comparisons, list)
        
        # ReportGenerator
        generator = ReportGenerator()
        result = generator.generate_daily_report(kpis, sinks=["log"])
        self.assertIn("status", result)
        
        print("✅ analytics 모듈 동작 확인")


if __name__ == "__main__":
    # 테스트 실행
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMonitoringAnalytics)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 결과 요약
    print("\n" + "="*60)
    print("📊 테스트 결과 요약")
    print("="*60)
    print(f"총 테스트: {result.testsRun}개")
    print(f"성공: {result.testsRun - len(result.failures) - len(result.errors)}개")
    print(f"실패: {len(result.failures)}개")
    print(f"에러: {len(result.errors)}개")
    print("="*60)
    
    # 종료 코드
    sys.exit(0 if result.wasSuccessful() else 1)
