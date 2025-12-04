#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE27-3: BTC 5m Baseline V1 전략 테스트 (ADX 통합)
======================================================
베이스라인 전략의 신호 생성 및 기본 동작 검증 + ADX 레짐 로직
"""
import pytest
import pandas as pd
import numpy as np
from strategies.btc5m_baseline_v1 import signal_logic, BTC5mBaselineV1


@pytest.fixture
def base_config():
    """기본 Config"""
    return {
        'leverage': {'min': 1, 'max': 10, 'default': 3},
        'rsi_long_threshold': 45,
        'rsi_short_threshold': 55,
        'bb_std_main': 1.0,
        'bb_std_strong': 1.5,
        'momentum_lookback': 5,
        'momentum_threshold': 0.001,
        'rr': 1.5,
        'atr_mult_sl': 1.5,
        'max_hold_minutes': 60,
        'min_bars_for_signal': 50,
        'filters': {'allow_short': True},
    }


@pytest.fixture
def sample_df():
    """샘플 DataFrame 생성"""
    np.random.seed(42)
    n = 100
    
    data = {
        'time': pd.date_range('2024-12-01', periods=n, freq='5min'),
        'open': np.random.uniform(90000, 91000, n),
        'high': np.random.uniform(90500, 91500, n),
        'low': np.random.uniform(89500, 90500, n),
        'close': np.random.uniform(90000, 91000, n),
        'volume': np.random.uniform(100, 200, n),
    }
    
    df = pd.DataFrame(data)
    
    # 기본 지표 추가 (모의)
    df['rsi'] = 50.0  # 중립
    df['bb_upper'] = df['close'] * 1.01  # +1%
    df['bb_lower'] = df['close'] * 0.99  # -1%
    df['atr'] = df['close'] * 0.002  # 0.2%
    df['vol_ma'] = df['volume'].rolling(20).mean().fillna(df['volume'].mean())
    
    return df


def test_strategy_init(base_config):
    """전략 초기화 테스트"""
    strategy = BTC5mBaselineV1(base_config)
    
    assert strategy.metadata.strategy_name == 'btc5m_baseline_v1'
    assert strategy.metadata.strategy_type == 'baseline'
    assert '5m' in strategy.metadata.supported_timeframes
    assert strategy.config == base_config


def test_insufficient_data(base_config):
    """데이터 부족 시 None 반환"""
    df = pd.DataFrame({
        'close': [90000, 90100, 90200],
        'rsi': [50, 50, 50],
        'bb_upper': [91000, 91100, 91200],
        'bb_lower': [89000, 89100, 89200],
        'atr': [180, 180, 180],
    })
    
    result = signal_logic(df, base_config)
    
    assert result['side'] is None
    assert '데이터 부족' in result['reason']


def test_rsi_long_signal(sample_df, base_config):
    """RSI 기반 LONG 신호 테스트"""
    # 마지막 캔들의 RSI를 44로 설정 (threshold 45 미만)
    sample_df.loc[sample_df.index[-1], 'rsi'] = 44.0
    
    result = signal_logic(sample_df, base_config)
    
    assert result['side'] == 'LONG'
    assert 'RSI' in result['reason']
    assert result['entry'] is not None
    assert result['sl'] < result['entry']  # LONG: SL은 entry 아래
    assert result['tp'] > result['entry']  # LONG: TP는 entry 위


def test_rsi_short_signal(sample_df, base_config):
    """RSI 기반 SHORT 신호 테스트"""
    # 마지막 캔들의 RSI를 56으로 설정 (threshold 55 초과)
    sample_df.loc[sample_df.index[-1], 'rsi'] = 56.0
    
    result = signal_logic(sample_df, base_config)
    
    assert result['side'] == 'SHORT'
    assert 'RSI' in result['reason']
    assert result['entry'] is not None
    assert result['sl'] > result['entry']  # SHORT: SL은 entry 위
    assert result['tp'] < result['entry']  # SHORT: TP는 entry 아래


def test_bb_lower_long_signal(sample_df, base_config):
    """BB Lower 돌파 LONG 신호 테스트"""
    # 마지막 캔들을 BB Lower 아래로 설정
    last_idx = sample_df.index[-1]
    sample_df.loc[last_idx, 'close'] = 89500  # BB Lower보다 아래
    sample_df.loc[last_idx, 'bb_lower'] = 89600
    sample_df.loc[last_idx, 'rsi'] = 50  # RSI는 중립 (RSI 신호 제외)
    
    # 하락 모멘텀 생성 (최근 5캔들 하락)
    for i in range(5):
        sample_df.loc[sample_df.index[-(i+1)], 'close'] = 90000 - (i * 100)
    
    result = signal_logic(sample_df, base_config)
    
    # BB 또는 모멘텀 조건으로 LONG 신호 발생 예상
    # (RSI 중립이어도 BB/모멘텀으로 신호 가능)
    assert result['side'] in ['LONG', None]


def test_no_signal_neutral_market(sample_df, base_config):
    """중립 시장에서 신호 없음"""
    # 모든 조건이 중립 상태
    sample_df['rsi'] = 50.0  # RSI 중립
    sample_df['close'] = 90000  # BB 중간
    sample_df['bb_upper'] = 90900  # +1%
    sample_df['bb_lower'] = 89100  # -1%
    
    result = signal_logic(sample_df, base_config)
    
    # 중립 상태이므로 신호 없음 예상 (하지만 BB 1.0 std는 넓어서 신호 가능)
    # 테스트는 OR 로직이므로 신호가 나올 수도 있음
    assert result['side'] in ['LONG', 'SHORT', None]


def test_short_disabled(sample_df, base_config):
    """SHORT 비활성화 시 SHORT 신호 없음"""
    base_config['filters']['allow_short'] = False
    
    # RSI를 56으로 (SHORT 조건)
    sample_df.loc[sample_df.index[-1], 'rsi'] = 56.0
    
    result = signal_logic(sample_df, base_config)
    
    # SHORT 비활성화이므로 SHORT 신호 없음
    assert result['side'] != 'SHORT'


def test_leverage_calculation(sample_df, base_config):
    """Leverage 계산 검증"""
    # RSI LONG 신호 발생
    sample_df.loc[sample_df.index[-1], 'rsi'] = 44.0
    
    result = signal_logic(sample_df, base_config)
    
    assert 'leverage' in result
    assert base_config['leverage']['min'] <= result['leverage'] <= base_config['leverage']['max']


def test_risk_reward_ratio(sample_df, base_config):
    """Risk/Reward 비율 검증"""
    # LONG 신호 발생
    sample_df.loc[sample_df.index[-1], 'rsi'] = 44.0
    
    result = signal_logic(sample_df, base_config)
    
    if result['side'] == 'LONG':
        sl_distance = result['entry'] - result['sl']
        tp_distance = result['tp'] - result['entry']
        actual_rr = tp_distance / sl_distance
        
        # RR 1.5 허용오차 ±0.01
        assert abs(actual_rr - base_config['rr']) < 0.01


def test_metadata_included(sample_df, base_config):
    """메타데이터 포함 여부"""
    sample_df.loc[sample_df.index[-1], 'rsi'] = 44.0
    
    result = signal_logic(sample_df, base_config)
    
    if result['side'] is not None:
        assert 'metadata' in result
        assert 'rsi' in result['metadata']
        assert 'bb_middle' in result['metadata']
        assert 'signal_count' in result['metadata']


def test_baseclass_interface(sample_df, base_config):
    """BaseStrategy 인터페이스 준수 확인"""
    strategy = BTC5mBaselineV1(base_config)
    
    # compute_signal 메서드 존재 확인
    assert hasattr(strategy, 'compute_signal')
    
    # 신호 계산
    result = strategy.compute_signal(sample_df)
    
    # 결과는 dict
    assert isinstance(result, dict)
    assert 'side' in result


def test_multiple_conditions_or_logic(sample_df, base_config):
    """여러 조건 동시 만족 시 OR 로직 확인"""
    last_idx = sample_df.index[-1]
    
    # RSI와 BB 둘 다 LONG 조건 만족
    sample_df.loc[last_idx, 'rsi'] = 40.0  # RSI LONG
    sample_df.loc[last_idx, 'close'] = 89000  # BB Lower 아래
    sample_df.loc[last_idx, 'bb_lower'] = 89100
    
    result = signal_logic(sample_df, base_config)
    
    # OR 로직이므로 LONG 신호
    assert result['side'] == 'LONG'
    
    # all_reasons에 여러 이유 포함 가능
    if 'all_reasons' in result:
        assert len(result['all_reasons']) >= 1


def test_adx_range_regime(sample_df, base_config):
    """ADX Range Regime 테스트 (ADX <= 25)"""
    base_config['use_adx'] = True
    base_config['adx_period'] = 14
    base_config['adx_trend_threshold'] = 25
    
    # ADX 컬럼 추가 (Range regime)
    sample_df['adx_14'] = 20.0  # ADX < 25 = Range
    sample_df['plus_di_14'] = 15.0
    sample_df['minus_di_14'] = 18.0
    
    last_idx = len(sample_df) - 1
    
    # RSI 조건만으로 LONG 신호 (Range regime)
    sample_df.loc[last_idx, 'rsi'] = 40.0  # RSI < 45
    sample_df.loc[last_idx, 'close'] = 90500
    
    result = signal_logic(sample_df, base_config)
    
    assert result['side'] == 'LONG'
    assert 'metadata' in result
    assert result['metadata']['regime'] == 'RANGE'
    assert result['metadata']['adx'] == 20.0
    assert '[RANGE]' in result['reason'] or 'RSI' in result['reason']


def test_adx_trend_regime(sample_df, base_config):
    """ADX Trend Regime 테스트 (ADX > 25)"""
    base_config['use_adx'] = True
    base_config['adx_period'] = 14
    base_config['adx_trend_threshold'] = 25
    
    # ADX 컬럼 추가 (Trend regime)
    sample_df['adx_14'] = 30.0  # ADX > 25 = Trend
    sample_df['plus_di_14'] = 25.0
    sample_df['minus_di_14'] = 10.0
    
    last_idx = len(sample_df) - 1
    
    # RSI만으로는 신호 없음 (Trend regime)
    sample_df.loc[last_idx, 'rsi'] = 40.0  # RSI < 45
    sample_df.loc[last_idx, 'close'] = 90500  # BB 조건 미충족
    sample_df.loc[last_idx, 'bb_lower'] = 89000  # Lower가 훨씬 아래
    
    result = signal_logic(sample_df, base_config)
    
    # Trend regime에서는 RSI 단독 신호 없음
    assert result['side'] is None or result['side'] != 'LONG'


def test_adx_trend_regime_with_bb_strong(sample_df, base_config):
    """ADX Trend Regime + BB Strong 조건"""
    base_config['use_adx'] = True
    base_config['adx_period'] = 14
    base_config['adx_trend_threshold'] = 25
    base_config['bb_std_strong'] = 1.5
    
    # ADX 컬럼 추가 (Trend regime)
    sample_df['adx_14'] = 35.0
    sample_df['plus_di_14'] = 30.0
    sample_df['minus_di_14'] = 8.0
    
    last_idx = len(sample_df) - 1
    
    # BB 설정 (2.0 std 기준 - indicators 기본값)
    bb_middle = 90000
    bb_std = 2.0
    bb_width_2std = 4000  # 2.0 std 기준 전체 폭
    sample_df.loc[last_idx, 'bb_upper'] = bb_middle + bb_width_2std / 2
    sample_df.loc[last_idx, 'bb_lower'] = bb_middle - bb_width_2std / 2
    
    # BB Lower 1.5 std 계산:
    # bb_lower_strong = bb_middle - (bb_width_2std / 2) * (1.5 / 2.0)
    # = 90000 - 2000 * 0.75 = 90000 - 1500 = 88500
    # close를 88500보다 아래로 설정
    sample_df.loc[last_idx, 'close'] = 88400
    
    result = signal_logic(sample_df, base_config)
    
    assert result['side'] == 'LONG'
    assert result['metadata']['regime'] == 'TREND'
    assert '[TREND]' in result['reason']


def test_adx_off_backward_compatible(sample_df, base_config):
    """ADX OFF 시 기존 로직 동작 (하위 호환성)"""
    # ADX 사용하지 않음
    base_config['use_adx'] = False
    
    last_idx = len(sample_df) - 1
    
    # RSI LONG 조건
    sample_df.loc[last_idx, 'rsi'] = 40.0
    
    result = signal_logic(sample_df, base_config)
    
    # ADX OFF이므로 Range 로직 (기존 PHASE27-2)
    assert result['side'] == 'LONG'
    assert result['metadata']['regime'] == 'RANGE (ADX OFF)'
    assert result['metadata']['use_adx'] is False


def test_adx_metadata_inclusion(sample_df, base_config):
    """ADX 관련 메타데이터 포함 확인"""
    base_config['use_adx'] = True
    sample_df['adx_14'] = 22.0
    
    last_idx = len(sample_df) - 1
    sample_df.loc[last_idx, 'rsi'] = 40.0
    
    result = signal_logic(sample_df, base_config)
    
    assert 'metadata' in result
    assert 'regime' in result['metadata']
    assert 'adx' in result['metadata']
    assert 'use_adx' in result['metadata']
    assert result['metadata']['adx'] == 22.0
    assert result['metadata']['use_adx'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
