#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-7: Dynamic Threshold Unit Tests
========================================
RSI/BB Dynamic Threshold 계산 검증
"""
import pytest
import pandas as pd
import numpy as np

from strategies.utils.dynamic_threshold import (
    get_rsi_threshold,
    get_bb_threshold,
    get_momentum_threshold,
    calculate_bb_bands
)


class TestDynamicThreshold:
    """Dynamic Threshold 단위 테스트"""
    
    def create_sample_df_with_rsi(self, rsi_mean=50, rsi_std=10, length=100):
        """RSI가 포함된 샘플 DataFrame 생성"""
        rsi_values = np.random.normal(rsi_mean, rsi_std, length)
        rsi_values = np.clip(rsi_values, 0, 100)  # RSI 범위 제한
        
        df = pd.DataFrame({
            'close': np.linspace(100, 110, length),
            'rsi': rsi_values,
            'atr_14': np.full(length, 0.002 * 105),  # 평균 close 대비 0.2%
        })
        return df
    
    def test_rsi_threshold_bull_adjustment(self):
        """Bull Regime에서 RSI threshold 상향 조정 테스트"""
        df = self.create_sample_df_with_rsi(rsi_mean=60, rsi_std=10)
        
        config = {
            'rsi_long_percentile_base': 25,
            'rsi_short_percentile_base': 75,
            'bull_rsi_adjustment': 1.2,
            'bear_rsi_adjustment': 0.85,
            'rsi_lookback': 100
        }
        
        # Bull regime에서는 threshold가 상향 조정되어야 함
        rsi_long, rsi_short = get_rsi_threshold(df, config, 'bull_high_vol')
        
        # Bull에서는 long threshold가 더 높아져야 함 (더 쉽게 진입)
        assert 25 <= rsi_long <= 50
        assert 50 <= rsi_short <= 75
        
        # Bull adjustment 적용 확인 (percentile base * 1.2)
        # 실제 RSI 평균이 60이므로 percentile 계산 결과도 그에 맞게 조정됨
        assert rsi_long > 25  # Base 25에서 상향 조정
    
    def test_rsi_threshold_bear_adjustment(self):
        """Bear Regime에서 RSI threshold 하향 조정 테스트"""
        df = self.create_sample_df_with_rsi(rsi_mean=40, rsi_std=10)
        
        config = {
            'rsi_long_percentile_base': 25,
            'rsi_short_percentile_base': 75,
            'bull_rsi_adjustment': 1.2,
            'bear_rsi_adjustment': 0.85,
            'rsi_lookback': 100
        }
        
        rsi_long, rsi_short = get_rsi_threshold(df, config, 'bear_high_vol')
        
        # Bear에서는 short threshold가 하향 조정되어야 함
        assert 25 <= rsi_long <= 50
        assert 50 <= rsi_short <= 75
    
    def test_rsi_threshold_range_neutral(self):
        """Range Regime에서 RSI threshold 조정 없음 테스트"""
        df = self.create_sample_df_with_rsi(rsi_mean=50, rsi_std=10)
        
        config = {
            'rsi_long_percentile_base': 25,
            'rsi_short_percentile_base': 75,
            'bull_rsi_adjustment': 1.2,
            'bear_rsi_adjustment': 0.85,
            'rsi_lookback': 100
        }
        
        rsi_long, rsi_short = get_rsi_threshold(df, config, 'range_low_vol')
        
        # Range에서는 조정이 1.0이므로 base percentile 그대로
        assert 25 <= rsi_long <= 50
        assert 50 <= rsi_short <= 75
    
    def test_rsi_threshold_clipping(self):
        """RSI threshold 극단값 clipping 테스트"""
        # 극단적인 RSI 분포
        df = pd.DataFrame({
            'close': np.linspace(100, 110, 100),
            'rsi': np.full(100, 90),  # 모든 값이 90
        })
        
        config = {
            'rsi_long_percentile_base': 25,
            'rsi_short_percentile_base': 75,
            'bull_rsi_adjustment': 1.5,  # 극단적 조정
            'bear_rsi_adjustment': 0.5,
            'rsi_lookback': 100
        }
        
        rsi_long, rsi_short = get_rsi_threshold(df, config, 'bull_high_vol')
        
        # Clipping 확인: [25, 50] / [50, 75] 범위 내
        assert 25 <= rsi_long <= 50
        assert 50 <= rsi_short <= 75
    
    def test_bb_threshold_high_vol_adjustment(self):
        """High Volatility에서 BB multiplier 하향 조정 테스트"""
        df = pd.DataFrame({
            'close': np.linspace(100, 110, 100),
            'atr_14': np.full(100, 0.003 * 105),  # High ATR (0.3%)
        })
        
        config = {
            'bb_mult_main_base': 0.8,
            'bb_mult_strong_base': 1.5,
            'high_vol_bb_adjustment': 0.85,
            'low_vol_bb_adjustment': 1.15
        }
        
        bb_main, bb_strong = get_bb_threshold(df, config, 'bull_high_vol')
        
        # High vol에서는 multiplier가 낮아져야 함 (더 쉽게 진입)
        assert bb_main < 1.0
        assert bb_strong < 2.0
        
        # Base * adjustment 확인
        # 0.8 * 0.85 = 0.68 (+ ATR adjustment)
        assert 0.5 <= bb_main <= 1.5
        assert 1.0 <= bb_strong <= 2.5
    
    def test_bb_threshold_low_vol_adjustment(self):
        """Low Volatility에서 BB multiplier 상향 조정 테스트"""
        df = pd.DataFrame({
            'close': np.linspace(100, 110, 100),
            'atr_14': np.full(100, 0.001 * 105),  # Low ATR (0.1%)
        })
        
        config = {
            'bb_mult_main_base': 0.8,
            'bb_mult_strong_base': 1.5,
            'high_vol_bb_adjustment': 0.85,
            'low_vol_bb_adjustment': 1.15
        }
        
        bb_main, bb_strong = get_bb_threshold(df, config, 'range_low_vol')
        
        # Low vol에서는 multiplier가 높아져야 함 (더 어렵게 진입)
        assert bb_main > 0.8  # Base보다 높음
        assert bb_strong > 1.5  # Base보다 높음
    
    def test_momentum_threshold_regime_specific(self):
        """Regime별 Momentum threshold 테스트"""
        df = pd.DataFrame({
            'close': np.linspace(100, 110, 100),
        })
        
        config = {
            'momentum_threshold_base': 0.001
        }
        
        # High vol regimes는 더 높은 threshold
        mom_bull_high = get_momentum_threshold(df, config, 'bull_high_vol')
        mom_range_low = get_momentum_threshold(df, config, 'range_low_vol')
        
        assert mom_bull_high > mom_range_low
        assert mom_bull_high == 0.002  # 0.2%
        assert mom_range_low == 0.0008  # 0.08%
    
    def test_calculate_bb_bands(self):
        """Bollinger Bands 계산 테스트"""
        close_prices = np.array([100, 101, 102, 103, 104] * 20)  # 100개
        df = pd.DataFrame({'close': close_prices})
        
        bb_mult = 2.0
        bb_period = 20
        
        bb_bands = calculate_bb_bands(df, bb_mult, bb_period)
        
        # 결과 구조 확인
        assert 'upper' in bb_bands
        assert 'middle' in bb_bands
        assert 'lower' in bb_bands
        
        # Upper > Middle > Lower 확인
        assert bb_bands['upper'] > bb_bands['middle']
        assert bb_bands['middle'] > bb_bands['lower']
        
        # Middle은 이동평균과 동일해야 함
        expected_middle = close_prices[-20:].mean()
        assert abs(bb_bands['middle'] - expected_middle) < 0.01
    
    def test_rsi_threshold_missing_column(self):
        """RSI 컬럼 누락 시 기본값 반환 테스트"""
        df = pd.DataFrame({
            'close': np.linspace(100, 110, 100),
            # RSI 컬럼 없음
        })
        
        config = {
            'rsi_long_percentile_base': 25,
            'rsi_short_percentile_base': 75,
            'bull_rsi_adjustment': 1.2,
            'bear_rsi_adjustment': 0.85,
            'rsi_lookback': 100
        }
        
        rsi_long, rsi_short = get_rsi_threshold(df, config, 'bull_high_vol')
        
        # Default 값 반환 확인
        assert rsi_long == 45.0
        assert rsi_short == 55.0
    
    def test_bb_bands_insufficient_data(self):
        """데이터 부족 시 BB bands 계산 테스트"""
        # 20개 미만 데이터
        df = pd.DataFrame({
            'close': np.linspace(100, 105, 15)
        })
        
        bb_mult = 2.0
        bb_period = 20
        
        # 데이터 부족 시에도 계산 가능해야 함 (rolling window가 부족한 초기 값은 NaN)
        bb_bands = calculate_bb_bands(df, bb_mult, bb_period)
        
        # 결과가 반환되어야 함 (NaN일 수 있음)
        assert bb_bands is not None
        assert 'upper' in bb_bands
        assert 'middle' in bb_bands
        assert 'lower' in bb_bands


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
