"""
⭐ PHASE7-2 Phase 2: 동적 슬리피지 계산 단위 테스트

업계 표준 검증:
- QuantConnect, Backtrader, Zipline 분석
- 방안 A (SL + 동적 슬리피지) 적용
"""
import pytest
from common.calculations import calculate_dynamic_slippage


class TestDynamicSlippage:
    """동적 슬리피지 계산 테스트"""
    
    def test_market_order_low_volatility(self):
        """MARKET 주문 + 낮은 변동성 → 기본 슬리피지"""
        config = {
            'fees': {
                'slippage_base': 0.0005,
                'slippage_multiplier': {'market': 1.0, 'sl': 3.0},
                'slippage_max': 0.06
            }
        }
        
        # ATR 1%, 가격 100 → 변동성 1%
        result = calculate_dynamic_slippage(atr=1.0, price=100.0, order_type='MARKET', config=config)
        
        # 기본 0.0005 + (0.01 * 1.0) = 0.0105 = 1.05%
        expected = 0.0005 + (1.0 / 100.0) * 1.0
        assert abs(result - expected) < 0.0001, f"Expected {expected}, got {result}"
    
    def test_sl_order_high_volatility(self):
        """SL 청산 + 높은 변동성 → 큰 슬리피지"""
        config = {
            'fees': {
                'slippage_base': 0.0005,
                'slippage_multiplier': {'market': 1.0, 'sl': 3.0},
                'slippage_max': 0.06
            }
        }
        
        # ATR 10%, 가격 100 → 변동성 10%
        result = calculate_dynamic_slippage(atr=10.0, price=100.0, order_type='SL', config=config)
        
        # 기본 0.0005 + (0.10 * 3.0) = 0.3005 → max 0.06 제한
        expected = 0.06  # 최대값
        assert result == expected, f"Expected {expected}, got {result}"
    
    def test_sl_order_medium_volatility(self):
        """SL 청산 + 중간 변동성 → 적정 슬리피지"""
        config = {
            'fees': {
                'slippage_base': 0.0005,
                'slippage_multiplier': {'market': 1.0, 'sl': 3.0},
                'slippage_max': 0.06
            }
        }
        
        # ATR 3%, 가격 100 → 변동성 3%
        result = calculate_dynamic_slippage(atr=3.0, price=100.0, order_type='SL', config=config)
        
        # 기본 0.0005 + (0.03 * 3.0) = 0.0905 → max 0.06 제한
        expected = 0.06
        assert result == expected, f"Expected {expected}, got {result}"
    
    def test_no_config_fallback(self):
        """config 없으면 기본값 사용"""
        result = calculate_dynamic_slippage(atr=2.0, price=100.0, order_type='MARKET', config=None)
        
        # 기본 0.0005 + (0.02 * 1.0) = 0.0205
        expected = 0.0005 + (2.0 / 100.0) * 1.0
        assert abs(result - expected) < 0.0001, f"Expected {expected}, got {result}"
    
    def test_max_limit_enforcement(self):
        """최대 슬리피지 제한 적용"""
        config = {
            'fees': {
                'slippage_base': 0.0005,
                'slippage_multiplier': {'market': 1.0, 'sl': 3.0},
                'slippage_max': 0.03  # 3%로 제한
            }
        }
        
        # ATR 10%, 가격 100 → 변동성 10%, SL 3배 → 30.05%
        result = calculate_dynamic_slippage(atr=10.0, price=100.0, order_type='SL', config=config)
        
        # max 3% 제한
        expected = 0.03
        assert result == expected, f"Expected {expected}, got {result}"
    
    def test_zero_atr(self):
        """ATR 0 → 기본 슬리피지만"""
        config = {
            'fees': {
                'slippage_base': 0.0005,
                'slippage_multiplier': {'market': 1.0, 'sl': 3.0},
                'slippage_max': 0.06
            }
        }
        
        result = calculate_dynamic_slippage(atr=0.0, price=100.0, order_type='MARKET', config=config)
        
        # 변동성 0 → 기본값만
        expected = 0.0005
        assert result == expected, f"Expected {expected}, got {result}"
    
    def test_realistic_scenario_btc(self):
        """현실적 시나리오: BTC ATR 3% → SL 슬리피지"""
        config = {
            'fees': {
                'slippage_base': 0.0005,
                'slippage_multiplier': {'market': 1.0, 'sl': 3.0},
                'slippage_max': 0.06
            }
        }
        
        # BTC 가격 40000, ATR 1200 (3%)
        result = calculate_dynamic_slippage(atr=1200, price=40000, order_type='SL', config=config)
        
        # 0.0005 + (0.03 * 3.0) = 0.0905 → max 0.06
        expected = 0.06
        assert result == expected, f"Expected {expected}, got {result}"
    
    def test_realistic_scenario_altcoin(self):
        """현실적 시나리오: 알트코인 ATR 5% → MARKET 슬리피지"""
        config = {
            'fees': {
                'slippage_base': 0.0005,
                'slippage_multiplier': {'market': 1.0, 'sl': 3.0},
                'slippage_max': 0.06
            }
        }
        
        # 알트코인 가격 1.0, ATR 0.05 (5%)
        result = calculate_dynamic_slippage(atr=0.05, price=1.0, order_type='MARKET', config=config)
        
        # 0.0005 + (0.05 * 1.0) = 0.0505 = 5.05%
        expected = 0.0505
        assert abs(result - expected) < 0.0001, f"Expected {expected}, got {result}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
