#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE17 Portfolio Budget SSOT 단위 테스트
==========================================

테스트 시나리오:
1. Portfolio Manager: get_available_budget() 메서드
2. Position Sizer: available_budget 파라미터 처리
3. Budget Cap 적용 및 로그
4. 통합 테스트: Portfolio + Position Sizer

⭐ PHASE17 V6: Budget SSOT 구현 검증
"""
import sys
import os
import pytest

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock 함수 정의 (import 오류 방지)
def mock_setup_logger(name, log_type="trading"):
    """로거 Mock"""
    import logging
    return logging.getLogger(name)

# common.logger를 mock으로 대체
class MockLoggerModule:
    def setup_logger(self, name, log_type="trading"):
        import logging
        return logging.getLogger(name)

class MockCalculationsModule:
    def position_size(self, entry, sl, equity, risk_frac):
        """Mock position_size function"""
        risk_usdt = equity * risk_frac
        stop_distance = abs(entry - sl)
        if stop_distance == 0:
            return 0.0, 0.0
        qty = risk_usdt / stop_distance
        return qty, risk_usdt

class MockMessagingModule:
    def tg(self, *args, **kwargs):
        """Mock Telegram function"""
        pass
    
    def send_telegram(self, *args, **kwargs):
        """Mock send_telegram function"""
        pass

sys.modules['common.logger'] = MockLoggerModule()
sys.modules['common.messaging'] = MockMessagingModule()
sys.modules['common.calculations'] = MockCalculationsModule()

# 이제 execution 모듈 import
try:
    from execution.position_sizer import PositionSizer
    from execution.portfolio_manager import PortfolioManager
except ImportError as e:
    pytest.skip(f"Import error: {e}", allow_module_level=True)


# ============================================================
# Test Fixtures
# ============================================================

@pytest.fixture
def base_config():
    """기본 설정"""
    return {
        'capital': {'initial': 50000},
        'risk': {
            'per_trade': 0.003,
            'max_positions': 3,
            'max_exposure_per_symbol': 0.35,
            'leverage_cap': 50,
            'liq_buffer_multiple_of_SL': 4,
            'margin_ratio': 0.01
        },
        'leverage': {
            'default': 2,
            'min': 2,
            'max': 50
        },
        'position_sizing': {
            'min_position_value': 100,
            'max_position_value': 15000,
            'min_position_notional': 100,
            'max_position_notional': 15000,
            'quality_weight_min': 0.7,
            'quality_weight_max': 1.3,
            'multi_position_scaling': True,
            'exposure_reduction_factor': 0.95,
            'allow_partial_entry': True,
            'context_scaling': {
                'enabled': True,
                'atr_low_pct': 0.004,
                'atr_high_pct': 0.02,
                'low_vol_mult': 1.2,
                'high_vol_mult': 0.7,
                'neutral_mult': 1.0
            }
        },
        'portfolio': {
            'max_strategy_positions': 5,
            'max_total_exposure': 0.95,
            'symbol_cooldown_seconds': 90,
            'budget': {
                'default_allocation': 0.25,  # 25%
                'strategy_allocation': {
                    'scalping': 0.25  # 25%
                }
            }
        }
    }


@pytest.fixture
def portfolio_manager(base_config):
    """PortfolioManager 인스턴스 (backtest 모드: load_existing=False)"""
    return PortfolioManager(base_config, load_existing=False)


@pytest.fixture
def position_sizer(base_config):
    """PositionSizer 인스턴스"""
    return PositionSizer(base_config)


# ============================================================
# Test 1: PortfolioManager Budget 계산
# ============================================================

def test_calculate_strategy_budget(portfolio_manager):
    """
    Scenario: 전략별 예산 계산
    - equity = 50,000
    - scalping allocation = 25%
    Expected: budget = 12,500
    """
    budget = portfolio_manager.calculate_strategy_budget('scalping')
    
    expected = 50000 * 0.25
    assert budget == expected
    assert budget == 12500


def test_calculate_strategy_budget_default(portfolio_manager):
    """
    Scenario: 기본 예산 (strategy_allocation에 없는 전략)
    - equity = 50,000
    - default_allocation = 25%
    Expected: budget = 12,500
    """
    budget = portfolio_manager.calculate_strategy_budget('unknown_strategy')
    
    expected = 50000 * 0.25
    assert budget == expected


def test_get_used_budget_empty(portfolio_manager):
    """
    Scenario: 포지션 없음
    Expected: used_budget = 0
    """
    used = portfolio_manager._get_used_budget('scalping')
    assert used == 0.0


def test_get_used_budget_with_positions(portfolio_manager):
    """
    Scenario: 포지션 2개 ($5k, $4k)
    Expected: used_budget = 9,000
    """
    # 포지션 추가 (Mock)
    portfolio_manager.positions['BTCUSDT'] = [
        {
            'strategy': 'scalping',
            'status': 'OPEN',
            'position_value': 5000.0,
            'side': 'LONG'
        }
    ]
    portfolio_manager.positions['ETHUSDT'] = [
        {
            'strategy': 'scalping',
            'status': 'OPEN',
            'position_value': 4000.0,
            'side': 'SHORT'
        }
    ]
    
    used = portfolio_manager._get_used_budget('scalping')
    assert used == 9000.0


def test_get_available_budget_full(portfolio_manager):
    """
    Scenario: 포지션 없음 (전액 사용 가능)
    Expected: available = total = 12,500
    """
    available = portfolio_manager.get_available_budget('scalping')
    
    total_budget = 50000 * 0.25
    assert available == total_budget
    assert available == 12500


def test_get_available_budget_partial(portfolio_manager):
    """
    Scenario: $9k 사용 중
    Expected: available = 12,500 - 9,000 = 3,500
    """
    # 포지션 추가
    portfolio_manager.positions['BTCUSDT'] = [
        {
            'strategy': 'scalping',
            'status': 'OPEN',
            'position_value': 9000.0,
            'side': 'LONG'
        }
    ]
    
    available = portfolio_manager.get_available_budget('scalping')
    assert available == 3500.0


def test_get_available_budget_exhausted(portfolio_manager):
    """
    Scenario: 예산 소진 ($12.5k 사용 중)
    Expected: available = 0
    """
    # 포지션 추가
    portfolio_manager.positions['BTCUSDT'] = [
        {
            'strategy': 'scalping',
            'status': 'OPEN',
            'position_value': 12500.0,
            'side': 'LONG'
        }
    ]
    
    available = portfolio_manager.get_available_budget('scalping')
    assert available == 0.0


def test_get_available_budget_over(portfolio_manager):
    """
    Scenario: 예산 초과 ($13k 사용 중, 이론상 불가하지만 테스트)
    Expected: available = 0 (음수 방지)
    """
    # 포지션 추가
    portfolio_manager.positions['BTCUSDT'] = [
        {
            'strategy': 'scalping',
            'status': 'OPEN',
            'position_value': 13000.0,
            'side': 'LONG'
        }
    ]
    
    available = portfolio_manager.get_available_budget('scalping')
    assert available == 0.0


# ============================================================
# Test 2: PositionSizer Budget Cap
# ============================================================

def test_position_sizer_no_budget_cap(position_sizer):
    """
    Scenario: Budget Cap 없음 (available_budget=None)
    - entry = 100,000, sl = 98,000
    - Risk-based calculation: ~$9,000
    Expected: position_value ~$9,000 (Budget Cap 미적용)
    """
    signal = {
        'entry_price': 100000.0,
        'sl_price': 98000.0,
        'confidence': 0.8
    }
    
    qty, meta = position_sizer.calculate(signal, available_budget=None)
    
    assert qty > 0
    assert 'position_value' in meta
    assert meta['budget_capped'] is False
    assert meta['available_budget'] is None


def test_position_sizer_budget_sufficient(position_sizer):
    """
    Scenario: Budget 충분 (available_budget=15,000)
    - entry = 100,000, sl = 98,000
    - Risk-based calculation: ~$9,000
    - available_budget = 15,000
    Expected: position_value ~$9,000 (Budget Cap 미적용)
    """
    signal = {
        'entry_price': 100000.0,
        'sl_price': 98000.0,
        'confidence': 0.8
    }
    
    qty, meta = position_sizer.calculate(signal, available_budget=15000.0)
    
    assert qty > 0
    assert meta['position_value'] < 15000
    assert meta['budget_capped'] is False
    assert meta['available_budget'] == 15000.0


def test_position_sizer_budget_cap_applied(position_sizer):
    """
    Scenario: Budget 부족 (Cap 적용)
    - entry = 100,000, sl = 98,000
    - Risk-based calculation: ~$9,000
    - available_budget = 3,000
    Expected: position_value = 3,000 (Budget Cap 적용!)
    """
    signal = {
        'entry_price': 100000.0,
        'sl_price': 98000.0,
        'confidence': 0.8
    }
    
    qty, meta = position_sizer.calculate(signal, available_budget=3000.0)
    
    assert qty > 0
    assert meta['position_value'] == 3000.0
    assert meta['budget_capped'] is True
    assert meta['available_budget'] == 3000.0


def test_position_sizer_budget_exhausted(position_sizer):
    """
    Scenario: Budget 소진 (available_budget=0)
    - entry = 100,000, sl = 98,000
    - available_budget = 0
    Expected: qty = 0 (below_min_value)
    """
    signal = {
        'entry_price': 100000.0,
        'sl_price': 98000.0,
        'confidence': 0.8
    }
    
    qty, meta = position_sizer.calculate(signal, available_budget=0.0)
    
    assert qty == 0.0
    assert meta['reason'] == 'below_min_value'


def test_position_sizer_budget_below_min(position_sizer):
    """
    Scenario: Budget 너무 작음 (min_position_value=100 미만)
    - entry = 100,000, sl = 98,000
    - available_budget = 50
    Expected: qty = 0 (below_min_value)
    """
    signal = {
        'entry_price': 100000.0,
        'sl_price': 98000.0,
        'confidence': 0.8
    }
    
    qty, meta = position_sizer.calculate(signal, available_budget=50.0)
    
    assert qty == 0.0
    assert meta['reason'] == 'below_min_value'


# ============================================================
# Test 3: 통합 테스트 (Portfolio + Position Sizer)
# ============================================================

def test_integration_first_entry(portfolio_manager, position_sizer):
    """
    Scenario: 첫 Entry (Budget 충분)
    - total_budget = 12,500
    - available_budget = 12,500
    - requested = ~9,000
    Expected: Entry 성공 ($9k)
    """
    available = portfolio_manager.get_available_budget('scalping')
    assert available == 12500.0
    
    signal = {
        'entry_price': 100000.0,
        'sl_price': 98000.0,
        'confidence': 0.8
    }
    
    qty, meta = position_sizer.calculate(signal, available_budget=available)
    
    assert qty > 0
    assert meta['position_value'] < 12500
    assert meta['budget_capped'] is False


def test_integration_second_entry_with_cap(portfolio_manager, position_sizer):
    """
    Scenario: 두 번째 Entry (Budget 부족, Cap 적용)
    - total_budget = 12,500
    - used = 9,000
    - available = 3,500
    - requested = ~8,500
    Expected: Entry 성공 ($3,500, Budget Cap)
    """
    # 첫 번째 포지션 추가
    portfolio_manager.positions['BTCUSDT'] = [
        {
            'strategy': 'scalping',
            'status': 'OPEN',
            'position_value': 9000.0,
            'side': 'LONG'
        }
    ]
    
    available = portfolio_manager.get_available_budget('scalping')
    assert available == 3500.0
    
    signal = {
        'entry_price': 100000.0,
        'sl_price': 98000.0,
        'confidence': 0.8
    }
    
    qty, meta = position_sizer.calculate(signal, available_budget=available)
    
    assert qty > 0
    assert meta['position_value'] == 3500.0
    assert meta['budget_capped'] is True


def test_integration_third_entry_blocked(portfolio_manager, position_sizer):
    """
    Scenario: 세 번째 Entry (Budget 소진, Entry 차단)
    - total_budget = 12,500
    - used = 12,500
    - available = 0
    Expected: qty = 0 (below_min_value)
    """
    # 첫 번째 + 두 번째 포지션 추가
    portfolio_manager.positions['BTCUSDT'] = [
        {
            'strategy': 'scalping',
            'status': 'OPEN',
            'position_value': 9000.0,
            'side': 'LONG'
        }
    ]
    portfolio_manager.positions['ETHUSDT'] = [
        {
            'strategy': 'scalping',
            'status': 'OPEN',
            'position_value': 3500.0,
            'side': 'SHORT'
        }
    ]
    
    available = portfolio_manager.get_available_budget('scalping')
    assert available == 0.0
    
    signal = {
        'entry_price': 100000.0,
        'sl_price': 98000.0,
        'confidence': 0.8
    }
    
    qty, meta = position_sizer.calculate(signal, available_budget=available)
    
    assert qty == 0.0
    assert meta['reason'] == 'below_min_value'


# ============================================================
# Test 4: V5/V5b 실패 케이스 재현
# ============================================================

def test_v5_failure_case_reproduced(portfolio_manager, position_sizer):
    """
    V5 실패 케이스 재현:
    - equity = 50,000
    - total_budget = 12,500 (25%)
    - used = 10,000 (기존 포지션 2개)
    - available = 2,500
    - Position Sizer가 $14,700 요청 (Budget 무시)
    - Portfolio Manager가 BLOCK
    
    V6 개선:
    - Position Sizer가 available_budget=2,500 받음
    - Budget Cap 적용: $14,700 → $2,500
    - Portfolio Manager PASS
    """
    # 기존 포지션 추가
    portfolio_manager.positions['BTCUSDT'] = [
        {
            'strategy': 'scalping',
            'status': 'OPEN',
            'position_value': 5000.0,
            'side': 'LONG'
        },
        {
            'strategy': 'scalping',
            'status': 'OPEN',
            'position_value': 5000.0,
            'side': 'SHORT'
        }
    ]
    
    available = portfolio_manager.get_available_budget('scalping')
    assert available == 2500.0
    
    # V5에서는 available_budget 없이 호출 → $14,700 계산
    signal = {
        'entry_price': 100000.0,
        'sl_price': 98000.0,
        'confidence': 0.8
    }
    
    qty_v5, meta_v5 = position_sizer.calculate(signal, available_budget=None)
    # V5 결과: position_value > 2,500 → Portfolio Manager BLOCK
    
    # V6에서는 available_budget 전달 → Budget Cap
    qty_v6, meta_v6 = position_sizer.calculate(signal, available_budget=available)
    
    # V6 결과: Budget Cap 적용
    assert meta_v6['position_value'] == 2500.0
    assert meta_v6['budget_capped'] is True
    
    # Portfolio Manager 검증
    can_open, reason = portfolio_manager.can_open_position(
        symbol='ETHUSDT',
        strategy='scalping',
        position_value=meta_v6['position_value'],
        side='LONG'
    )
    
    # V6: PASS (10,000 + 2,500 = 12,500 ≤ 12,500)
    assert can_open is True


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
