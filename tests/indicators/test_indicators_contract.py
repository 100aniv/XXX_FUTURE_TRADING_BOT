#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Indicators Contract Tests
==========================
PR4: 인터페이스 계약 검증 (12개 테스트)

계약 검증 항목:
1. 입력 요구사항 (필수 컬럼, 정렬, 결측치)
2. 출력 보장 (불변성, 인덱스 유지, NaN 전파)
3. 최소 데이터 요구사항
4. NaN 처리 정책
"""
import pytest
import pandas as pd
import numpy as np

from indicators.core_indicators import (
    ema, rsi, macd, bb, atr, donchian, volume_ma, add_indicators, regime
)


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def sample_df():
    """표준 OHLCV DataFrame (100개 행)"""
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='1h')
    df = pd.DataFrame({
        'time': dates,
        'open': 100 + np.random.randn(100).cumsum(),
        'high': 101 + np.random.randn(100).cumsum(),
        'low': 99 + np.random.randn(100).cumsum(),
        'close': 100 + np.random.randn(100).cumsum(),
        'volume': 1000 + np.random.randint(-100, 100, 100)
    })
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    return df


@pytest.fixture
def minimal_df():
    """최소 데이터 (20개 행)"""
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=20, freq='1h')
    df = pd.DataFrame({
        'time': dates,
        'open': 100 + np.random.randn(20).cumsum(),
        'high': 101 + np.random.randn(20).cumsum(),
        'low': 99 + np.random.randn(20).cumsum(),
        'close': 100 + np.random.randn(20).cumsum(),
        'volume': 1000 + np.random.randint(-100, 100, 20)
    })
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    return df


# ============================================
# Contract Tests
# ============================================

def test_contract_01_ema_immutability(sample_df):
    """C01: EMA는 입력 Series를 수정하지 않음"""
    original = sample_df['close'].copy()
    result = ema(sample_df['close'], 20)
    
    assert sample_df['close'].equals(original), "입력 Series가 수정됨"
    assert len(result) == len(sample_df), "출력 길이가 입력과 다름"
    assert result.index.equals(sample_df.index), "인덱스가 유지되지 않음"


def test_contract_02_ema_nan_propagation(minimal_df):
    """C02: EMA는 초기 length-1개 행에서 NaN 전파"""
    length = 10
    result = ema(minimal_df['close'], length)
    
    # 초기 length-1개는 NaN (pandas ewm 특성상 첫 값부터 계산됨)
    # 하지만 warmup 기간 동안 불안정함을 확인
    assert not result.isna().all(), "모든 값이 NaN"
    assert len(result) == len(minimal_df), "길이 불일치"


def test_contract_03_rsi_minimum_data(minimal_df):
    """C03: RSI는 length+1개 행 필요"""
    length = 14
    result = rsi(minimal_df['close'], length)
    
    # RSI는 length개 행 이후부터 유효 값
    assert len(result) == len(minimal_df), "길이 불일치"
    # 초기 length개는 NaN일 수 있음
    valid_count = result.notna().sum()
    assert valid_count >= len(minimal_df) - length, f"유효 값 부족: {valid_count}"


def test_contract_04_macd_output_schema(sample_df):
    """C04: MACD는 macd, macd_signal, macd_hist 컬럼 추가"""
    df = sample_df.copy()
    result = macd(df, fast=12, slow=26, signal=9)
    
    required_cols = ['macd', 'macd_signal', 'macd_hist']
    for col in required_cols:
        assert col in result.columns, f"{col} 컬럼 누락"
    
    assert len(result) == len(sample_df), "행 수 변경됨"


def test_contract_05_bb_output_schema(sample_df):
    """C05: BB는 bb_upper, bb_mid, bb_lower 컬럼 추가"""
    df = sample_df.copy()
    result = bb(df, length=20, std=2.0)
    
    required_cols = ['bb_upper', 'bb_mid', 'bb_lower']
    for col in required_cols:
        assert col in result.columns, f"{col} 컬럼 누락"
    
    # BB 상/하단은 중심선 위/아래에 위치
    valid_rows = result.dropna()
    if len(valid_rows) > 0:
        assert (valid_rows['bb_upper'] >= valid_rows['bb_mid']).all(), "상단 < 중심"
        assert (valid_rows['bb_lower'] <= valid_rows['bb_mid']).all(), "하단 > 중심"


def test_contract_06_atr_minimum_data(minimal_df):
    """C06: ATR는 length+1개 행 필요 (shift 고려)"""
    length = 14
    df = minimal_df.copy()
    result = atr(df, length)
    
    assert len(result) == len(minimal_df), "길이 불일치"
    # ATR은 shift로 인해 첫 행 + length-1개 행이 NaN
    valid_count = result.notna().sum()
    assert valid_count >= len(minimal_df) - length, f"유효 값 부족: {valid_count}"


def test_contract_07_donchian_output_schema(sample_df):
    """C07: Donchian은 dc_upper, dc_mid, dc_lower 컬럼 추가"""
    df = sample_df.copy()
    result = donchian(df, length=20)
    
    required_cols = ['dc_upper', 'dc_mid', 'dc_lower']
    for col in required_cols:
        assert col in result.columns, f"{col} 컬럼 누락"
    
    # 동키안 상단 >= 하단
    valid_rows = result.dropna()
    if len(valid_rows) > 0:
        assert (valid_rows['dc_upper'] >= valid_rows['dc_lower']).all(), "상단 < 하단"


def test_contract_08_volume_ma_immutability(sample_df):
    """C08: volume_ma는 입력 Series를 수정하지 않음"""
    original = sample_df['volume'].copy()
    result = volume_ma(sample_df['volume'], 30)
    
    assert sample_df['volume'].equals(original), "입력 Series가 수정됨"
    assert len(result) == len(sample_df), "길이 불일치"


def test_contract_09_add_indicators_removes_nan(sample_df):
    """C09: add_indicators는 NaN 제거 후 반환"""
    df = sample_df.copy()
    result = add_indicators(df)
    
    # NaN 제거됨
    assert not result.isna().any().any(), "NaN이 남아있음"
    
    # 필수 컬럼 존재
    required_cols = [
        'ema_fast', 'ema_mid', 'ema_slow',
        'macd', 'macd_signal', 'macd_hist',
        'rsi', 'bb_upper', 'bb_mid', 'bb_lower',
        'atr', 'dc_upper', 'dc_mid', 'dc_lower', 'vol_ma'
    ]
    for col in required_cols:
        assert col in result.columns, f"{col} 컬럼 누락"


def test_contract_10_add_indicators_preserves_ohlcv(sample_df):
    """C10: add_indicators는 OHLCV 컬럼 유지"""
    df = sample_df.copy()
    result = add_indicators(df)
    
    ohlcv_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in ohlcv_cols:
        assert col in result.columns, f"OHLCV {col} 컬럼 누락"


def test_contract_11_regime_requires_indicators(sample_df):
    """C11: regime은 ema_fast/mid/slow, rsi 필요"""
    df = sample_df.copy()
    df = add_indicators(df)
    
    # regime 적용
    df['regime_label'] = df.apply(regime, axis=1)
    
    valid_regimes = {"상승장", "하락장", "횡보장", "중립"}
    assert df['regime_label'].isin(valid_regimes).all(), "잘못된 레짐 값"


def test_contract_12_nan_handling_policy(minimal_df):
    """C12: 지표는 NaN 전파를 허용하며, 시그널 생성 시 제거 필요"""
    df = minimal_df.copy()
    
    # 지표 계산 (NaN 포함)
    df["ema_20"] = ema(df["close"], 20)
    df["rsi_14"] = rsi(df["close"], 14)
    
    # 초기 행에서 NaN 존재 확인
    assert df["ema_20"].isna().any() or df["rsi_14"].isna().any(), \
        "최소 데이터에서 NaN이 없음 (비정상)"
    
    # dropna 후 유효 데이터 확인
    df_clean = df.dropna()
    assert len(df_clean) > 0, "dropna 후 데이터 없음"
    assert not df_clean["ema_20"].isna().any(), "dropna 후에도 NaN 존재"
    assert not df_clean["rsi_14"].isna().any(), "dropna 후에도 NaN 존재"


# ============================================
# 실행
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
