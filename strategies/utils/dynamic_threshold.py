#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dynamic Threshold Calculator for btc5m_baseline_v2
===================================================
Regime 및 시장 상태 기반 동적 threshold 계산 모듈

Features:
- RSI Dynamic Threshold: Rolling percentile 기반
- BB Dynamic Threshold: Volatility 조정 기반
- Momentum Dynamic Threshold: Regime별 적응
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


def get_rsi_threshold(df: pd.DataFrame, config: dict, regime: str) -> Tuple[float, float]:
    """
    Regime별 Dynamic RSI Threshold 계산
    
    Args:
        df: OHLCV + 지표가 포함된 DataFrame (RSI 필요)
        config: 전략 설정
            - rsi_long_percentile_base: LONG RSI percentile base (기본 25)
            - rsi_short_percentile_base: SHORT RSI percentile base (기본 75)
            - bull_rsi_adjustment: Bull Trend RSI 조정 비율 (기본 1.2)
            - bear_rsi_adjustment: Bear Trend RSI 조정 비율 (기본 0.85)
            - rsi_lookback: RSI percentile 계산 lookback (기본 100)
        regime: 'bull_high_vol' | 'bull_low_vol' | ... | 'range_low_vol'
    
    Returns:
        (rsi_long_threshold, rsi_short_threshold): RSI threshold 값
    """
    # Config 로드
    rsi_long_percentile_base = config.get('rsi_long_percentile_base', 25)
    rsi_short_percentile_base = config.get('rsi_short_percentile_base', 75)
    bull_rsi_adjustment = config.get('bull_rsi_adjustment', 1.2)
    bear_rsi_adjustment = config.get('bear_rsi_adjustment', 0.85)
    rsi_lookback = config.get('rsi_lookback', 100)
    
    # Regime별 Percentile 조정
    regime_adjustments = {
        'bull_high_vol': (bull_rsi_adjustment, 1.0),    # LONG threshold 상향
        'bull_low_vol': (bull_rsi_adjustment * 0.95, 1.0),
        'bear_high_vol': (1.0, bear_rsi_adjustment),     # SHORT threshold 하향
        'bear_low_vol': (1.0, bear_rsi_adjustment * 0.95),
        'range_high_vol': (1.0, 1.0),                    # 조정 없음
        'range_low_vol': (1.0, 1.0),
    }
    
    long_adj, short_adj = regime_adjustments.get(regime, (1.0, 1.0))
    
    # Adjusted Percentile 계산
    long_pct = rsi_long_percentile_base * long_adj
    short_pct = rsi_short_percentile_base * short_adj
    
    # Clipping (극단값 방지)
    long_pct = max(10, min(50, long_pct))
    short_pct = max(50, min(90, short_pct))
    
    # RSI 시리즈 추출
    if 'rsi' not in df.columns:
        logger.warning("RSI column not found. Using default thresholds (45/55).")
        return 45.0, 55.0
    
    rsi_series = df['rsi'].iloc[-rsi_lookback:] if len(df) >= rsi_lookback else df['rsi']
    
    # Rolling Percentile 계산
    rsi_long_threshold = rsi_series.quantile(long_pct / 100.0)
    rsi_short_threshold = rsi_series.quantile(short_pct / 100.0)
    
    # Final Clipping (절대값 범위 제한)
    rsi_long_threshold = max(25, min(50, rsi_long_threshold))
    rsi_short_threshold = max(50, min(75, rsi_short_threshold))
    
    logger.debug(f"RSI Threshold ({regime}): LONG {rsi_long_threshold:.1f}, SHORT {rsi_short_threshold:.1f}")
    
    return rsi_long_threshold, rsi_short_threshold


