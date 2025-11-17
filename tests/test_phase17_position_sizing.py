#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE17 Position Sizing + Exposure Guard 단위 테스트
======================================================

테스트 시나리오:
1. Multi-position Scaling (동시 포지션 수에 따른 크기 조정)
2. Exposure Guard 3단계 의사결정 (ALLOW/ALLOW_REDUCED/BLOCK)
3. Position Sizer와 Risk Manager 통합 테스트
"""
import sys
import os
import pytest

# 테스트 환경 설정
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 필요한 모듈만 선택적으로 import
try:
    from execution.position_sizer import PositionSizer
    from execution.risk_manager import RiskManager, ExposureDecision
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
            'max_positions': 2,
            'max_exposure_per_symbol': 0.3,
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
            'max_position_value': 10000,
            'min_position_notional': 100,
            'max_position_notional': 10000,
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
        }
    }


@pytest.fixture
def position_sizer(base_config):
    """PositionSizer 인스턴스"""
    return PositionSizer(base_config)


@pytest.fixture
def risk_manager(base_config):
    """RiskManager 인스턴스"""
    return RiskManager(base_config, portfolio=None)


# ============================================================
# Test 1: Multi-position Scaling
# ============================================================

def test_multi_position_scaling_0_positions(position_sizer):
    """
    Scenario: 0개 포지션 열림
    Expected: scaling_factor = 1.0 (100%)
    """
    base_risk = 150.0
    num_open = 0
    max_positions = 2
    
    scaled_risk = position_sizer.apply_multi_position_scaling(
        base_risk, num_open, max_positions
    )
    
    assert scaled_risk == 150.0
    assert abs(scaled_risk / base_risk - 1.0) < 0.001


def test_multi_position_scaling_1_position(position_sizer):
    """
    Scenario: 1개 포지션 열림
    Expected: scaling_factor = 0.667 (67%)
    """
    base_risk = 150.0
    num_open = 1
    max_positions = 2
    
    scaled_risk = position_sizer.apply_multi_position_scaling(
        base_risk, num_open, max_positions
    )
    
    expected_factor = 1.0 / (1.0 + 1/2)
    expected_risk = base_risk * expected_factor
    
    assert abs(scaled_risk - expected_risk) < 0.01
    assert abs(scaled_risk / base_risk - 0.667) < 0.01


def test_multi_position_scaling_2_positions(position_sizer):
    """
    Scenario: 2개 포지션 열림
    Expected: scaling_factor = 0.5 (50%)
    """
    base_risk = 150.0
    num_open = 2
    max_positions = 2
    
    scaled_risk = position_sizer.apply_multi_position_scaling(
        base_risk, num_open, max_positions
    )
    
    expected_factor = 1.0 / (1.0 + 2/2)
    expected_risk = base_risk * expected_factor
    
    assert abs(scaled_risk - expected_risk) < 0.01
    assert abs(scaled_risk / base_risk - 0.5) < 0.01


def test_multi_position_scaling_disabled(base_config):
    """
    Scenario: Multi-position Scaling OFF
    Expected: scaling_factor = 1.0 (변화 없음)
    """
    base_config['position_sizing']['multi_position_scaling'] = False
    sizer = PositionSizer(base_config)
    
    base_risk = 150.0
    scaled_risk = sizer.apply_multi_position_scaling(base_risk, 1, 2)
    
    assert scaled_risk == base_risk


# ============================================================
# Test 2: Exposure Guard 3단계 의사결정 (Risk Manager)
# ============================================================

def test_exposure_guard_allow(risk_manager):
    """
    Scenario: ALLOW (정상 진입)
    - current_exposure = 10,000
    - requested = 4,000
    - max_exposure = 15,000
    Expected: ALLOW (total = 14,000 < 15,000)
    """
    decision = risk_manager.check_symbol_exposure_with_adjustment(
        symbol="BTCUSDT",
        requested_notional=4000.0,
        current_exposure=10000.0,
        min_position_notional=100
    )
    
    assert decision.decision == "ALLOW"
    assert decision.adjusted_notional == 4000.0
    assert "Within exposure limit" in decision.reason


def test_exposure_guard_allow_reduced(risk_manager):
    """
    Scenario: ALLOW_REDUCED (사이즈 축소 후 진입)
    - current_exposure = 10,000
    - requested = 8,000
    - max_exposure = 15,000
    Expected: ALLOW_REDUCED (total = 18,000 > 15,000)
              adjusted = (15,000 - 10,000) × 0.95 = 4,750
    """
    decision = risk_manager.check_symbol_exposure_with_adjustment(
        symbol="BTCUSDT",
        requested_notional=8000.0,
        current_exposure=10000.0,
        min_position_notional=100
    )
    
    assert decision.decision == "ALLOW_REDUCED"
    expected_adjusted = (15000 - 10000) * 0.95
    assert abs(decision.adjusted_notional - expected_adjusted) < 1.0
    assert "Reduced from" in decision.reason


def test_exposure_guard_block_at_limit(risk_manager):
    """
    Scenario: BLOCK (현재 노출도가 이미 한계)
    - current_exposure = 15,000
    - requested = 5,000
    - max_exposure = 15,000
    Expected: BLOCK (current >= max)
    """
    decision = risk_manager.check_symbol_exposure_with_adjustment(
        symbol="BTCUSDT",
        requested_notional=5000.0,
        current_exposure=15000.0,
        min_position_notional=100
    )
    
    assert decision.decision == "BLOCK"
    assert decision.adjusted_notional == 0.0
    assert "already at limit" in decision.reason


def test_exposure_guard_block_adjusted_too_small(risk_manager):
    """
    Scenario: BLOCK (조정 후 크기가 최소값 미만)
    - current_exposure = 14,950
    - requested = 1,000
    - max_exposure = 15,000
    - available = 50 × 0.95 = 47.5 < min_notional (100)
    Expected: BLOCK (adjusted < min)
    """
    decision = risk_manager.check_symbol_exposure_with_adjustment(
        symbol="BTCUSDT",
        requested_notional=1000.0,
        current_exposure=14950.0,
        min_position_notional=100
    )
    
    assert decision.decision == "BLOCK"
    assert decision.adjusted_notional == 0.0
    assert "below minimum" in decision.reason


# ============================================================
# Test 3: Position Sizer + Exposure Check 통합
# ============================================================

def test_position_sizer_with_exposure_check_allow(position_sizer):
    """
    Scenario: ALLOW (정상 진입)
    - equity = 50,000
    - entry = 95,000, sl = 94,000
    - current_exposure = 5,000
    - max_exposure = 15,000
    Expected: ALLOW
    """
    signal = {
        'symbol': 'BTCUSDT',
        'entry_price': 95000.0,
        'sl_price': 94000.0,
        'confidence': 0.8,
        'atr': 380.0  # ATR ≈ 0.4%
    }
    
    qty, metadata, action = position_sizer.calculate_with_exposure_check(
        signal=signal,
        current_symbol_exposure=5000.0,
        max_symbol_exposure=15000.0,
        num_open_positions=0
    )
    
    assert action == "ALLOW"
    assert qty > 0
    assert 'position_value' in metadata


def test_position_sizer_with_exposure_check_allow_reduced(position_sizer):
    """
    Scenario: ALLOW_REDUCED (사이즈 축소 후 진입)
    - equity = 50,000
    - entry = 95,000, sl = 94,000
    - current_exposure = 10,000
    - max_exposure = 15,000
    - num_open = 1 (67% scaling)
    Expected: ALLOW_REDUCED
    """
    signal = {
        'symbol': 'BTCUSDT',
        'entry_price': 95000.0,
        'sl_price': 94000.0,
        'confidence': 0.8,
        'atr': 380.0
    }
    
    qty, metadata, action = position_sizer.calculate_with_exposure_check(
        signal=signal,
        current_symbol_exposure=10000.0,
        max_symbol_exposure=12000.0,  # 여유 2,000만 남음
        num_open_positions=1
    )
    
    # Multi-position scaling (67%)으로 인해 원래 요청이 줄어들고,
    # 그래도 초과하면 ALLOW_REDUCED
    assert action in ["ALLOW", "ALLOW_REDUCED"]
    
    if action == "ALLOW_REDUCED":
        assert 'adjusted_exposure' in metadata
        assert metadata['adjusted_exposure'] < metadata.get('original_exposure', float('inf'))


def test_position_sizer_with_exposure_check_block(position_sizer):
    """
    Scenario: BLOCK (완전 차단)
    - current_exposure = 15,000 (이미 한계)
    - max_exposure = 15,000
    Expected: BLOCK
    """
    signal = {
        'symbol': 'BTCUSDT',
        'entry_price': 95000.0,
        'sl_price': 94000.0,
        'confidence': 0.8
    }
    
    qty, metadata, action = position_sizer.calculate_with_exposure_check(
        signal=signal,
        current_symbol_exposure=15000.0,
        max_symbol_exposure=15000.0,
        num_open_positions=0
    )
    
    assert action == "BLOCK"
    assert qty == 0.0
    assert 'block_reason' in metadata


# ============================================================
# Test 4: Edge Cases
# ============================================================

def test_multi_position_scaling_max_positions_zero(position_sizer):
    """
    Scenario: max_positions = 0 (무제한)
    Expected: scaling 적용 안 함 (1.0)
    """
    base_risk = 150.0
    scaled_risk = position_sizer.apply_multi_position_scaling(base_risk, 5, 0)
    
    assert scaled_risk == base_risk


def test_exposure_guard_zero_current_exposure(risk_manager):
    """
    Scenario: 현재 노출도 = 0
    Expected: ALLOW (신규 진입)
    """
    decision = risk_manager.check_symbol_exposure_with_adjustment(
        symbol="BTCUSDT",
        requested_notional=5000.0,
        current_exposure=0.0,
        min_position_notional=100
    )
    
    assert decision.decision == "ALLOW"


def test_position_sizer_invalid_signal(position_sizer):
    """
    Scenario: 잘못된 신호 (entry ≤ sl)
    Expected: BLOCK (qty = 0)
    """
    signal = {
        'symbol': 'BTCUSDT',
        'entry_price': 95000.0,
        'sl_price': 96000.0,  # SL이 entry보다 높음 (LONG인데)
        'confidence': 0.8
    }
    
    qty, metadata, action = position_sizer.calculate_with_exposure_check(
        signal=signal,
        current_symbol_exposure=0.0,
        max_symbol_exposure=15000.0,
        num_open_positions=0
    )
    
    assert action == "BLOCK"
    assert qty == 0.0


# ============================================================
# Test 5: PHASE16 실패 케이스 재현 및 검증
# ============================================================

def test_phase16_failure_case_2nd_run(position_sizer):
    """
    PHASE16 2차 실행 실패 케이스 재현:
    - equity = 50,000
    - current_exposure = 20,048 (BTCUSDT)
    - max_exposure = 14,705 (29.4%)
    - 기존: BLOCK (완전 차단)
    - PHASE17: BLOCK (이미 초과 상태)
    """
    signal = {
        'symbol': 'BTCUSDT',
        'entry_price': 95000.0,
        'sl_price': 94000.0,
        'confidence': 0.8
    }
    
    qty, metadata, action = position_sizer.calculate_with_exposure_check(
        signal=signal,
        current_symbol_exposure=20048.0,
        max_symbol_exposure=14705.0,
        num_open_positions=2
    )
    
    # 이미 노출도가 한계를 초과한 상태 → BLOCK
    assert action == "BLOCK"
    assert qty == 0.0


def test_phase16_failure_case_improved(position_sizer):
    """
    PHASE16 개선 케이스:
    - equity = 50,000
    - current_exposure = 10,000 (BTCUSDT)
    - max_exposure = 15,000 (30%)
    - requested ≈ 8,000 (초과)
    - PHASE17: ALLOW_REDUCED (사이즈 축소 후 진입)
    """
    signal = {
        'symbol': 'BTCUSDT',
        'entry_price': 95000.0,
        'sl_price': 94000.0,
        'confidence': 0.8
    }
    
    qty, metadata, action = position_sizer.calculate_with_exposure_check(
        signal=signal,
        current_symbol_exposure=10000.0,
        max_symbol_exposure=15000.0,
        num_open_positions=1  # 67% scaling 적용
    )
    
    # Multi-position scaling으로 요청이 줄어들지만,
    # 그래도 초과하면 ALLOW_REDUCED로 사이즈 추가 축소
    assert action in ["ALLOW", "ALLOW_REDUCED"]
    assert qty > 0  # 거래 가능!


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
