#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE22-1 Unit Tests - 신규 4개 전략 테스트
===========================================
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 sys.path에 명시적으로 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from strategies.research.volatility_breakout_v2 import VolatilityBreakoutStrategy
from strategies.research.mean_reversion_v2 import MeanReversionStrategy
from strategies.research.trend_follow_v2 import TrendFollowingStrategy
from strategies.research.volume_based_v2 import VolumeBasedStrategy


# Fixture: 기본 Config
@pytest.fixture
def base_config():
    return {
        'leverage': {'min': 1, 'max': 10, 'default': 3},
        'filters': {'allow_short': True},
        'min_bars_for_signal': 60,
    }


# Fixture: 더미 OHLCV 데이터 (250개 캔들)
@pytest.fixture
def dummy_df():
    """더미 OHLCV + 지표 데이터 생성"""
    n = 250
    dates = pd.date_range(end=datetime.now(), periods=n, freq='5T')
    
    # 더미 OHLCV
    close = 50000 + np.cumsum(np.random.randn(n) * 100)
    high = close + np.abs(np.random.randn(n) * 50)
    low = close - np.abs(np.random.randn(n) * 50)
    open_price = close + np.random.randn(n) * 20
    volume = np.random.randint(1000, 5000, n)
    
    df = pd.DataFrame({
        'time': dates,
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    })
    
    # 지표 추가
    df['atr'] = np.abs(np.random.randn(n) * 200)
    df['rsi'] = 30 + np.random.randn(n) * 20  # 10~70 범위
    df['ema_fast'] = df['close'].ewm(span=8).mean()
    df['ema_slow'] = df['close'].ewm(span=21).mean()
    df['vol_ma'] = df['volume'].rolling(20).mean().fillna(df['volume'].mean())
    df['bb_upper'] = df['close'] + df['atr'] * 2
    df['bb_lower'] = df['close'] - df['atr'] * 2
    df['bb_middle'] = df['close']
    df['macd'] = np.random.randn(n) * 10
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    return df


# ==============================================================================
# Test: VolatilityBreakoutStrategy
# ==============================================================================

def test_volatility_breakout_instantiation(base_config):
    """전략 인스턴스 생성 테스트"""
    strategy = VolatilityBreakoutStrategy(base_config)
    assert strategy is not None
    assert strategy.config == base_config


def test_volatility_breakout_metadata(base_config):
    """Metadata 프로퍼티 테스트"""
    strategy = VolatilityBreakoutStrategy(base_config)
    metadata = strategy.metadata
    
    assert metadata.strategy_name == 'breakout_v2'
    assert metadata.strategy_type == 'breakout'
    assert '15m' in metadata.supported_timeframes
    assert metadata.optimal_regime == 'trending'
    assert metadata.worst_regime == 'low_volatility'


def test_volatility_breakout_compute_signal(base_config, dummy_df):
    """compute_signal 호출 테스트"""
    strategy = VolatilityBreakoutStrategy(base_config)
    signal = strategy.compute_signal(dummy_df)
    
    # 신호 구조 확인
    assert 'side' in signal
    assert 'action' in signal
    assert 'entry' in signal
    assert 'sl' in signal
    assert 'tp' in signal
    assert 'lev' in signal
    assert 'reason' in signal
    
    # 신호 타입 확인
    if signal['side']:
        assert signal['side'] in ['LONG', 'SHORT']
        assert signal['entry'] is not None
        assert signal['sl'] is not None
        assert signal['tp'] is not None


def test_volatility_breakout_no_crash_on_edge_cases(base_config):
    """극단 케이스에서 예외 없이 동작 테스트"""
    strategy = VolatilityBreakoutStrategy(base_config)
    
    # 데이터 부족 케이스
    small_df = pd.DataFrame({
        'time': pd.date_range(end=datetime.now(), periods=10, freq='5T'),
        'open': [50000] * 10,
        'high': [50100] * 10,
        'low': [49900] * 10,
        'close': [50000] * 10,
        'volume': [1000] * 10,
        'atr': [100] * 10,
        'rsi': [50] * 10,
        'vol_ma': [1000] * 10,
    })
    
    signal = strategy.compute_signal(small_df)
    assert signal is not None
    # 데이터 부족 시 신호 없음
    assert signal.get('side') is None


# ==============================================================================
# Test: MeanReversionStrategy
# ==============================================================================

def test_mean_reversion_instantiation(base_config):
    """전략 인스턴스 생성 테스트"""
    strategy = MeanReversionStrategy(base_config)
    assert strategy is not None


def test_mean_reversion_metadata(base_config):
    """Metadata 프로퍼티 테스트"""
    strategy = MeanReversionStrategy(base_config)
    metadata = strategy.metadata
    
    assert metadata.strategy_name == 'reversion_v2'
    assert metadata.strategy_type == 'reversion'
    assert '5m' in metadata.supported_timeframes
    assert metadata.optimal_regime == 'ranging'
    assert metadata.worst_regime == 'trending'


def test_mean_reversion_compute_signal(base_config, dummy_df):
    """compute_signal 호출 테스트"""
    strategy = MeanReversionStrategy(base_config)
    signal = strategy.compute_signal(dummy_df)
    
    # 신호 구조 확인
    assert 'side' in signal
    assert 'rsi' in signal
    assert 'bb_upper' in signal
    assert 'bb_lower' in signal


