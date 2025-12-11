#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE30-1: btc15m_core_v1 전략 테스트
====================================

Core V1 전략의 핵심 컴포넌트 단위 테스트
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from strategies.btc15m_core_v1 import (
    detect_regime,
    passes_core_and_filters,
    trend_up_scenarios,
    trend_down_scenarios,
    range_scenarios,
    calculate_sl_tp,
    signal_logic,
    Btc15mCoreV1
)


# =====================================================
# Fixtures
# =====================================================

@pytest.fixture
def sample_df():
    """샘플 OHLCV + 지표 데이터"""
    dates = pd.date_range(start='2024-01-01', periods=200, freq='15min')
    
    # 가격 생성 (간단한 추세 + 노이즈)
    price_base = 50000
    price = price_base + np.cumsum(np.random.randn(200) * 100)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': price + np.random.randn(200) * 10,
        'high': price + abs(np.random.randn(200) * 20),
        'low': price - abs(np.random.randn(200) * 20),
        'close': price,
        'volume': 1000 + np.random.rand(200) * 500
    })
    
    # 지표 추가
    df['rsi_14'] = 50 + np.random.randn(200) * 15
    df['adx_14'] = 20 + abs(np.random.randn(200) * 10)
    df['di_plus_14'] = 20 + abs(np.random.randn(200) * 5)
    df['di_minus_14'] = 20 + abs(np.random.randn(200) * 5)
    df['atr_14'] = df['close'] * 0.002 + abs(np.random.randn(200) * 0.0005)
    df['ema_20'] = df['close'].rolling(20).mean()
    df['ema_50'] = df['close'].rolling(50).mean()
    df['ema_200'] = df['close'].rolling(100).mean()  # 200은 너무 길어서 100으로
    df['volume_ma_20'] = df['volume'].rolling(20).mean()
    
    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_middle'] + bb_std * 2
    df['bb_lower'] = df['bb_middle'] - bb_std * 2
    
    return df


@pytest.fixture
def default_config():
    """기본 Config"""
    return {
        'regime_detection': {
            'adx_trend_threshold': 25,
            'adx_range_threshold': 20,
            'atr_high_vol_mult': 1.5,
            'volume_high_vol_mult': 2.0,
            'min_confidence': 0.3
        },
        'filters': {
            'min_atr_pct': 0.002,
            'min_volume_ratio': 0.7
        },
        'sl_tp': {
            'sl_mult_trend': 2.0,
            'tp1_rr_trend': 1.5,
            'tp2_rr_trend': 3.0,
            'sl_mult_range': 1.5,
            'tp1_rr_range': 1.5,
            'tp2_rr_range': 2.5
        },
        'leverage': {
            'min': 1,
            'max': 5,
            'default': 3
        }
    }


# =====================================================
# Regime Detection 테스트
# =====================================================

def test_detect_regime_trend_up(sample_df, default_config):
    """Trend-Up Regime 감지 테스트"""
    # Trend-Up 조건 강제 설정
    sample_df.loc[sample_df.index[-1], 'adx_14'] = 30
    sample_df.loc[sample_df.index[-1], 'di_plus_14'] = 30
    sample_df.loc[sample_df.index[-1], 'di_minus_14'] = 20
    
    regime_info = detect_regime(sample_df, default_config)
    
    assert regime_info['regime'] == 'TREND_UP'
    assert regime_info['confidence'] > 0
    assert 'adx' in regime_info
    assert 'atr_ratio' in regime_info


def test_detect_regime_trend_down(sample_df, default_config):
    """Trend-Down Regime 감지 테스트"""
    # Trend-Down 조건 강제 설정
    sample_df.loc[sample_df.index[-1], 'adx_14'] = 30
    sample_df.loc[sample_df.index[-1], 'di_plus_14'] = 20
    sample_df.loc[sample_df.index[-1], 'di_minus_14'] = 30
    
    regime_info = detect_regime(sample_df, default_config)
    
    assert regime_info['regime'] == 'TREND_DOWN'
    assert regime_info['confidence'] > 0


