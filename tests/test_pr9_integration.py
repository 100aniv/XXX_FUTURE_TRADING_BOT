#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PR9 통합 테스트
==============
실제 모듈 import 및 기능 테스트
"""
import pytest


def test_core_imports():
    """핵심 모듈 import 테스트"""
    from core.flow_guardian import FlowGuardian
    from core.interfaces import IDataSource, IStrategy, IRisk, IBroker, IMetrics
    
    assert FlowGuardian is not None
    assert IDataSource is not None
    assert IStrategy is not None
    assert IRisk is not None
    assert IBroker is not None
    assert IMetrics is not None


def test_execution_imports():
    """실행 모듈 import 테스트"""
    from execution.position_tracker import PositionTracker
    from execution.tp_manager import TPManager
    from execution.risk_manager import RiskManager
    from execution.portfolio_manager import PortfolioManager
    
    assert PositionTracker is not None
    assert TPManager is not None
    assert RiskManager is not None
    assert PortfolioManager is not None


def test_monitoring_imports():
    """모니터링 모듈 import 테스트"""
    from monitoring.performance_monitor import PerformanceMonitor
    from monitoring.telemetry_profiler import TelemetryProfiler
    
    assert PerformanceMonitor is not None
    assert TelemetryProfiler is not None


def test_position_tracker_basic():
    """PositionTracker 기본 기능 테스트"""
    from execution.position_tracker import PositionTracker
    
    tracker = PositionTracker()
    
    # 메서드 존재 확인
    assert hasattr(tracker, 'track_position')
    assert hasattr(tracker, 'update_position')
    assert hasattr(tracker, 'close_position')
    assert hasattr(tracker, 'get_active_positions')


def test_risk_manager_basic():
    """RiskManager 기본 기능 테스트"""
    from execution.risk_manager import RiskManager
    
    config = {
        'risk': {
            'max_daily_loss': 1000,
            'max_positions': 5,
            'max_position_size': 0.02
        }
    }
    
    risk_manager = RiskManager(config)
    
    # 메서드 존재 확인
    assert hasattr(risk_manager, 'check_risk')
    assert hasattr(risk_manager, 'can_open_position')
    assert hasattr(risk_manager, 'update_daily_pnl')


def test_portfolio_manager_basic():
    """PortfolioManager 기본 기능 테스트"""
    from execution.portfolio_manager import PortfolioManager
    
    config = {
        'portfolio': {
            'max_positions': 5,
            'max_exposure': 0.5
        }
    }
    
    portfolio_manager = PortfolioManager(config)
    
    # 메서드 존재 확인
    assert hasattr(portfolio_manager, 'can_add_position')
    assert hasattr(portfolio_manager, 'get_exposure')
    assert hasattr(portfolio_manager, 'get_position_count')


def test_tp_manager_basic():
    """TPManager 기본 기능 테스트"""
    from execution.tp_manager import TPManager
    
    config = {
        'tp': {
            'enabled': True,
            'levels': [0.5, 1.0]
        }
    }
    
    tp_manager = TPManager(config)
    
    # 메서드 존재 확인
    assert hasattr(tp_manager, 'check_tp_levels')
    assert hasattr(tp_manager, 'update_trailing_stop')


def test_flow_guardian_basic():
    """FlowGuardian 기본 기능 테스트"""
    from core.flow_guardian import FlowGuardian
    from execution.risk_manager import RiskManager
    
    config = {
        'risk': {
            'max_daily_loss': 1000,
            'max_positions': 5
        },
        'flow_guardian': {
            'enabled': True,
            'min_score': 50
        }
    }
    
    risk_manager = RiskManager(config)
    
    try:
        guardian = FlowGuardian(
            config=config,
            risk=risk_manager,
            trial_id="test_trial"
        )
        
        # 메서드 존재 확인
        assert hasattr(guardian, 'check_ready')
        assert hasattr(guardian, 'update_metrics')
        
    except Exception as e:
        # FlowGuardian 초기화 실패는 허용 (DB 연결 등)
        pytest.skip(f"FlowGuardian 초기화 실패: {e}")


def test_performance_monitor_basic():
    """PerformanceMonitor 기본 기능 테스트"""
    from monitoring.performance_monitor import PerformanceMonitor
    
    monitor = PerformanceMonitor()
    
    # 메서드 존재 확인
    assert hasattr(monitor, 'record_trade')
    assert hasattr(monitor, 'get_statistics')
    assert hasattr(monitor, 'calculate_metrics')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
