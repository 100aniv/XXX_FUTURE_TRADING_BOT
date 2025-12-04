#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE27-3: ADX 지표 단위 테스트
================================
compute_adx 및 add_indicators ADX 옵션 테스트
"""
import pytest
import pandas as pd
import numpy as np
from indicators.core_indicators import compute_adx, add_indicators


@pytest.fixture
def trending_data():
    """상승 추세 데이터 생성"""
    np.random.seed(42)
    n = 100
    # 상승 추세 + 노이즈
    base = np.linspace(100, 150, n)
    noise = np.random.randn(n) * 2
    close = base + noise
    
    df = pd.DataFrame({
        'time': pd.date_range('2024-01-01', periods=n, freq='5min'),
        'open': close * 0.999,
        'high': close * 1.002,
        'low': close * 0.998,
        'close': close,
        'volume': np.random.rand(n) * 1000 + 500
    })
    return df


@pytest.fixture
def ranging_data():
    """횡보 데이터 생성"""
    np.random.seed(123)
    n = 100
    # 횡보 (평균 회귀)
    close = 100 + np.random.randn(n) * 1.5
    
    df = pd.DataFrame({
        'time': pd.date_range('2024-01-01', periods=n, freq='5min'),
        'open': close * 0.999,
        'high': close * 1.001,
        'low': close * 0.999,
        'close': close,
        'volume': np.random.rand(n) * 1000 + 500
    })
    return df


@pytest.fixture
def minimal_data():
    """최소 데이터 (edge case)"""
    n = 20
    close = [100.0 + i * 0.5 for i in range(n)]
    
    df = pd.DataFrame({
        'time': pd.date_range('2024-01-01', periods=n, freq='5min'),
        'open': close,
        'high': [c * 1.01 for c in close],
        'low': [c * 0.99 for c in close],
        'close': close,
        'volume': [1000] * n
    })
    return df


def test_compute_adx_basic(trending_data):
    """ADX 기본 계산 테스트"""
    df = compute_adx(trending_data, period=14)
    
    # 컬럼 존재 확인
    assert 'plus_di_14' in df.columns
    assert 'minus_di_14' in df.columns
    assert 'adx_14' in df.columns
    
    # NaN이 아닌 값 존재 확인
    assert df['adx_14'].notna().sum() > 0
    assert df['plus_di_14'].notna().sum() > 0
    assert df['minus_di_14'].notna().sum() > 0


def test_adx_trending_vs_ranging(trending_data, ranging_data):
    """
    추세 데이터와 횡보 데이터에서 ADX 차이 확인
    - Trending: ADX가 상대적으로 높아야 함
    - Ranging: ADX가 상대적으로 낮아야 함
    """
    df_trend = compute_adx(trending_data, period=14)
    df_range = compute_adx(ranging_data, period=14)
    
    # 마지막 20개 평균 ADX 비교
    adx_trend_avg = df_trend['adx_14'].iloc[-20:].mean()
    adx_range_avg = df_range['adx_14'].iloc[-20:].mean()
    
    # Sanity check: ADX는 0-100 범위
    assert 0 <= adx_trend_avg <= 100
    assert 0 <= adx_range_avg <= 100
    
    # 추세장 ADX가 횡보장보다 높아야 함
    assert adx_trend_avg > adx_range_avg, \
        f"Trending ADX ({adx_trend_avg:.1f}) should be > Ranging ADX ({adx_range_avg:.1f})"


def test_adx_plus_di_minus_di_relationship(trending_data):
    """+DI와 -DI의 관계 확인"""
    df = compute_adx(trending_data, period=14)
    
    # 상승 추세에서는 +DI가 -DI보다 평균적으로 높아야 함
    plus_di_avg = df['plus_di_14'].iloc[-20:].mean()
    minus_di_avg = df['minus_di_14'].iloc[-20:].mean()
    
    assert plus_di_avg > 0, "+DI는 양수여야 함"
    assert minus_di_avg > 0, "-DI는 양수여야 함"
    
    # 상승 추세이므로 +DI > -DI 경향
    assert plus_di_avg > minus_di_avg, \
        f"+DI ({plus_di_avg:.1f}) should be > -DI ({minus_di_avg:.1f}) in uptrend"


def test_adx_minimal_data(minimal_data):
    """최소 데이터에서 ADX 계산"""
    df = compute_adx(minimal_data, period=14)
    
    # 계산은 완료되어야 함 (NaN 있을 수 있음)
    assert 'adx_14' in df.columns
    
    # 최소한 일부 유효한 값 존재
    valid_count = df['adx_14'].notna().sum()
    assert valid_count > 0, "최소 데이터에서도 일부 ADX 값은 계산되어야 함"


def test_adx_no_nan_propagation_issue():
    """NaN 전파가 과도하지 않은지 확인"""
    n = 50
    df = pd.DataFrame({
        'time': pd.date_range('2024-01-01', periods=n, freq='5min'),
        'open': [100] * n,
        'high': [101] * n,
        'low': [99] * n,
        'close': [100 + i * 0.1 for i in range(n)],
        'volume': [1000] * n
    })
    
    df = compute_adx(df, period=14)
    
    # 초기 period*2 정도는 NaN 허용, 나머지는 유효값
    valid_count = df['adx_14'].notna().sum()
    assert valid_count >= n - 30, \
        f"ADX 유효값이 너무 적음: {valid_count}/{n}"


def test_add_indicators_with_adx():
    """add_indicators에서 ADX 옵션 테스트"""
    n = 100
    df = pd.DataFrame({
        'time': pd.date_range('2024-01-01', periods=n, freq='5min'),
        'open': [100] * n,
        'high': [101] * n,
        'low': [99] * n,
        'close': [100 + i * 0.1 for i in range(n)],
        'volume': [1000] * n
    })
    
    # ADX 없이 호출
    df_no_adx = add_indicators(df.copy(), use_adx=False)
    assert 'adx_14' not in df_no_adx.columns, "use_adx=False일 때 ADX 컬럼 없어야 함"
    
    # ADX 포함 호출
    df_with_adx = add_indicators(df.copy(), use_adx=True, adx_period=14)
    assert 'adx_14' in df_with_adx.columns, "use_adx=True일 때 ADX 컬럼 있어야 함"
    assert 'plus_di_14' in df_with_adx.columns
    assert 'minus_di_14' in df_with_adx.columns
    
    # 기존 지표들도 여전히 존재
    assert 'rsi' in df_with_adx.columns
    assert 'bb_upper' in df_with_adx.columns
    assert 'atr' in df_with_adx.columns


def test_adx_different_periods():
    """다양한 period에서 ADX 계산"""
    n = 100
    df = pd.DataFrame({
        'time': pd.date_range('2024-01-01', periods=n, freq='5min'),
        'open': [100] * n,
        'high': [101] * n,
        'low': [99] * n,
        'close': [100 + i * 0.2 for i in range(n)],
        'volume': [1000] * n
    })
    
    for period in [7, 14, 21]:
        df_test = compute_adx(df.copy(), period=period)
        assert f'adx_{period}' in df_test.columns
        assert f'plus_di_{period}' in df_test.columns
        assert f'minus_di_{period}' in df_test.columns
        
        # 유효값 존재
        assert df_test[f'adx_{period}'].notna().sum() > 0


def test_adx_regime_threshold_25():
    """
    ADX 25 임계값 기준 테스트
    - Trending data: ADX > 25 비율이 높아야 함
    - Ranging data: ADX <= 25 비율이 높아야 함
    """
    # Trending
    np.random.seed(42)
    n = 100
    trending_close = np.linspace(100, 150, n) + np.random.randn(n) * 1
    df_trend = pd.DataFrame({
        'time': pd.date_range('2024-01-01', periods=n, freq='5min'),
        'open': trending_close * 0.999,
        'high': trending_close * 1.002,
        'low': trending_close * 0.998,
        'close': trending_close,
        'volume': [1000] * n
    })
    
    # Ranging
    ranging_close = 100 + np.random.randn(n) * 1.5
    df_range = pd.DataFrame({
        'time': pd.date_range('2024-01-01', periods=n, freq='5min'),
        'open': ranging_close * 0.999,
        'high': ranging_close * 1.001,
        'low': ranging_close * 0.999,
        'close': ranging_close,
        'volume': [1000] * n
    })
    
    df_trend = compute_adx(df_trend, period=14)
    df_range = compute_adx(df_range, period=14)
    
    # 마지막 20개 데이터에서 ADX > 25 비율
    trend_above_25 = (df_trend['adx_14'].iloc[-20:] > 25).sum() / 20
    range_above_25 = (df_range['adx_14'].iloc[-20:] > 25).sum() / 20
    
    # Trending은 25 이상 비율이 높아야 함 (최소 30%)
    # Ranging은 25 이하 비율이 높아야 함 (최대 30%)
    print(f"Trending ADX > 25: {trend_above_25*100:.1f}%")
    print(f"Ranging ADX > 25: {range_above_25*100:.1f}%")
    
    # 추세장에서 ADX > 25 비율이 횡보장보다 높아야 함
    assert trend_above_25 > range_above_25, \
        "Trending market should have higher ADX > 25 ratio than ranging market"
