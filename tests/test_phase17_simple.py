#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE17 간소화 테스트
======================

execution 모듈 의존성을 최소화한 PHASE17 로직 검증 테스트
"""
import pytest


# ============================================================
# Test 1: Multi-position Scaling 공식 검증
# ============================================================

def multi_position_scaling(base_risk: float, num_open: int, max_positions: int) -> float:
    """
    Multi-position Scaling 공식 (PositionSizer 로직 복제)
    
    scaling_factor = 1.0 / (1 + num_open / max_positions)
    """
    if max_positions <= 0:
        return base_risk
    scaling_factor = 1.0 / (1.0 + num_open / max_positions)
    return base_risk * scaling_factor


def test_multi_position_scaling_0_positions():
    """0개 포지션 열림 → 100% scaling"""
    result = multi_position_scaling(150.0, 0, 2)
    assert result == 150.0


def test_multi_position_scaling_1_position():
    """1개 포지션 열림 → 67% scaling"""
    result = multi_position_scaling(150.0, 1, 2)
    expected = 150.0 / 1.5  # 100USDT
    assert abs(result - expected) < 0.01


def test_multi_position_scaling_2_positions():
    """2개 포지션 열림 → 50% scaling"""
    result = multi_position_scaling(150.0, 2, 2)
    expected = 150.0 / 2.0  # 75USDT
    assert abs(result - expected) < 0.01


def test_multi_position_scaling_max_positions_zero():
    """max_positions=0 (무제한) → scaling 안 함"""
    result = multi_position_scaling(150.0, 5, 0)
    assert result == 150.0


# ============================================================
# Test 2: Exposure Guard 3단계 의사결정 로직 검증
# ============================================================

def exposure_guard_decision(
    current_exposure: float,
    requested_notional: float,
    max_exposure: float,
    min_notional: float = 100,
    reduction_factor: float = 0.95
) -> tuple:
    """
    Exposure Guard 3단계 의사결정 (RiskManager 로직 복제)
    
    Returns:
        (decision, adjusted_notional, reason)
        - decision: "ALLOW" | "ALLOW_REDUCED" | "BLOCK"
    """
    total_exposure = current_exposure + requested_notional
    
    # ALLOW: 정상 진입
    if total_exposure <= max_exposure:
        return ("ALLOW", requested_notional, "Within exposure limit")
    
    # ALLOW_REDUCED: 사이즈 축소 후 진입
    if current_exposure < max_exposure:
        available = max_exposure - current_exposure
        adjusted = available * reduction_factor
        
        if adjusted >= min_notional:
            return ("ALLOW_REDUCED", adjusted, f"Reduced from ${requested_notional:.2f}")
        else:
            return ("BLOCK", 0.0, f"Adjusted size (${adjusted:.2f}) below minimum")
    
    # BLOCK: 완전 차단
    return ("BLOCK", 0.0, "Per-symbol exposure already at limit")


def test_exposure_guard_allow():
    """ALLOW: 정상 진입"""
    decision, adjusted, reason = exposure_guard_decision(
        current_exposure=10000,
        requested_notional=4000,
        max_exposure=15000
    )
    assert decision == "ALLOW"
    assert adjusted == 4000


def test_exposure_guard_allow_reduced():
    """ALLOW_REDUCED: 사이즈 축소 후 진입"""
    decision, adjusted, reason = exposure_guard_decision(
        current_exposure=10000,
        requested_notional=8000,
        max_exposure=15000
    )
    assert decision == "ALLOW_REDUCED"
    expected_adjusted = (15000 - 10000) * 0.95  # 4750
    assert abs(adjusted - expected_adjusted) < 1.0


def test_exposure_guard_block_at_limit():
    """BLOCK: 현재 노출도가 이미 한계"""
    decision, adjusted, reason = exposure_guard_decision(
        current_exposure=15000,
        requested_notional=5000,
        max_exposure=15000
    )
    assert decision == "BLOCK"
    assert adjusted == 0.0


def test_exposure_guard_block_adjusted_too_small():
    """BLOCK: 조정 후 크기가 최소값 미만"""
    decision, adjusted, reason = exposure_guard_decision(
        current_exposure=14950,
        requested_notional=1000,
        max_exposure=15000,
        min_notional=100
    )
    assert decision == "BLOCK"  # (15000 - 14950) * 0.95 = 47.5 < 100


# ============================================================
# Test 3: 통합 시나리오 (Multi-position Scaling + Exposure Guard)
# ============================================================

def test_integrated_scenario_progressive_scaling():
    """
    통합 시나리오: 동시 포지션 증가 시 크기 점진적 감소
    
    Equity: 50,000 USDT
    max_positions: 3
    max_symbol_exposure: 17,500 USDT (35%)
    base_risk: 8,000 USDT (기본 요청)
    """
    equity = 50000
    max_positions = 3
    max_symbol_exposure = equity * 0.35  # 17,500
    base_risk = 8000
    current_exposure = 0
    
    # Entry 1: 0개 열림 → 100% scaling
    scaled_risk_1 = multi_position_scaling(base_risk, 0, max_positions)
    assert abs(scaled_risk_1 - 8000) < 1  # 100%
    
    decision_1, adjusted_1, _ = exposure_guard_decision(
        current_exposure, scaled_risk_1, max_symbol_exposure
    )
    assert decision_1 == "ALLOW"
    current_exposure += adjusted_1
    
    # Entry 2: 1개 열림 → 75% scaling
    scaled_risk_2 = multi_position_scaling(base_risk, 1, max_positions)
    expected_2 = 8000 / (1 + 1/3)  # 6000
    assert abs(scaled_risk_2 - expected_2) < 1
    
    decision_2, adjusted_2, _ = exposure_guard_decision(
        current_exposure, scaled_risk_2, max_symbol_exposure
    )
    assert decision_2 == "ALLOW"
    current_exposure += adjusted_2
    
    # Entry 3: 2개 열림 → 60% scaling
    scaled_risk_3 = multi_position_scaling(base_risk, 2, max_positions)
    expected_3 = 8000 / (1 + 2/3)  # 4800
    assert abs(scaled_risk_3 - expected_3) < 1
    
    decision_3, adjusted_3, _ = exposure_guard_decision(
        current_exposure, scaled_risk_3, max_symbol_exposure
    )
    # current_exposure ≈ 14,000, requested ≈ 4,800, total ≈ 18,800 > 17,500
    # → ALLOW_REDUCED
    assert decision_3 == "ALLOW_REDUCED"
    assert adjusted_3 < scaled_risk_3


def test_integrated_scenario_phase16_failure_case():
    """
    PHASE16 실패 케이스 재현
    
    Equity: 50,000 USDT
    Current Exposure: 20,048 USDT (초과 상태)
    Max Exposure: 14,705 USDT (29.4%)
    
    Expected: BLOCK (현재 노출도가 이미 초과)
    """
    decision, adjusted, reason = exposure_guard_decision(
        current_exposure=20048,
        requested_notional=8000,
        max_exposure=14705
    )
    assert decision == "BLOCK"


def test_integrated_scenario_phase17_improvement():
    """
    PHASE17 개선 케이스
    
    Equity: 50,000 USDT
    Current Exposure: 10,000 USDT
    Max Exposure: 15,000 USDT (30%)
    Requested: 8,000 USDT (초과)
    
    Expected: ALLOW_REDUCED (사이즈 축소 후 진입)
    """
    decision, adjusted, reason = exposure_guard_decision(
        current_exposure=10000,
        requested_notional=8000,
        max_exposure=15000
    )
    assert decision == "ALLOW_REDUCED"
    expected = (15000 - 10000) * 0.95  # 4750
    assert abs(adjusted - expected) < 1.0


# ============================================================
# 실행
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
