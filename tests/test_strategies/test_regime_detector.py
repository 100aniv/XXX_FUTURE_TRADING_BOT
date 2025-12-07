#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-7: Regime Detector Unit Tests
======================================
6-state Regime Detection 검증
"""
import pytest
import pandas as pd
import numpy as np

from strategies.utils.regime_detector import detect_regime, get_regime_characteristics


class TestRegimeDetector:
    """Regime Detector 단위 테스트"""
    
    def create_sample_df(self, adx, di_plus, di_minus, atr_pct, length=100):
        """테스트용 샘플 DataFrame 생성"""
        df = pd.DataFrame({
            'close': np.linspace(100, 110, length),
            'adx_14': [adx] * length,
            'plus_di_14': [di_plus] * length,
            'minus_di_14': [di_minus] * length,
            'atr_14': [100 * atr_pct] * length,  # ATR = close * atr_pct
        })
        return df
    
    def test_bull_high_vol_detection(self):
        """Bull Trend + High Volatility 감지 테스트"""
        # ADX > 25, DI+ > DI-, ATR percentile > 70
        # ATR를 점진적으로 증가시켜 마지막 값이 percentile 상위에 오도록
        close_prices = np.linspace(100, 110, 100)
        atr_values = np.linspace(0.001, 0.005, 100) * close_prices  # 점진적 증가
        
        df = pd.DataFrame({
            'close': close_prices,
            'adx_14': [30] * 100,
            'plus_di_14': [30] * 100,
            'minus_di_14': [15] * 100,
            'atr_14': atr_values,
        })
        
        config = {
            'adx_trend_threshold': 25,
            'di_diff_threshold': 5,
            'atr_high_threshold': 70,
            'atr_lookback': 100
        }
        
        result = detect_regime(df, config)
        
        assert result['trend'] == 'bull'
        assert result['volatility'] == 'high_vol'
        assert result['regime'] == 'bull_high_vol'
        assert result['adx'] == 30
        assert result['di_plus'] == 30
        assert result['di_minus'] == 15
    
    def test_bear_low_vol_detection(self):
        """Bear Trend + Low Volatility 감지 테스트"""
        # ADX > 25, DI- > DI+, ATR percentile < 70
        df = self.create_sample_df(adx=28, di_plus=15, di_minus=35, atr_pct=0.001)
        
        config = {
            'adx_trend_threshold': 25,
            'di_diff_threshold': 5,
            'atr_high_threshold': 70,
            'atr_lookback': 100
        }
        
        result = detect_regime(df, config)
        
        assert result['trend'] == 'bear'
        assert result['volatility'] == 'low_vol'
        assert result['regime'] == 'bear_low_vol'
    
    def test_range_low_vol_detection(self):
        """Range + Low Volatility 감지 테스트"""
        # ADX < 25, DI+ ≈ DI-, ATR percentile < 70
        df = self.create_sample_df(adx=20, di_plus=18, di_minus=17, atr_pct=0.001)
        
        config = {
            'adx_trend_threshold': 25,
            'di_diff_threshold': 5,
            'atr_high_threshold': 70,
            'atr_lookback': 100
        }
        
        result = detect_regime(df, config)
        
        assert result['trend'] == 'range'
        assert result['volatility'] == 'low_vol'
        assert result['regime'] == 'range_low_vol'
    
    def test_range_high_vol_detection(self):
        """Range + High Volatility 감지 테스트"""
        # ADX < 25, DI+ ≈ DI-, ATR percentile > 70
        # ATR를 점진적으로 증가시켜 percentile이 높아지도록
        close_prices = np.linspace(100, 110, 100)
        atr_values = np.linspace(0.001, 0.005, 100) * close_prices  # 점진적 증가
        
        df = pd.DataFrame({
            'close': close_prices,
            'adx_14': [20] * 100,
            'plus_di_14': [18] * 100,
            'minus_di_14': [17] * 100,
            'atr_14': atr_values,
        })
        
        config = {
            'adx_trend_threshold': 25,
            'di_diff_threshold': 5,
            'atr_high_threshold': 70,
            'atr_lookback': 100
        }
        
        result = detect_regime(df, config)
        
        assert result['trend'] == 'range'
        assert result['volatility'] == 'high_vol'
        assert result['regime'] == 'range_high_vol'
    
    def test_weak_bull_trend_detection(self):
        """약한 Bull Trend 감지 테스트 (ADX < 25 but DI+ > DI-)"""
        df = self.create_sample_df(adx=22, di_plus=25, di_minus=15, atr_pct=0.002)
        
        config = {
            'adx_trend_threshold': 25,
            'di_diff_threshold': 5,
            'atr_high_threshold': 70,
            'atr_lookback': 100
        }
        
        result = detect_regime(df, config)
        
        assert result['trend'] == 'bull'  # DI+ - DI- = 10 > threshold(5)
    
    def test_missing_columns_fallback(self):
        """필수 컬럼 누락 시 기본 regime 반환 테스트"""
        df = pd.DataFrame({
            'close': np.linspace(100, 110, 100),
            # ADX/DI 컬럼 없음
        })
        
        config = {
            'adx_trend_threshold': 25,
            'di_diff_threshold': 5,
            'atr_high_threshold': 70,
            'atr_lookback': 100
        }
        
        result = detect_regime(df, config)
        
        assert result['regime'] == 'range_low_vol'  # Default fallback
        assert result['adx'] is None
    
    def test_regime_characteristics(self):
        """Regime 특성 정보 검증 테스트"""
        bull_high = get_regime_characteristics('bull_high_vol')
        assert bull_high['long_bias'] == 0.70
        assert bull_high['short_bias'] == 0.30
        assert '추세 추종' in bull_high['strategy_direction']
        
        bear_low = get_regime_characteristics('bear_low_vol')
        assert bear_low['long_bias'] == 0.40
        assert bear_low['short_bias'] == 0.60
        
        range_low = get_regime_characteristics('range_low_vol')
        assert range_low['long_bias'] == 0.50
        assert range_low['short_bias'] == 0.50
    
    def test_atr_percentile_calculation(self):
        """ATR percentile 계산 정확도 테스트"""
        # ATR가 선형 증가하는 경우
        atr_values = np.linspace(0.001, 0.005, 100)
        close_prices = np.full(100, 100.0)
        
        df = pd.DataFrame({
            'close': close_prices,
            'adx_14': [25] * 100,
            'plus_di_14': [25] * 100,
            'minus_di_14': [20] * 100,
            'atr_14': atr_values * close_prices,
        })
        
        config = {
            'adx_trend_threshold': 25,
            'di_diff_threshold': 5,
            'atr_high_threshold': 70,
            'atr_lookback': 100
        }
        
        result = detect_regime(df, config)
        
        # 마지막 ATR은 최대값이므로 percentile이 높아야 함
        assert result['atr_percentile'] > 90
        assert result['volatility'] == 'high_vol'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
