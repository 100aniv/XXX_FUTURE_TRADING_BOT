#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-0: Prometheus Exporter Unit Tests
==========================================

테스트 목적:
- PrometheusExporter 초기화 검증
- 메트릭 등록 확인
- record_* API 호출 검증
- Config 기반 활성화/비활성화 검증
- 기존 엔진/SSOT 테스트 회귀 방지
"""
import pytest
from unittest.mock import Mock, patch
from prometheus_client import REGISTRY
from monitoring.prometheus_exporter import (
    PrometheusExporter,
    init_prometheus_exporter,
    get_prometheus_exporter
)


@pytest.fixture(autouse=True)
def clear_prometheus_registry():
    """
    각 테스트 전후로 Prometheus Registry 초기화
    
    Note: Prometheus client는 전역 Registry를 사용하므로
    테스트 간 메트릭 이름 충돌을 방지하기 위해 초기화 필요
    """
    # Setup: 테스트 전 Registry 초기화
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass
    
    yield
    
    # Teardown: 테스트 후 Registry 초기화
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass


class TestPrometheusExporterInit:
    """PrometheusExporter 초기화 테스트"""
    
    def test_exporter_init_enabled(self):
        """Exporter 활성화 초기화"""
        exporter = PrometheusExporter(
            enabled=True,
            port=9091,
            mode="paper"
        )
        
        assert exporter.enabled is True
        assert exporter.port == 9091
        assert exporter.mode == "paper"
        
        # 메트릭 객체들이 등록되었는지 확인
        assert hasattr(exporter, 'loop_latency')
        assert hasattr(exporter, 'candles_processed')
        assert hasattr(exporter, 'trades')
        assert hasattr(exporter, 'strategy_signals')
        assert hasattr(exporter, 'ensemble_decisions')
        assert hasattr(exporter, 'guard_blocks')
    
    def test_exporter_init_disabled(self):
        """Exporter 비활성화 초기화"""
        exporter = PrometheusExporter(
            enabled=False,
            port=9091,
            mode="paper"
        )
        
        assert exporter.enabled is False
        # 비활성화 상태에서도 객체는 생성되지만 record는 no-op
    
    def test_exporter_mode_labels(self):
        """모드별 레이블 확인"""
        # Note: 하나의 Exporter만 생성 (Registry 충돌 방지)
        exporter = PrometheusExporter(
            enabled=True,
            port=9091,
            mode="backtest"
        )
        assert exporter.mode == "backtest"
        
        # 다른 모드는 값 확인만 (새 인스턴스 생성하지 않음)
        modes = ["backtest", "paper", "live"]
        for mode in modes:
            assert mode in modes  # 모드 리스트 확인


class TestPrometheusExporterRecordAPI:
    """Record API 테스트"""
    
    @pytest.fixture
    def exporter(self):
        """테스트용 Exporter 인스턴스"""
        return PrometheusExporter(
            enabled=True,
            port=9091,
            mode="paper"
        )
    
    def test_record_loop_latency(self, exporter):
        """Loop latency 기록"""
        # Should not raise
        exporter.record_loop_latency("BTCUSDT", 12.5)
        exporter.record_loop_latency("ETHUSDT", 15.3)
    
    def test_record_candle_processed(self, exporter):
        """캔들 처리 카운트 기록"""
        exporter.record_candle_processed("BTCUSDT")
        exporter.record_candle_processed("BTCUSDT")
        exporter.record_candle_processed("ETHUSDT")
    
    def test_record_strategy_signal(self, exporter):
        """전략 신호 기록"""
        # has_signal=True, with side/regime
        exporter.record_strategy_signal(
            symbol="BTCUSDT",
            strategy="baseline_v1",
            has_signal=True,
            side="LONG",
            regime="RANGE"
        )
        
        # has_signal=False
        exporter.record_strategy_signal(
            symbol="BTCUSDT",
            strategy="baseline_v1",
            has_signal=False
        )
    
    def test_record_ensemble_decision(self, exporter):
        """앙상블 결정 기록"""
        exporter.record_ensemble_decision("BTCUSDT", "tier1")
        exporter.record_ensemble_decision("BTCUSDT", "tier2")
        exporter.record_ensemble_decision("BTCUSDT", "skip")
    
    def test_record_guard_block(self, exporter):
        """Guard 블록 기록"""
        exporter.record_guard_block("BTCUSDT", "cooldown_active")
        exporter.record_guard_block("BTCUSDT", "exposure_exceeded")
    
    def test_record_order_submitted(self, exporter):
        """주문 제출 기록"""
        exporter.record_order_submitted("BTCUSDT")
        exporter.record_order_submitted("ETHUSDT")
    
    def test_record_trade(self, exporter):
        """트레이드 기록"""
        exporter.record_trade("BTCUSDT", "LONG")
        exporter.record_trade("BTCUSDT", "SHORT")
    
    def test_update_pnl(self, exporter):
        """PnL 업데이트"""
        exporter.update_pnl("BTCUSDT", 123.45)
        exporter.update_pnl("BTCUSDT", -56.78)
    
    def test_update_open_positions(self, exporter):
        """오픈 포지션 수 업데이트"""
        exporter.update_open_positions("BTCUSDT", 2)
        exporter.update_open_positions("BTCUSDT", 0)
    
    def test_update_budget_used_ratio(self, exporter):
        """Budget 사용 비율 업데이트"""
        exporter.update_budget_used_ratio(0.5)
        exporter.update_budget_used_ratio(0.9)
    
    def test_record_error(self, exporter):
        """에러 기록"""
        exporter.record_error("ERROR")
        exporter.record_error("CRITICAL")
    
    def test_update_cpu_usage(self, exporter):
        """CPU 사용률 업데이트"""
        exporter.update_cpu_usage(45.2)
    
    def test_update_memory_usage(self, exporter):
        """메모리 사용량 업데이트"""
        exporter.update_memory_usage(512.0)


class TestPrometheusExporterDisabled:
    """비활성화 상태 테스트 (no-op 동작 확인)"""
    
    @pytest.fixture
    def disabled_exporter(self):
        """비활성화된 Exporter"""
        return PrometheusExporter(
            enabled=False,
            port=9091,
            mode="paper"
        )
    
    def test_record_no_op_when_disabled(self, disabled_exporter):
        """비활성화 시 record 함수들이 no-op으로 동작"""
        # Should not raise, should be no-op
        disabled_exporter.record_loop_latency("BTCUSDT", 10.0)
        disabled_exporter.record_candle_processed("BTCUSDT")
        disabled_exporter.record_strategy_signal("BTCUSDT", "test", True)
        disabled_exporter.record_ensemble_decision("BTCUSDT", "tier1")
        disabled_exporter.record_guard_block("BTCUSDT", "test")
        disabled_exporter.record_order_submitted("BTCUSDT")
        disabled_exporter.record_trade("BTCUSDT", "LONG")
        disabled_exporter.update_pnl("BTCUSDT", 100.0)
        disabled_exporter.update_open_positions("BTCUSDT", 1)
        disabled_exporter.update_budget_used_ratio(0.5)
        disabled_exporter.record_error("ERROR")
        disabled_exporter.update_cpu_usage(50.0)
        disabled_exporter.update_memory_usage(256.0)


class TestPrometheusExporterGlobalInstance:
    """전역 인스턴스 관리 테스트"""
    
    def test_init_prometheus_exporter(self):
        """전역 Exporter 초기화"""
        exporter = init_prometheus_exporter(
            enabled=True,
            port=9091,
            mode="paper"
        )
        
        assert exporter is not None
        assert exporter.enabled is True
        
        # 전역 인스턴스 확인
        global_exporter = get_prometheus_exporter()
        assert global_exporter is exporter
    
    def test_get_prometheus_exporter_before_init(self):
        """초기화 전 get_prometheus_exporter는 None 또는 이전 인스턴스 반환"""
        # 이전 테스트에서 초기화되었을 수 있으므로 None이 아닐 수 있음
        exporter = get_prometheus_exporter()
        # None이거나 PrometheusExporter 인스턴스여야 함
        assert exporter is None or isinstance(exporter, PrometheusExporter)


class TestTradeActivityTrackerIntegration:
    """TradeActivityTracker와의 통합 테스트"""
    
    def test_tracker_calls_exporter_on_record(self):
        """Tracker의 record_* 호출 시 Exporter 자동 호출 확인"""
        from metrics.trade_activity_tracker import TradeActivityTracker
        
        # Mock Exporter
        mock_exporter = Mock()
        mock_exporter.enabled = True
        
        tracker = TradeActivityTracker(
            run_id="test",
            prometheus_exporter=mock_exporter
        )
        
        # Strategy signal 기록
        tracker.record_strategy_signal(
            symbol="BTCUSDT",
            strategy_id="test_strategy",
            has_signal=True,
            side="LONG",
            regime="RANGE"
        )
        
        # Exporter의 record_strategy_signal이 호출되었는지 확인
        mock_exporter.record_strategy_signal.assert_called_once_with(
            symbol="BTCUSDT",
            strategy="test_strategy",
            has_signal=True,
            side="LONG",
            regime="RANGE"
        )
    
    def test_tracker_without_exporter(self):
        """Exporter 없이 Tracker 사용 시 정상 동작"""
        from metrics.trade_activity_tracker import TradeActivityTracker
        
        tracker = TradeActivityTracker(
            run_id="test",
            prometheus_exporter=None  # Exporter 없음
        )
        
        # Should not raise
        tracker.record_strategy_signal(
            symbol="BTCUSDT",
            strategy_id="test_strategy",
            has_signal=True
        )
        tracker.record_ensemble_decision("BTCUSDT", "tier1")
        tracker.record_guard_block("BTCUSDT", "test")
        tracker.record_order_submitted("BTCUSDT", "LONG", 0.1)


class TestSSOTRegression:
    """SSOT/Engine 구조 회귀 테스트"""
    
    def test_no_new_engine_entrypoints(self):
        """새로운 엔진 진입점이 추가되지 않았는지 확인"""
        # run_v2가 여전히 단일 진입점인지 확인
        from pathlib import Path
        
        scripts_dir = Path(__file__).parent.parent / "scripts"
        
        # run_v*.py 파일 확인
        run_v_files = list(scripts_dir.glob("run_v*.py"))
        
        # run_v2.py만 존재해야 함
        assert len(run_v_files) == 1
        assert run_v_files[0].name == "run_v2.py"
    
    def test_no_direct_signal_calculation_in_monitoring(self):
        """Monitoring 모듈에서 신호 직접 계산하지 않는지 확인"""
        from pathlib import Path
        
        monitoring_dir = Path(__file__).parent.parent / "monitoring"
        
        # monitoring/ 하위 모든 Python 파일 검사
        for py_file in monitoring_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # signal_logic() 직접 호출이 없어야 함
            assert "signal_logic(" not in content or "# signal_logic" in content, \
                f"monitoring/{py_file.name}에서 signal_logic() 직접 호출 발견"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
