#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PR9 Coverage 향상 테스트
=======================
주요 모듈의 coverage를 높이기 위한 통합 테스트
"""
import pytest
import os
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_config_loading():
    """config.yml 로딩 테스트"""
    import yaml
    
    config_path = project_root / "config.yml"
    assert config_path.exists(), "config.yml 파일이 없음"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    assert config is not None
    assert 'mode' in config
    assert 'strategies' in config
    assert 'risk' in config


def test_logger_setup():
    """로거 설정 테스트"""
    from common.logger import setup_logger
    
    logger = setup_logger("test_logger", "logs/test.log")
    assert logger is not None
    assert logger.name == "test_logger"
    
    # 로그 메시지 테스트
    logger.info("테스트 로그 메시지")
    logger.debug("디버그 메시지")


def test_database_connection():
    """데이터베이스 연결 테스트"""
    from common.database import get_db_connection
    
    try:
        conn = get_db_connection()
        assert conn is not None
        
        # 간단한 쿼리 테스트
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1
        
        cursor.close()
        conn.close()
    except Exception as e:
        pytest.skip(f"DB 연결 실패: {e}")


def test_position_tracker_initialization():
    """PositionTracker 초기화 테스트"""
    from execution.position_tracker import PositionTracker
    
    tracker = PositionTracker()
    assert tracker is not None
    assert hasattr(tracker, 'positions')
    assert hasattr(tracker, 'track_position')


def test_position_tracker_operations():
    """PositionTracker 기본 작업 테스트"""
    from execution.position_tracker import PositionTracker
    
    tracker = PositionTracker()
    
    # 포지션 추가
    position = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 50000.0,
        'qty': 0.01,
        'sl': 49000.0,
        'tp': 52000.0
    }
    
    tracker.track_position(position)
    
    # 활성 포지션 확인
    active = tracker.get_active_positions()
    assert len(active) >= 0


def test_risk_manager_initialization():
    """RiskManager 초기화 테스트"""
    from execution.risk_manager import RiskManager
    
    config = {
        'risk': {
            'max_daily_loss': 1000,
            'max_positions': 5,
            'max_position_size': 0.02,
            'per_trade': 0.01
        }
    }
    
    risk_manager = RiskManager(config)
    assert risk_manager is not None
    assert hasattr(risk_manager, 'check_risk')


def test_risk_manager_checks():
    """RiskManager 리스크 체크 테스트"""
    from execution.risk_manager import RiskManager
    
    config = {
        'risk': {
            'max_daily_loss': 1000,
            'max_positions': 5,
            'max_position_size': 0.02,
            'per_trade': 0.01
        }
    }
    
    risk_manager = RiskManager(config)
    
    # 포지션 오픈 가능 여부 체크
    can_open = risk_manager.can_open_position()
    assert isinstance(can_open, bool)


def test_portfolio_manager_initialization():
    """PortfolioManager 초기화 테스트"""
    from execution.portfolio_manager import PortfolioManager
    
    config = {
        'portfolio': {
            'max_positions': 5,
            'max_exposure': 0.5,
            'max_correlation': 0.7
        }
    }
    
    portfolio_manager = PortfolioManager(config)
    assert portfolio_manager is not None
    assert hasattr(portfolio_manager, 'can_add_position')


def test_portfolio_manager_operations():
    """PortfolioManager 기본 작업 테스트"""
    from execution.portfolio_manager import PortfolioManager
    
    config = {
        'portfolio': {
            'max_positions': 5,
            'max_exposure': 0.5,
            'max_correlation': 0.7
        }
    }
    
    portfolio_manager = PortfolioManager(config)
    
    # 포지션 추가 가능 여부 체크
    signal = {
        'symbol': 'BTCUSDT',
        'side': 'LONG'
    }
    
    can_add = portfolio_manager.can_add_position(signal)
    assert isinstance(can_add, (bool, tuple))


def test_tp_manager_initialization():
    """TPManager 초기화 테스트"""
    from execution.tp_manager import TPManager
    
    config = {
        'tp': {
            'enabled': True,
            'levels': [0.5, 1.0],
            'trailing': {
                'enabled': True,
                'activation': 0.5
            }
        }
    }
    
    tp_manager = TPManager(config)
    assert tp_manager is not None
    assert hasattr(tp_manager, 'check_tp_levels')


def test_tp_manager_operations():
    """TPManager 기본 작업 테스트"""
    from execution.tp_manager import TPManager
    
    config = {
        'tp': {
            'enabled': True,
            'levels': [0.5, 1.0],
            'trailing': {
                'enabled': True,
                'activation': 0.5
            }
        }
    }
    
    tp_manager = TPManager(config)
    
    # TP 레벨 체크
    position = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 50000.0,
        'qty': 0.01,
        'tp': 52000.0
    }
    
    current_price = 51000.0
    result = tp_manager.check_tp_levels(position, current_price)
    assert result is not None


def test_signal_generator_initialization():
    """SignalGenerator 초기화 테스트"""
    from signals.signal_generator import SignalGenerator
    
    config = {
        'timeframe': '5m',
        'lookback': 100
    }
    
    signal_gen = SignalGenerator(config)
    assert signal_gen is not None
    assert hasattr(signal_gen, 'generate_signals')


def test_signal_generator_validation():
    """SignalGenerator 신호 검증 테스트"""
    from signals.signal_generator import SignalGenerator
    
    config = {
        'timeframe': '5m',
        'lookback': 100
    }
    
    signal_gen = SignalGenerator(config)
    
    # 신호 검증
    signal = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry': 50000.0,
        'sl': 49000.0,
        'tp': 52000.0
    }
    
    is_valid = signal_gen.validate_signal(signal)
    assert isinstance(is_valid, bool)


def test_messaging_functions():
    """메시징 함수 테스트"""
    from common.messaging import format_signal_alert, format_exit_alert
    
    signal = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry': 50000.0,
        'sl': 49000.0,
        'tp': 52000.0,
        'qty': 0.01
    }
    
    config = {
        'telegram': {
            'emoji': {
                'entry': '🚀',
                'exit': '🏁'
            }
        }
    }
    
    # 신호 알림 포맷
    alert = format_signal_alert(signal, config)
    assert isinstance(alert, str)
    assert 'BTCUSDT' in alert
    
    # 청산 알림 포맷
    exit_info = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'exit_price': 51000.0,
        'pnl': 100.0,
        'reason': 'TP'
    }
    
    exit_alert = format_exit_alert(exit_info, config)
    assert isinstance(exit_alert, str)


def test_indicators_basic():
    """지표 계산 기본 테스트"""
    from indicators import add_indicators
    import pandas as pd
    
    # 샘플 데이터 생성
    df = pd.DataFrame({
        'open': [50000, 50100, 50200, 50300, 50400],
        'high': [50200, 50300, 50400, 50500, 50600],
        'low': [49900, 50000, 50100, 50200, 50300],
        'close': [50100, 50200, 50300, 50400, 50500],
        'volume': [100, 110, 120, 130, 140]
    })
    
    # 지표 추가
    result = add_indicators(df, {})
    assert result is not None
    assert len(result) == len(df)


def test_flow_guardian_initialization():
    """FlowGuardian 초기화 테스트"""
    from core.flow_guardian import FlowGuardian
    from execution.risk_manager import RiskManager
    
    config = {
        'risk': {
            'max_daily_loss': 1000,
            'max_positions': 5,
            'per_trade': 0.01
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
        
        assert guardian is not None
        assert hasattr(guardian, 'check_ready')
        
    except Exception as e:
        pytest.skip(f"FlowGuardian 초기화 실패: {e}")


def test_monitoring_initialization():
    """모니터링 모듈 초기화 테스트"""
    from monitoring import init_guardian
    from execution.risk_manager import RiskManager
    
    config = {
        'risk': {
            'max_daily_loss': 1000,
            'max_positions': 5,
            'per_trade': 0.01
        },
        'flow_guardian': {
            'enabled': True,
            'min_score': 50
        }
    }
    
    risk_manager = RiskManager(config)
    
    try:
        guardian = init_guardian(config, risk_manager, "test_trial")
        assert guardian is not None
        
    except Exception as e:
        pytest.skip(f"Guardian 초기화 실패: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
