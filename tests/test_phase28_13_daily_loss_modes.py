#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-13: Daily Loss Guard Modes Unit Test
==============================================
Testing off/soft/hard modes
"""
import pytest
from unittest.mock import Mock, MagicMock
from execution.risk_manager import RiskManager


@pytest.fixture
def mock_portfolio():
    """Mock PortfolioManager"""
    portfolio = Mock()
    portfolio.get_daily_pnl = Mock(return_value=0.0)
    portfolio.initial_equity = 50000
    return portfolio


@pytest.fixture
def mock_activity_tracker():
    """Mock TradeActivityTracker"""
    tracker = Mock()
    tracker.record_guard_block = Mock()
    return tracker


def test_daily_loss_mode_off(mock_portfolio, mock_activity_tracker):
    """Test 1: mode='off' → 손실 발생해도 차단하지 않음"""
    config = {
        'mode': 'backtest',
        'capital': {'initial': 50000},
        'risk': {
            'max_positions': 3,
            'max_exposure_per_symbol': 0.3,
            'daily_loss': {
                'mode': 'off',
                'soft_limit_pct': 0.05
            }
        }
    }
    
    rm = RiskManager(config, portfolio=mock_portfolio, activity_tracker=mock_activity_tracker)
    
    # 큰 손실 발생 (-10%)
    mock_portfolio.get_daily_pnl.return_value = -5000.0
    
    # Signal check
    signal = {'symbol': 'BTCUSDT', 'entry_price': 100000}
    allowed, reason = rm.check_order(signal, qty=0.1, position_value=10000)
    
    # OFF 모드 → 허용되어야 함
    assert allowed is True
    assert 'Daily loss' not in reason


def test_daily_loss_mode_soft_within_limit(mock_portfolio, mock_activity_tracker):
    """Test 2: mode='soft' + 손실이 한도 이내 → 허용"""
    config = {
        'mode': 'backtest',
        'capital': {'initial': 50000},
        'risk': {
            'max_positions': 3,
            'max_exposure_per_symbol': 0.3,
            'daily_loss': {
                'mode': 'soft',
                'soft_limit_pct': 0.05  # 5% = $2,500
            },
            'enforce_daily_loss_in_backtest': True
        }
    }
    
    rm = RiskManager(config, portfolio=mock_portfolio, activity_tracker=mock_activity_tracker)
    
    # 작은 손실 (-2%)
    mock_portfolio.get_daily_pnl.return_value = -1000.0
    
    signal = {'symbol': 'BTCUSDT', 'entry_price': 100000}
    allowed, reason = rm.check_order(signal, qty=0.1, position_value=10000)
    
    # 한도 이내 → 허용
    assert allowed is True


def test_daily_loss_mode_soft_exceeds_limit(mock_portfolio, mock_activity_tracker):
    """Test 3: mode='soft' + 손실이 한도 초과 → 차단"""
    config = {
        'mode': 'backtest',
        'capital': {'initial': 50000},
        'risk': {
            'max_positions': 3,
            'max_exposure_per_symbol': 0.3,
            'daily_loss': {
                'mode': 'soft',
                'soft_limit_pct': 0.05  # 5% = $2,500
            },
            'enforce_daily_loss_in_backtest': True
        }
    }
    
    rm = RiskManager(config, portfolio=mock_portfolio, activity_tracker=mock_activity_tracker)
    
    # 큰 손실 (-6%)
    mock_portfolio.get_daily_pnl.return_value = -3000.0
    
    signal = {'symbol': 'BTCUSDT', 'entry_price': 100000}
    allowed, reason = rm.check_order(signal, qty=0.1, position_value=10000)
    
    # 한도 초과 → 차단
    assert allowed is False
    assert 'SOFT' in reason
    
    # Telemetry 호출 확인
    mock_activity_tracker.record_guard_block.assert_called_with('BTCUSDT', 'GUARD_DAILY_LOSS_LIMIT_SOFT')


def test_daily_loss_mode_hard_exceeds_hard_limit(mock_portfolio, mock_activity_tracker):
    """Test 4: mode='hard' + 손실이 hard 한도 초과 → 차단"""
    config = {
        'mode': 'backtest',
        'capital': {'initial': 50000},
        'risk': {
            'max_positions': 3,
            'max_exposure_per_symbol': 0.3,
            'daily_loss': {
                'mode': 'hard',
                'soft_limit_pct': 0.05,  # 5% = $2,500
                'hard_limit_pct': 0.10   # 10% = $5,000
            },
            'enforce_daily_loss_in_backtest': True
        }
    }
    
    rm = RiskManager(config, portfolio=mock_portfolio, activity_tracker=mock_activity_tracker)
    
    # 매우 큰 손실 (-12%)
    mock_portfolio.get_daily_pnl.return_value = -6000.0
    
    signal = {'symbol': 'BTCUSDT', 'entry_price': 100000}
    allowed, reason = rm.check_order(signal, qty=0.1, position_value=10000)
    
    # Hard 한도 초과 → 차단
    assert allowed is False
    assert 'HARD' in reason
    
    # Telemetry 호출 확인
    mock_activity_tracker.record_guard_block.assert_called_with('BTCUSDT', 'GUARD_DAILY_LOSS_LIMIT_HARD')


def test_daily_loss_profit_not_blocked(mock_portfolio, mock_activity_tracker):
    """Test 5: 이익 발생 시 차단하지 않음 (버그 수정 검증)"""
    config = {
        'mode': 'backtest',
        'capital': {'initial': 50000},
        'risk': {
            'max_positions': 3,
            'max_exposure_per_symbol': 0.3,
            'daily_loss': {
                'mode': 'soft',
                'soft_limit_pct': 0.05
            },
            'enforce_daily_loss_in_backtest': True
        }
    }
    
    rm = RiskManager(config, portfolio=mock_portfolio, activity_tracker=mock_activity_tracker)
    
    # 큰 이익 (+10%)
    mock_portfolio.get_daily_pnl.return_value = 5000.0
    
    signal = {'symbol': 'BTCUSDT', 'entry_price': 100000}
    allowed, reason = rm.check_order(signal, qty=0.1, position_value=10000)
    
    # 이익 → 항상 허용
    assert allowed is True
    
    # Telemetry 호출 안 됨
    mock_activity_tracker.record_guard_block.assert_not_called()


def test_backwards_compatibility_max_daily_loss_pct(mock_portfolio, mock_activity_tracker):
    """Test 6: 기존 max_daily_loss_pct 설정 → soft 모드로 자동 변환"""
    config = {
        'mode': 'backtest',
        'capital': {'initial': 50000},
        'risk': {
            'max_positions': 3,
            'max_exposure_per_symbol': 0.3,
            'max_daily_loss_pct': 5.0  # 레거시 설정 (5%)
        }
    }
    
    rm = RiskManager(config, portfolio=mock_portfolio, activity_tracker=mock_activity_tracker)
    
    # Backwards compatibility 확인
    assert rm.daily_loss_mode == 'soft'
    assert rm.daily_loss_soft_limit_pct == 0.05
    assert rm.daily_loss_limit == rm.daily_loss_soft_limit


def test_check_daily_loss_limit_method_off_mode(mock_portfolio):
    """Test 7: check_daily_loss_limit() 메서드 - OFF 모드"""
    config = {
        'mode': 'backtest',
        'capital': {'initial': 50000},
        'risk': {
            'max_positions': 3,
            'max_exposure_per_symbol': 0.3,
            'daily_loss': {
                'mode': 'off'
            }
        }
    }
    
    rm = RiskManager(config, portfolio=mock_portfolio)
    
    # 큰 손실
    mock_portfolio.get_daily_pnl.return_value = -10000.0
    
    # OFF 모드 → 항상 True
    assert rm.check_daily_loss_limit() is True


def test_check_daily_loss_limit_method_soft_mode(mock_portfolio):
    """Test 8: check_daily_loss_limit() 메서드 - SOFT 모드"""
    config = {
        'mode': 'backtest',
        'capital': {'initial': 50000},
        'risk': {
            'max_positions': 3,
            'max_exposure_per_symbol': 0.3,
            'daily_loss': {
                'mode': 'soft',
                'soft_limit_pct': 0.05
            }
        }
    }
    
    rm = RiskManager(config, portfolio=mock_portfolio)
    
    # 한도 이내
    mock_portfolio.get_daily_pnl.return_value = -1000.0
    assert rm.check_daily_loss_limit() is True
    
    # 한도 초과
    mock_portfolio.get_daily_pnl.return_value = -3000.0
    assert rm.check_daily_loss_limit() is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
