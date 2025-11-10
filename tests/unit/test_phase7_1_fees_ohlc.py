#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE7-1 단위 테스트: 수수료 반영 + OHLC SL 체크 + Extreme Loss -20%
"""
import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest
from execution.engine import calculate_pnl
from execution.position_tracker import PositionTracker


class TestCalculatePnlWithFees:
    """calculate_pnl() 수수료 반영 테스트"""
    
    def test_long_profit_with_fees(self):
        """LONG 수익 (수수료 차감)"""
        position = {'entry': 100.0, 'qty': 1.0, 'side': 'LONG'}
        pnl = calculate_pnl(position, 100.10, fee_rate=0.0004)
        # Gross: (100.10 - 100.0) * 1.0 = 0.10
        # Fee: (100.0 + 100.10) * 1.0 * 0.0004 = 0.0804
        # Net: 0.10 - 0.0804 = 0.0196
        assert 0.019 < pnl < 0.021, f"Expected ~0.02, got {pnl}"
    
    def test_small_profit_becomes_loss_after_fees(self):
        """소액 수익 → 수수료 후 손실 전환"""
        position = {'entry': 100.0, 'qty': 1.0, 'side': 'SHORT'}
        pnl = calculate_pnl(position, 99.95, fee_rate=0.0004)
        # Gross: (100.0 - 99.95) * 1.0 = 0.05
        # Fee: (100.0 + 99.95) * 1.0 * 0.0004 = 0.0798
        # Net: 0.05 - 0.0798 = -0.0298
        assert pnl < 0, f"Expected negative, got {pnl}"
        assert -0.03 < pnl < -0.029, f"Expected ~-0.03, got {pnl}"
    
    def test_zero_profit_minus_fees(self):
        """0% 수익 = 수수료만 손실"""
        position = {'entry': 100.0, 'qty': 1.0, 'side': 'LONG'}
        pnl = calculate_pnl(position, 100.0, fee_rate=0.0004)
        # Gross: 0
        # Fee: (100.0 + 100.0) * 1.0 * 0.0004 = 0.08
        # Net: -0.08
        assert -0.081 < pnl < -0.079, f"Expected ~-0.08, got {pnl}"
    
    def test_short_profit_with_fees(self):
        """SHORT 수익 (수수료 차감)"""
        position = {'entry': 100.0, 'qty': 1.0, 'side': 'SHORT'}
        pnl = calculate_pnl(position, 98.0, fee_rate=0.0004)
        # Gross: (100.0 - 98.0) * 1.0 = 2.0
        # Fee: (100.0 + 98.0) * 1.0 * 0.0004 = 0.0792
        # Net: 2.0 - 0.0792 = 1.9208
        assert 1.92 < pnl < 1.93, f"Expected ~1.92, got {pnl}"


class TestOHLCSLCheck:
    """OHLC 기반 SL 체크 테스트"""
    
    @pytest.fixture
    def tracker(self):
        """PositionTracker 인스턴스"""
        config = {
            'execution': {},
            'exits': {}
        }
        return PositionTracker(config)
    
    def test_short_sl_hit_by_high(self, tracker):
        """SHORT: High가 SL 도달 → SL 청산"""
        position = {
            'entry': 100.0,
            'sl': 108.0,
            'side': 'SHORT',
            'qty': 1.0,
            'tp_levels': {'tp1': 95.0}
        }
        candle = {'high': 110.0, 'low': 94.0, 'close': 95.0}
        
        should_action, qty, reason = tracker.check_tpsl_with_partial(
            position, 95.0, candle=candle
        )
        
        assert should_action is True, "SL should trigger"
        assert reason == 'SL', f"Expected 'SL', got '{reason}'"
        assert qty is None, "Should close entire position"
    
    def test_long_sl_hit_by_low(self, tracker):
        """LONG: Low가 SL 도달 → SL 청산"""
        position = {
            'entry': 100.0,
            'sl': 92.0,
            'side': 'LONG',
            'qty': 1.0,
            'tp_levels': {'tp1': 105.0}
        }
        candle = {'high': 106.0, 'low': 90.0, 'close': 105.0}
        
        should_action, qty, reason = tracker.check_tpsl_with_partial(
            position, 105.0, candle=candle
        )
        
        assert should_action is True, "SL should trigger"
        assert reason == 'SL', f"Expected 'SL', got '{reason}'"
    
    def test_sl_priority_over_tp(self, tracker):
        """SL 우선 체크: High가 SL 도달하면 TP1보다 우선"""
        position = {
            'entry': 100.0,
            'sl': 108.0,
            'side': 'SHORT',
            'qty': 1.0,
            'tp_levels': {'tp1': 95.0}
        }
        # High 110 (SL 도달), Close 95 (TP1 도달)
        candle = {'high': 110.0, 'low': 94.0, 'close': 95.0}
        
        should_action, qty, reason = tracker.check_tpsl_with_partial(
            position, 95.0, candle=candle
        )
        
        # SL이 TP1보다 우선해야 함
        assert reason == 'SL', f"SL should be prioritized, got '{reason}'"
    
    def test_no_sl_hit_when_safe(self, tracker):
        """SL 미도달: 정상 TP1 청산"""
        position = {
            'entry': 100.0,
            'sl': 108.0,
            'side': 'SHORT',
            'qty': 1.0,
            'tp_levels': {'tp1': 95.0}
        }
        # High 106 (SL 미도달), Close 95 (TP1 도달)
        candle = {'high': 106.0, 'low': 94.0, 'close': 95.0}
        
        should_action, qty, reason = tracker.check_tpsl_with_partial(
            position, 95.0, candle=candle
        )
        
        assert reason == 'TP1', f"Expected 'TP1', got '{reason}'"


class TestExtremeLoss20Pct:
    """Extreme Loss -20% 임계 테스트"""
    
    @pytest.fixture
    def tracker(self):
        """PositionTracker 인스턴스"""
        config = {
            'execution': {},
            'exits': {}
        }
        return PositionTracker(config)
    
    def test_long_extreme_loss_20pct(self, tracker):
        """LONG -20% 도달 → EXTREME_LOSS 청산"""
        position = {
            'entry': 100.0,
            'sl': 92.0,
            'side': 'LONG',
            'qty': 1.0,
            'tp_levels': {'tp1': 105.0}
        }
        
        should_action, qty, reason = tracker.check_tpsl_with_partial(
            position, 80.0  # -20%
        )
        
        assert should_action is True, "Extreme loss should trigger"
        assert reason == 'EXTREME_LOSS', f"Expected 'EXTREME_LOSS', got '{reason}'"
        assert qty is None, "Should close entire position"
    
    def test_short_extreme_loss_20pct(self, tracker):
        """SHORT -20% 도달 → EXTREME_LOSS 청산"""
        position = {
            'entry': 100.0,
            'sl': 108.0,
            'side': 'SHORT',
            'qty': 1.0,
            'tp_levels': {'tp1': 95.0}
        }
        
        should_action, qty, reason = tracker.check_tpsl_with_partial(
            position, 120.0  # -20%
        )
        
        assert should_action is True, "Extreme loss should trigger"
        assert reason == 'EXTREME_LOSS', f"Expected 'EXTREME_LOSS', got '{reason}'"
    
    def test_no_extreme_loss_at_minus_19pct(self, tracker):
        """LONG -19% → 정상 유지"""
        position = {
            'entry': 100.0,
            'sl': 92.0,
            'side': 'LONG',
            'qty': 1.0,
            'tp_levels': {'tp1': 105.0}
        }
        
        should_action, qty, reason = tracker.check_tpsl_with_partial(
            position, 81.0  # -19%
        )
        
        # SL 도달로 청산될 수 있지만, EXTREME_LOSS는 아님
        if should_action:
            assert reason != 'EXTREME_LOSS', "Should not trigger extreme loss at -19%"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