def test_mean_reversion_extreme_rsi():
    """극단 RSI 케이스 테스트"""
    config = {
        'leverage': {'min': 1, 'max': 10, 'default': 3},
        'filters': {'allow_short': True},
        'min_bars_for_signal': 60,
        'rsi_oversold': 25,
        'rsi_overbought': 75,
    }
    
    n = 100
    dates = pd.date_range(end=datetime.now(), periods=n, freq='5T')
    df = pd.DataFrame({
        'time': dates,
        'open': [50000] * n,
        'high': [50100] * n,
        'low': [49900] * n,
        'close': [50000] * n,
        'volume': [1000] * n,
        'atr': [100] * n,
        'rsi': [20] * n,  # 극단 과매도
        'vol_ma': [1000] * n,
        'bb_upper': [50200] * n,
        'bb_lower': [49800] * n,
        'bb_middle': [50000] * n,
    })
    
    strategy = MeanReversionStrategy(config)
    signal = strategy.compute_signal(df)
    assert signal is not None


# ==============================================================================
# Test: TrendFollowingStrategy
# ==============================================================================

def test_trend_following_instantiation(base_config):
    """전략 인스턴스 생성 테스트"""
    strategy = TrendFollowingStrategy(base_config)
    assert strategy is not None


def test_trend_following_metadata(base_config):
    """Metadata 프로퍼티 테스트"""
    strategy = TrendFollowingStrategy(base_config)
    metadata = strategy.metadata
    
    assert metadata.strategy_name == 'trend_v2'
    assert metadata.strategy_type == 'trend'
    assert '1h' in metadata.supported_timeframes
    assert metadata.optimal_regime == 'trending'


def test_trend_following_compute_signal(base_config, dummy_df):
    """compute_signal 호출 테스트"""
    strategy = TrendFollowingStrategy(base_config)
    signal = strategy.compute_signal(dummy_df)
    
    # 신호 구조 확인
    assert 'side' in signal
    assert 'macd' in signal


def test_trend_following_insufficient_data():
    """SMA200 데이터 부족 케이스"""
    config = {
        'leverage': {'min': 1, 'max': 10, 'default': 3},
        'filters': {'allow_short': True},
        'min_bars_for_signal': 210,
        'sma_fast': 50,
        'sma_slow': 200,
    }
    
    n = 100  # SMA200 필요하지만 100개만 제공
    dates = pd.date_range(end=datetime.now(), periods=n, freq='1H')
    df = pd.DataFrame({
        'time': dates,
        'open': [50000] * n,
        'high': [50100] * n,
        'low': [49900] * n,
        'close': [50000] * n,
        'volume': [1000] * n,
        'atr': [100] * n,
        'rsi': [50] * n,
        'vol_ma': [1000] * n,
        'macd': [0] * n,
        'macd_signal': [0] * n,
        'macd_hist': [0] * n,
    })
    
    strategy = TrendFollowingStrategy(config)
    signal = strategy.compute_signal(df)
    # 데이터 부족 시 신호 없음
    assert signal.get('side') is None


# ==============================================================================
# Test: VolumeBasedStrategy
# ==============================================================================

def test_volume_based_instantiation(base_config):
    """전략 인스턴스 생성 테스트"""
    strategy = VolumeBasedStrategy(base_config)
    assert strategy is not None


def test_volume_based_metadata(base_config):
    """Metadata 프로퍼티 테스트"""
    strategy = VolumeBasedStrategy(base_config)
    metadata = strategy.metadata
    
    assert metadata.strategy_name == 'volume_v2'
    assert metadata.strategy_type == 'volume'
    assert '5m' in metadata.supported_timeframes
    assert metadata.optimal_regime == 'high_volume'
    assert metadata.worst_regime == 'low_volume'


def test_volume_based_compute_signal(base_config, dummy_df):
    """compute_signal 호출 테스트"""
    strategy = VolumeBasedStrategy(base_config)
    signal = strategy.compute_signal(dummy_df)
    
    # 신호 구조 확인
    assert 'side' in signal
    assert 'obv' in signal
    assert 'volume' in signal


def test_volume_based_obv_calculation():
    """OBV 계산 검증"""
    config = {
        'leverage': {'min': 1, 'max': 10, 'default': 3},
        'filters': {'allow_short': True},
        'min_bars_for_signal': 60,
        'obv_ma_period': 20,
        'vol_mult': 2.0,
    }
    
    n = 100
    dates = pd.date_range(end=datetime.now(), periods=n, freq='5T')
    df = pd.DataFrame({
        'time': dates,
        'open': [50000] * n,
        'high': [50100] * n,
        'low': [49900] * n,
        'close': list(range(50000, 50000 + n)),  # 점진적 상승
        'volume': [1000] * n,
        'atr': [100] * n,
        'rsi': [50] * n,
        'vol_ma': [1000] * n,
    })
    
    strategy = VolumeBasedStrategy(config)
    signal = strategy.compute_signal(df)
    
    # OBV가 계산되었는지 확인
    assert 'obv' in signal
    assert signal['obv'] is not None


# ==============================================================================
# Integration Test: 모든 전략 동시 실행
# ==============================================================================

def test_all_strategies_no_conflict(base_config, dummy_df):
    """4개 전략 동시 실행 시 충돌 없음 확인"""
    strategies = [
        VolatilityBreakoutStrategy(base_config),
        MeanReversionStrategy(base_config),
        TrendFollowingStrategy(base_config),
        VolumeBasedStrategy(base_config),
    ]
    
    for strategy in strategies:
        signal = strategy.compute_signal(dummy_df)
        assert signal is not None
        assert 'side' in signal


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