def test_detect_regime_range(sample_df, default_config):
    """Range Regime 감지 테스트"""
    # Range 조건 강제 설정
    sample_df.loc[sample_df.index[-1], 'adx_14'] = 15
    
    regime_info = detect_regime(sample_df, default_config)
    
    assert regime_info['regime'] == 'RANGE'
    assert regime_info['confidence'] > 0


def test_detect_regime_insufficient_data():
    """데이터 부족 시 UNKNOWN 반환 테스트"""
    df = pd.DataFrame({
        'close': [50000] * 10,
        'volume': [1000] * 10
    })
    
    regime_info = detect_regime(df, {})
    
    assert regime_info['regime'] == 'UNKNOWN'
    assert regime_info['confidence'] == 0.0


# =====================================================
# Core AND Block 테스트
# =====================================================

def test_core_and_filters_pass(sample_df, default_config):
    """Core AND 필터 통과 테스트"""
    regime_info = {
        'regime': 'TREND_UP',
        'confidence': 0.5
    }
    
    # ATR, Volume 충분히 높게 설정
    sample_df.loc[sample_df.index[-1], 'atr_14'] = sample_df.iloc[-1]['close'] * 0.003
    sample_df.loc[sample_df.index[-1], 'volume'] = sample_df['volume'].mean() * 1.5
    
    passed, reason = passes_core_and_filters(sample_df, regime_info, default_config)
    
    assert passed is True
    assert reason == "core_and_pass"


def test_core_and_filters_invalid_regime(sample_df, default_config):
    """잘못된 Regime 거부 테스트"""
    regime_info = {
        'regime': 'HIGH_VOL_CHOP',  # 진입 불가 Regime
        'confidence': 0.5
    }
    
    passed, reason = passes_core_and_filters(sample_df, regime_info, default_config)
    
    assert passed is False
    assert "invalid_regime" in reason


def test_core_and_filters_low_atr(sample_df, default_config):
    """ATR 부족 거부 테스트"""
    regime_info = {
        'regime': 'TREND_UP',
        'confidence': 0.5
    }
    
    # ATR 매우 낮게 설정
    sample_df.loc[sample_df.index[-1], 'atr_14'] = sample_df.iloc[-1]['close'] * 0.0001
    
    passed, reason = passes_core_and_filters(sample_df, regime_info, default_config)
    
    assert passed is False
    assert "atr_too_low" in reason


# =====================================================
# Optional OR Block 테스트
# =====================================================

def test_trend_up_ema_pullback(sample_df, default_config):
    """Trend-Up EMA Pullback 시나리오 테스트"""
    last_idx = sample_df.index[-1]
    
    # EMA Pullback 조건 설정
    sample_df.loc[last_idx, 'ema_50'] = 50000
    sample_df.loc[last_idx, 'close'] = 50100
    sample_df.loc[last_idx, 'open'] = 49950
    sample_df.loc[last_idx, 'low'] = 49990  # EMA 터치
    
    has_signal, scenario = trend_up_scenarios(sample_df, default_config)
    
    assert has_signal is True
    assert scenario == "trend_up_ema_pullback"


def test_trend_down_rsi_overbought(sample_df, default_config):
    """Trend-Down RSI Overbought 시나리오 테스트"""
    last_idx = sample_df.index[-1]
    prev_idx = sample_df.index[-2]
    
    # RSI Overbought 조건 설정
    sample_df.loc[prev_idx, 'rsi_14'] = 70
    sample_df.loc[last_idx, 'rsi_14'] = 68  # RSI 하락
    sample_df.loc[last_idx, 'close'] = 49900
    sample_df.loc[last_idx, 'open'] = 50100  # 하락 캔들
    
    has_signal, scenario = trend_down_scenarios(sample_df, default_config)
    
    assert has_signal is True
    assert scenario == "trend_down_rsi_overbought"


