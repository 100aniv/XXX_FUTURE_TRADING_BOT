#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Factor Calculator
=================
PHASE19-2: 시장 상황을 계량화하는 6개 Factor 계산

**Factor 목록**:
- momentum: 가격 모멘텀 강도
- volatility: 변동성 수준
- volume: 거래량 급증도
- trend_strength: 추세 강도
- overbought_oversold: RSI 극단 정도
- breakout_probability: 돌파 확률
"""
from typing import Dict
import pandas as pd
import numpy as np

FactorDict = Dict[str, float]


def _sigmoid(x: float, k: float = 1.0) -> float:
    """Sigmoid 함수로 값을 0~1로 정규화"""
    return 1.0 / (1.0 + np.exp(-k * x))


def _clip_01(x: float) -> float:
    """값을 0~1 범위로 클리핑"""
    return max(0.0, min(1.0, x))


def compute_momentum_factor(df: pd.DataFrame, lookback: int = 20) -> float:
    """
    가격 모멘텀 강도 (0~1)
    
    계산: (close - close[lookback]) / ATR
    정규화: sigmoid(x, k=0.5) → 0~1
    
    Args:
        df: OHLCV + ATR 포함
        lookback: 모멘텀 계산 기간 (default: 20)
    
    Returns:
        momentum_factor: 0~1 (상승 모멘텀 강할수록 1에 근접)
    """
    if len(df) < lookback + 1:
        return 0.5  # 데이터 부족 시 중립

    last = df.iloc[-1]
    prev = df.iloc[-lookback-1]
    
    close_now = float(last["close"])
    close_prev = float(prev["close"])
    atr = float(last.get("atr", 1.0))
    
    if atr == 0:
        return 0.5  # ATR 0이면 중립
    
    momentum_raw = (close_now - close_prev) / atr
    
    # Sigmoid로 0~1 정규화 (k=0.5: 완만하게)
    return _sigmoid(momentum_raw, k=0.5)


def compute_volatility_factor(df: pd.DataFrame, window: int = 20) -> float:
    """
    변동성 수준 (0~1)
    
    계산: ATR percentile(window)
    정규화: percentile rank → 0~1
    
    Args:
        df: OHLCV + ATR 포함
        window: percentile 계산 기간
    
    Returns:
        volatility_factor: 0~1 (높은 변동성일수록 1에 근접)
    """
    if len(df) < window:
        return 0.5  # 데이터 부족 시 중립
    
    recent_df = df.iloc[-window:]
    atr_series = recent_df["atr"].astype(float)
    
    current_atr = float(df.iloc[-1]["atr"])
    
    # Percentile rank 계산
    rank = (atr_series < current_atr).sum()
    percentile = rank / len(atr_series)
    
    return _clip_01(percentile)


def compute_volume_factor(df: pd.DataFrame, ma_window: int = 20) -> float:
    """
    거래량 급증도 (0~1)
    
    계산: (volume / vol_ma) - 1
    정규화: clip to 0~1 (2배 이상이면 1.0)
    
    Args:
        df: OHLCV + vol_ma 포함
        ma_window: 거래량 MA 기간 (사용 안함, df에 vol_ma 있다고 가정)
    
    Returns:
        volume_factor: 0~1 (거래량 급증일수록 1에 근접)
    """
    if len(df) < 2:
        return 0.5  # 데이터 부족 시 중립
    
    last = df.iloc[-1]
    volume = float(last.get("volume", 0))
    vol_ma = float(last.get("vol_ma", 1.0))
    
    if vol_ma == 0:
        return 0.5  # vol_ma 0이면 중립
    
    # volume / vol_ma - 1 → 0~1로 스케일 (2배 이상이면 1.0)
    ratio = (volume / vol_ma) - 1.0
    
    # 0~1 범위로 정규화 (2배 = 1.0)
    normalized = ratio / 1.0  # ratio=1.0(2배) → 1.0
    
    return _clip_01(normalized)


def compute_trend_strength_factor(
    df: pd.DataFrame,
    fast_col: str = "ema_fast",
    slow_col: str = "ema_slow"
) -> float:
    """
    추세 강도 (0~1)
    
    계산: (ema_fast - ema_slow) / ATR
    정규화: sigmoid(x, k=0.5) → 0~1
    
    Args:
        df: OHLCV + EMA + ATR 포함
        fast_col: Fast EMA 컬럼명
        slow_col: Slow EMA 컬럼명
    
    Returns:
        trend_strength_factor: 0~1 (상승 추세 강할수록 1에 근접)
    """
    if len(df) < 1:
        return 0.5  # 데이터 부족 시 중립
    
    last = df.iloc[-1]
    
    # EMA 컬럼 존재 여부 확인
    if fast_col not in df.columns or slow_col not in df.columns:
        return 0.5  # EMA 없으면 중립
    
    ema_fast = float(last[fast_col])
    ema_slow = float(last[slow_col])
    atr = float(last.get("atr", 1.0))
    
    if atr == 0:
        return 0.5  # ATR 0이면 중립
    
    trend_raw = (ema_fast - ema_slow) / atr
    
    # Sigmoid로 0~1 정규화
    return _sigmoid(trend_raw, k=0.5)


def compute_overbought_oversold_factor(
    df: pd.DataFrame,
    rsi_col: str = "rsi"
) -> float:
    """
    RSI 극단 정도 (0~1)
    
    계산: abs(RSI - 50) / 50
    정규화: 0~1 (RSI 0 or 100이면 1.0, RSI 50이면 0.0)
    
    Args:
        df: OHLCV + RSI 포함
        rsi_col: RSI 컬럼명
    
    Returns:
        overbought_oversold_factor: 0~1 (극단값일수록 1에 근접)
    """
    if len(df) < 1:
        return 0.0  # 데이터 부족 시 0
    
    last = df.iloc[-1]
    
    # RSI 컬럼 존재 여부 확인
    if rsi_col not in df.columns:
        return 0.0  # RSI 없으면 0
    
    rsi = float(last[rsi_col])
    
    # abs(RSI - 50) / 50 → 0~1
    extremeness = abs(rsi - 50.0) / 50.0
    
    return _clip_01(extremeness)


def compute_breakout_probability_factor(
    df: pd.DataFrame,
    dc_upper_col: str = "dc_upper",
    dc_lower_col: str = "dc_lower"
) -> float:
    """
    돌파 확률 (0~1)
    
    계산: (close - dc_mid) / (dc_upper - dc_lower)
    정규화: -1~1 → 0~1 (상단 돌파 = 1.0, 하단 돌파 = 0.0, 중간 = 0.5)
    
    Args:
        df: OHLCV + Donchian Channel 포함
        dc_upper_col: Donchian 상단 컬럼명
        dc_lower_col: Donchian 하단 컬럼명
    
    Returns:
        breakout_probability_factor: 0~1 (상단 돌파일수록 1에 근접)
    """
    if len(df) < 1:
        return 0.5  # 데이터 부족 시 중립
    
    last = df.iloc[-1]
    
    # Donchian 컬럼 존재 여부 확인
    if dc_upper_col not in df.columns or dc_lower_col not in df.columns:
        return 0.5  # Donchian 없으면 중립
    
    close = float(last["close"])
    dc_upper = float(last[dc_upper_col])
    dc_lower = float(last[dc_lower_col])
    
    if dc_upper == dc_lower:
        return 0.5  # 채널 폭 0이면 중립
    
    dc_mid = (dc_upper + dc_lower) / 2.0
    dc_range = dc_upper - dc_lower
    
    # (close - dc_mid) / (dc_range / 2) → -1~1
    # -1~1 → 0~1로 변환
    normalized = ((close - dc_mid) / (dc_range / 2.0) + 1.0) / 2.0
    
    return _clip_01(normalized)


def compute_all_factors(df: pd.DataFrame) -> FactorDict:
    """
    모든 Factor 계산 (마지막 row 기준)
    
    Args:
        df: OHLCV + 지표 (ATR, EMA, RSI, vol_ma, Donchian 등) 포함
    
    Returns:
        FactorDict: 6개 Factor 값 dict (각 0~1 범위)
    """
    return {
        "momentum": compute_momentum_factor(df),
        "volatility": compute_volatility_factor(df),
        "volume": compute_volume_factor(df),
        "trend_strength": compute_trend_strength_factor(df),
        "overbought_oversold": compute_overbought_oversold_factor(df),
        "breakout_probability": compute_breakout_probability_factor(df),
    }
