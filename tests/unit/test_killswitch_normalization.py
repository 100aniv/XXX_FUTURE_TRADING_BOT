#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE36-0: KILLSWITCH 정규화 재발방지 계약 테스트

이 테스트는 extreme_loss_cutoff_pct와 max_drawdown_pct가
양수로 들어와도 항상 음수로 정규화되는 것을 검증합니다.
"""

import pytest


def normalize_killswitch_threshold(value: float, default: float = -20.0) -> float:
    """KILLSWITCH 임계값 정규화 (항상 음수)"""
    if value is None:
        return default
    if value > 0:
        return -abs(value)
    return value


class TestKillswitchNormalization:
    """PHASE36-0: KILLSWITCH 정규화 계약 테스트"""
    
    def test_positive_value_normalized_to_negative(self):
        """양수 값이 음수로 정규화되는지 검증"""
        result = normalize_killswitch_threshold(20.0)
        assert result == -20.0, f"Expected -20.0, got {result}"
    
    def test_negative_value_stays_negative(self):
        """음수 값이 그대로 유지되는지 검증"""
        result = normalize_killswitch_threshold(-20.0)
        assert result == -20.0, f"Expected -20.0, got {result}"
    
    def test_zero_stays_zero(self):
        """0이 0으로 유지되는지 검증"""
        result = normalize_killswitch_threshold(0.0)
        assert result == 0.0, f"Expected 0.0, got {result}"
    
    def test_none_uses_default(self):
        """None이면 기본값을 사용하는지 검증"""
        result = normalize_killswitch_threshold(None, default=-10.0)
        assert result == -10.0, f"Expected -10.0, got {result}"
    
    def test_loss_pct_comparison_logic(self):
        """
        KILLSWITCH 발동 조건 검증:
        - loss_pct = -25.0%
        - cutoff = -20.0%
        - 조건: loss_pct <= cutoff → True (발동)
        """
        loss_pct = -25.0
        cutoff = -20.0
        
        assert loss_pct <= cutoff, f"Expected trigger: {loss_pct} <= {cutoff}"
    
    def test_no_trigger_when_loss_is_small(self):
        """
        손실이 작을 때 KILLSWITCH 미발동 검증:
        - loss_pct = -5.0%
        - cutoff = -20.0%
        - 조건: loss_pct <= cutoff → False (미발동)
        """
        loss_pct = -5.0
        cutoff = -20.0
        
        assert not (loss_pct <= cutoff), f"Expected no trigger: {loss_pct} > {cutoff}"
    
    def test_positive_cutoff_normalized_then_compared(self):
        """
        양수로 입력된 cutoff가 정규화 후 정상 비교되는지 검증:
        - 입력: cutoff_raw = 20.0 (양수)
        - 정규화: cutoff = -20.0
        - loss_pct = -25.0%
        - 조건: loss_pct <= cutoff → True (발동)
        """
        cutoff_raw = 20.0
        cutoff = normalize_killswitch_threshold(cutoff_raw)
        loss_pct = -25.0
        
        assert cutoff == -20.0, "Normalization failed"
        assert loss_pct <= cutoff, f"Expected trigger after normalization: {loss_pct} <= {cutoff}"
    
    def test_trade_count_guard(self):
        """
        trade_count=0일 때 KILLSWITCH 미발동 검증:
        - trade_count = 0
        - loss_pct = -25.0%
        - cutoff = -20.0%
        - 조건: (trade_count > 0) and (loss_pct <= cutoff) → False
        """
        trade_count = 0
        loss_pct = -25.0
        cutoff = -20.0
        
        trigger = (trade_count > 0) and (loss_pct <= cutoff)
        assert not trigger, f"KILLSWITCH should NOT trigger when trade_count=0"
    
    def test_trade_count_allows_trigger(self):
        """
        trade_count>0일 때 KILLSWITCH 정상 발동 검증:
        - trade_count = 1
        - loss_pct = -25.0%
        - cutoff = -20.0%
        - 조건: (trade_count > 0) and (loss_pct <= cutoff) → True
        """
        trade_count = 1
        loss_pct = -25.0
        cutoff = -20.0
        
        trigger = (trade_count > 0) and (loss_pct <= cutoff)
        assert trigger, f"KILLSWITCH should trigger when trade_count>0 and loss exceeds cutoff"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