def get_bb_threshold(df: pd.DataFrame, config: dict, regime: str) -> Tuple[float, float]:
    """
    Regime + Volatility 기반 Dynamic BB Threshold 계산
    
    Args:
        df: OHLCV + 지표가 포함된 DataFrame (ATR 필요)
        config: 전략 설정
            - bb_mult_main_base: BB Main multiplier base (기본 0.8)
            - bb_mult_strong_base: BB Strong multiplier base (기본 1.5)
            - high_vol_bb_adjustment: High Vol BB 조정 비율 (기본 0.85)
            - low_vol_bb_adjustment: Low Vol BB 조정 비율 (기본 1.15)
        regime: 'bull_high_vol' | 'bull_low_vol' | ... | 'range_low_vol'
    
    Returns:
        (bb_mult_main, bb_mult_strong): BB std multiplier 값
    """
    # Config 로드
    bb_mult_main_base = config.get('bb_mult_main_base', 0.8)
    bb_mult_strong_base = config.get('bb_mult_strong_base', 1.5)
    high_vol_bb_adjustment = config.get('high_vol_bb_adjustment', 0.85)
    low_vol_bb_adjustment = config.get('low_vol_bb_adjustment', 1.15)
    
    # Regime별 Base Multiplier 및 Volatility 조정
    regime_base_map = {
        'bull_high_vol': (0.7, 1.3, high_vol_bb_adjustment),
        'bull_low_vol': (0.9, 1.5, low_vol_bb_adjustment),
        'bear_high_vol': (0.7, 1.3, high_vol_bb_adjustment),
        'bear_low_vol': (0.9, 1.5, low_vol_bb_adjustment),
        'range_high_vol': (0.8, 1.4, high_vol_bb_adjustment),
        'range_low_vol': (1.0, 1.7, low_vol_bb_adjustment),
    }
    
    base_main, base_strong, vol_adj = regime_base_map.get(regime, (1.0, 1.5, 1.0))
    
    # ParamSpace base 값 우선 사용 (tunable)
    base_main = bb_mult_main_base
    base_strong = bb_mult_strong_base
    
    # Volatility 조정 적용
    bb_mult_main = base_main * vol_adj
    bb_mult_strong = base_strong * vol_adj
    
    # ATR 기반 추가 조정 (Optional)
    atr_col = 'atr_14'
    if atr_col in df.columns:
        price = float(df['close'].iloc[-1])
        atr = float(df[atr_col].iloc[-1])
        atr_pct = atr / price
        
        # 변동성이 극단적으로 높으면 더 낮은 std 사용
        # 0.2% 기준으로 조정
        atr_adjustment = max(0.8, min(1.2, 0.002 / atr_pct))
        bb_mult_main *= atr_adjustment
        bb_mult_strong *= atr_adjustment
    
    # Final Clipping
    bb_mult_main = max(0.5, min(1.5, bb_mult_main))
    bb_mult_strong = max(1.0, min(2.5, bb_mult_strong))
    
    logger.debug(f"BB Multiplier ({regime}): MAIN {bb_mult_main:.2f}, STRONG {bb_mult_strong:.2f}")
    
    return bb_mult_main, bb_mult_strong


def get_momentum_threshold(df: pd.DataFrame, config: dict, regime: str) -> float:
    """
    Regime별 Dynamic Momentum Threshold 계산
    
    Args:
        df: OHLCV + 지표가 포함된 DataFrame
        config: 전략 설정
            - momentum_threshold_base: Momentum threshold base (기본 0.001)
        regime: 'bull_high_vol' | 'bull_low_vol' | ... | 'range_low_vol'
    
    Returns:
        momentum_threshold: 변화율 threshold (예: 0.001 = 0.1%)
    """
    # Config 로드
    momentum_threshold_base = config.get('momentum_threshold_base', 0.001)
    
    # Regime별 Threshold
    regime_momentum_map = {
        'bull_high_vol': 0.002,    # 0.2% (높은 변동성)
        'bull_low_vol': 0.001,     # 0.1%
        'bear_high_vol': 0.002,    # 0.2%
        'bear_low_vol': 0.001,     # 0.1%
        'range_high_vol': 0.0015,  # 0.15%
        'range_low_vol': 0.0008,   # 0.08% (낮은 변동성)
    }
    
    # ParamSpace base 값과 Regime 값 중 선택
    # (여기서는 Regime 값 우선, tunable base 값은 multiplier로 활용 가능)
    momentum_threshold = regime_momentum_map.get(regime, momentum_threshold_base)
    
    # Base 값과 조합 (Optional)
    # momentum_threshold = momentum_threshold_base * (regime_factor)
    
    logger.debug(f"Momentum Threshold ({regime}): {momentum_threshold:.4f}")
    
    return momentum_threshold


def calculate_bb_bands(df: pd.DataFrame, bb_mult: float, bb_period: int = 20) -> Dict[str, float]:
    """
    Bollinger Bands 계산 (동적 std multiplier 적용)
    
    Args:
        df: OHLCV DataFrame
        bb_mult: BB std multiplier
        bb_period: BB 계산 기간 (기본 20)
    
    Returns:
        dict: {'upper': float, 'middle': float, 'lower': float}
    """
    close = df['close']
    bb_middle = close.rolling(window=bb_period).mean().iloc[-1]
    bb_std = close.rolling(window=bb_period).std().iloc[-1]
    
    bb_upper = bb_middle + (bb_std * bb_mult)
    bb_lower = bb_middle - (bb_std * bb_mult)
    
    return {
        'upper': float(bb_upper),
        'middle': float(bb_middle),
        'lower': float(bb_lower)
    }