def test_range_bb_lower_long(sample_df, default_config):
    """Range BB Lower LONG 시나리오 테스트"""
    last_idx = sample_df.index[-1]
    
    # BB Lower 터치 조건 설정
    sample_df.loc[last_idx, 'bb_lower'] = 50000
    sample_df.loc[last_idx, 'low'] = 50005  # BB 하단 터치
    sample_df.loc[last_idx, 'rsi_14'] = 35  # Oversold
    sample_df.loc[last_idx, 'close'] = 50100
    sample_df.loc[last_idx, 'open'] = 50050  # 반등 캔들
    
    has_signal, scenario, side = range_scenarios(sample_df, default_config)
    
    assert has_signal is True
    assert scenario == "range_bb_lower_long"
    assert side == "LONG"


# =====================================================
# SL/TP 계산 테스트
# =====================================================

def test_calculate_sl_tp_trend_long(default_config):
    """Trend LONG SL/TP 계산 테스트"""
    sl_tp = calculate_sl_tp('TREND_UP', 'LONG', 50000, 100, default_config)
    
    assert sl_tp['sl'] < 50000  # SL은 진입가 아래
    assert sl_tp['tp1'] > 50000  # TP1은 진입가 위
    assert sl_tp['tp2'] > sl_tp['tp1']  # TP2는 TP1보다 위
    assert sl_tp['tp1_rr'] >= 1.5  # 최소 RR 1.5
    assert sl_tp['tp2_rr'] > sl_tp['tp1_rr']


def test_calculate_sl_tp_range_short(default_config):
    """Range SHORT SL/TP 계산 테스트"""
    sl_tp = calculate_sl_tp('RANGE', 'SHORT', 50000, 100, default_config)
    
    assert sl_tp['sl'] > 50000  # SL은 진입가 위
    assert sl_tp['tp1'] < 50000  # TP1은 진입가 아래
    assert sl_tp['tp2'] < sl_tp['tp1']  # TP2는 TP1보다 아래
    assert sl_tp['tp1_rr'] >= 1.5  # 최소 RR 1.5


# =====================================================
# BaseStrategy 클래스 테스트
# =====================================================

def test_btc15m_core_v1_metadata(default_config):
    """전략 메타데이터 테스트"""
    strategy = Btc15mCoreV1(default_config)
    metadata = strategy.metadata
    
    assert metadata.strategy_name == 'btc15m_core_v1'
    assert metadata.strategy_type == 'core_and_optional_or'
    assert '15m' in metadata.supported_timeframes
    assert 'BTCUSDT' in metadata.supported_symbols


def test_btc15m_core_v1_compute_signal_insufficient_data(default_config):
    """데이터 부족 시 신호 없음 테스트"""
    strategy = Btc15mCoreV1(default_config)
    
    # 10개 캔들만
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=10, freq='15min'),
        'open': [50000] * 10,
        'high': [50100] * 10,
        'low': [49900] * 10,
        'close': [50000] * 10,
        'volume': [1000] * 10
    })
    
    signal = strategy.compute_signal(df)
    
    assert signal['side'] is None
    assert "데이터 부족" in signal['reason']


# =====================================================
# 통합 테스트
# =====================================================

def test_signal_logic_full_flow_trend_up(sample_df, default_config):
    """Trend-Up 전체 신호 생성 통합 테스트"""
    last_idx = sample_df.index[-1]
    
    # Trend-Up + EMA Pullback 조건 설정
    sample_df.loc[last_idx, 'adx_14'] = 30
    sample_df.loc[last_idx, 'di_plus_14'] = 30
    sample_df.loc[last_idx, 'di_minus_14'] = 20
    sample_df.loc[last_idx, 'atr_14'] = sample_df.iloc[-1]['close'] * 0.003
    sample_df.loc[last_idx, 'volume'] = sample_df['volume'].mean() * 1.5
    
    sample_df.loc[last_idx, 'ema_50'] = 50000
    sample_df.loc[last_idx, 'close'] = 50100
    sample_df.loc[last_idx, 'open'] = 49950
    sample_df.loc[last_idx, 'low'] = 49990
    
    signal = signal_logic(sample_df, default_config)
    
    assert signal['side'] == 'LONG'
    assert signal['entry'] > 0
    assert signal['sl'] < signal['entry']
    assert signal['tp'] > signal['entry']
    assert signal['multi_tp'] is True
    assert len(signal['tp_targets']) == 2
    assert signal['regime'] == 'TREND_UP'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
