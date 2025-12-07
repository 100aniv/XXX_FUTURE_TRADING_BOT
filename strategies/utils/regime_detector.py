#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regime Detector for btc5m_baseline_v2
======================================
시장 레짐 6-state 분류 모듈

Regime States (6):
- bull_high_vol: 상승 추세 + 높은 변동성
- bull_low_vol: 상승 추세 + 낮은 변동성
- bear_high_vol: 하락 추세 + 높은 변동성
- bear_low_vol: 하락 추세 + 낮은 변동성
- range_high_vol: 횡보 + 높은 변동성
- range_low_vol: 횡보 + 낮은 변동성

Detection Logic:
1. ADX + DI+/DI- → Trend Direction (bull/bear/range)
2. ATR percentile → Volatility Level (high/low)
3. Combine → 6-state regime
"""
import pandas as pd
import numpy as np
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def detect_regime(df: pd.DataFrame, config: dict) -> Dict[str, Any]:
    """
    6-state Regime Detection
    
    Args:
        df: OHLCV + 지표가 포함된 DataFrame (ADX, DI+, DI-, ATR 필요)
        config: 전략 설정
            - adx_period: ADX 계산 기간 (기본 14)
            - adx_trend_threshold: Trend vs Range 분류 threshold (기본 25)
            - di_diff_threshold: DI+/DI- 차이 threshold (기본 5)
            - atr_high_threshold: High Volatility percentile threshold (기본 70)
            - atr_lookback: ATR percentile 계산 lookback (기본 100)
    
    Returns:
        dict: {
            'regime': str ('bull_high_vol' | 'bull_low_vol' | 'bear_high_vol' | 
                          'bear_low_vol' | 'range_high_vol' | 'range_low_vol'),
            'trend': str ('bull' | 'bear' | 'range'),
            'volatility': str ('high_vol' | 'low_vol'),
            'adx': float,
            'di_plus': float,
            'di_minus': float,
            'atr_pct': float,
            'atr_percentile': float
        }
    """
    # Config 로드
    adx_period = config.get('adx_period', 14)
    adx_trend_threshold = config.get('adx_trend_threshold', 25)
    di_diff_threshold = config.get('di_diff_threshold', 5)
    atr_high_threshold = config.get('atr_high_threshold', 70)
    atr_lookback = config.get('atr_lookback', 100)
    
    # 현재 캔들
    last = df.iloc[-1]
    price = float(last['close'])
    
    # === 1. Trend Direction (ADX + DI+/DI-) ===
    adx_col = f"adx_{adx_period}"
    di_plus_col = f"plus_di_{adx_period}"
    di_minus_col = f"minus_di_{adx_period}"
    
    # ADX/DI 컬럼 확인
    if adx_col not in last.index or di_plus_col not in last.index or di_minus_col not in last.index:
        logger.warning(f"ADX/DI columns not found. Using default 'range_low_vol' regime.")
        return {
            'regime': 'range_low_vol',
            'trend': 'range',
            'volatility': 'low_vol',
            'adx': None,
            'di_plus': None,
            'di_minus': None,
            'atr_pct': None,
            'atr_percentile': None
        }
    
    adx = float(last[adx_col])
    di_plus = float(last[di_plus_col])
    di_minus = float(last[di_minus_col])
    
    # Trend 판정
    if adx >= adx_trend_threshold:
        # Strong Trend
        if di_plus > di_minus:
            trend = "bull"
        else:
            trend = "bear"
    else:
        # Range or Weak Trend
        di_diff = di_plus - di_minus
        if di_diff > di_diff_threshold:
            trend = "bull"
        elif di_diff < -di_diff_threshold:
            trend = "bear"
        else:
            trend = "range"
    
    # === 2. Volatility Level (ATR percentile) ===
    atr_col = f"atr_{adx_period}"  # ADX와 같은 기간 사용
    if atr_col not in last.index:
        logger.warning(f"ATR column '{atr_col}' not found. Using default 'low_vol'.")
        volatility = "low_vol"
        atr_pct = None
        atr_percentile = None
    else:
        atr = float(last[atr_col])
        atr_pct = atr / price
        
        # ATR percentile 계산 (최근 N바 기준)
        atr_pct_series = df[atr_col] / df['close']
        lookback_data = atr_pct_series.iloc[-atr_lookback:] if len(atr_pct_series) >= atr_lookback else atr_pct_series
        atr_percentile = _percentile_rank(lookback_data, atr_pct)
        
        # Volatility 판정
        if atr_percentile >= atr_high_threshold:
            volatility = "high_vol"
        else:
            volatility = "low_vol"
    
    # === 3. Regime 조합 ===
    regime = f"{trend}_{volatility}"
    
    return {
        'regime': regime,
        'trend': trend,
        'volatility': volatility,
        'adx': adx,
        'di_plus': di_plus,
        'di_minus': di_minus,
        'atr_pct': atr_pct,
        'atr_percentile': atr_percentile
    }


def _percentile_rank(series: pd.Series, value: float) -> float:
    """
    시리즈에서 value의 percentile 순위 계산
    
    Args:
        series: pandas Series
        value: 순위를 계산할 값
    
    Returns:
        percentile: 0-100 사이의 값 (value가 시리즈에서 차지하는 백분위)
    """
    if len(series) == 0:
        return 50.0  # Default to median
    
    count_below = (series < value).sum()
    percentile = (count_below / len(series)) * 100.0
    return percentile


def get_regime_characteristics(regime: str) -> Dict[str, Any]:
    """
    Regime별 특성 반환 (전략 방향, 포지션 bias 등)
    
    Args:
        regime: 'bull_high_vol' | 'bull_low_vol' | ... | 'range_low_vol'
    
    Returns:
        dict: {
            'strategy_direction': str (전략 방향),
            'long_bias': float (LONG 포지션 비율, 0-1),
            'short_bias': float (SHORT 포지션 비율, 0-1)
        }
    """
    regime_map = {
        'bull_high_vol': {
            'strategy_direction': '추세 추종 + 돌파',
            'long_bias': 0.70,
            'short_bias': 0.30
        },
        'bull_low_vol': {
            'strategy_direction': '조정 매수 + Mean Reversion',
            'long_bias': 0.60,
            'short_bias': 0.40
        },
        'bear_high_vol': {
            'strategy_direction': '추세 추종 + 돌파',
            'long_bias': 0.30,
            'short_bias': 0.70
        },
        'bear_low_vol': {
            'strategy_direction': '반등 매도 + Mean Reversion',
            'long_bias': 0.40,
            'short_bias': 0.60
        },
        'range_high_vol': {
            'strategy_direction': '경계 거래 + 빠른 익절',
            'long_bias': 0.50,
            'short_bias': 0.50
        },
        'range_low_vol': {
            'strategy_direction': 'Mean Reversion',
            'long_bias': 0.50,
            'short_bias': 0.50
        },
    }
    
    return regime_map.get(regime, regime_map['range_low_vol'])
