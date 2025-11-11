#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE7-2 Phase 1 단위 테스트: 동적 SL/TP
"""
import pytest
from common.calculations import price_levels


class TestDynamicSL:
    """동적 SL (ATR 기반) 테스트"""
    
    def test_sl_with_config_max_pct(self):
        """ATR 기반 SL이 max_sl_pct로 제한되는지 확인"""
        config = {
            'exits': {
                'sl_atr_multiplier': 1.5,
                'sl_max_pct': 6.0,  # 6%
                'sl_min_pct': 2.0,  # 2%
            }
        }
        
        # ATR이 매우 클 때 (10%) → max_pct로 제한
        entry, sl, tp = price_levels("LONG", 100, 10, 2.0, config=config)
        
        sl_dist_pct = abs(entry - sl) / entry * 100
        assert sl_dist_pct == pytest.approx(6.0, abs=0.1), f"SL이 6%로 제한되어야 함: {sl_dist_pct}%"
    
    def test_sl_with_config_min_pct(self):
        """ATR 기반 SL이 min_sl_pct로 제한되는지 확인"""
        config = {
            'exits': {
                'sl_atr_multiplier': 1.5,
                'sl_max_pct': 6.0,
                'sl_min_pct': 2.0,  # 2%
            }
        }
        
        # ATR이 매우 작을 때 (0.5%) → min_pct로 제한
        entry, sl, tp = price_levels("LONG", 100, 0.5, 2.0, config=config)
        
        sl_dist_pct = abs(entry - sl) / entry * 100
        assert sl_dist_pct == pytest.approx(2.0, abs=0.1), f"SL이 2%로 제한되어야 함: {sl_dist_pct}%"
    
    def test_sl_with_config_normal(self):
        """정상 범위의 ATR일 때 ATR * multiplier가 적용되는지 확인"""
        config = {
            'exits': {
                'sl_atr_multiplier': 1.5,
                'sl_max_pct': 6.0,
                'sl_min_pct': 2.0,
            }
        }
        
        # ATR 3% * 1.5 = 4.5% (2~6% 범위 내)
        entry, sl, tp = price_levels("LONG", 100, 3, 2.0, config=config)
        
        sl_dist_pct = abs(entry - sl) / entry * 100
        expected = 4.5  # 3 * 1.5 / 100 * 100 = 4.5%
        assert sl_dist_pct == pytest.approx(expected, abs=0.1), f"SL이 {expected}%여야 함: {sl_dist_pct}%"
    
    def test_sl_without_config_backward_compatible(self):
        """config 미전달 시 기존 파라미터가 사용되는지 확인 (하위 호환)"""
        # max_sl_pct=0.08 (8%) 기본값
        entry, sl, tp = price_levels("LONG", 100, 2, 2.0, max_sl_pct=0.08)
        
        sl_dist_pct = abs(entry - sl) / entry * 100
        assert sl_dist_pct == pytest.approx(3.0, abs=0.1), f"SL이 3%여야 함: {sl_dist_pct}%"
    
    def test_sl_short_position(self):
        """SHORT 포지션에서도 동적 SL이 올바르게 작동하는지 확인"""
        config = {
            'exits': {
                'sl_atr_multiplier': 1.5,
                'sl_max_pct': 6.0,
                'sl_min_pct': 2.0,
            }
        }
        
        # SHORT: entry 100, ATR 3 * 1.5 = 4.5% → SL 104.5
        entry, sl, tp = price_levels("SHORT", 100, 3, 2.0, config=config)
        
        assert entry == 100
        assert sl > entry, "SHORT SL은 entry보다 높아야 함"
        sl_dist_pct = abs(sl - entry) / entry * 100
        assert sl_dist_pct == pytest.approx(4.5, abs=0.1)


# TPManager 테스트는 Paper 테스트에서 통합 검증
# (import 문제로 단위 테스트 제외)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
