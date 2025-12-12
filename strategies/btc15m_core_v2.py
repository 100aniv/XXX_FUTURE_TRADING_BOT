#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTCUSDT 15m Core Strategy V2 (PHASE30-3)
=========================================
STATUS: IMPLEMENTATION

Core V2 Strategy: Comprehensive Redesign
- Multi-Timeframe Regime Detection (1H/4H + 15m)
- 2-Tier Core AND (Absolute + Penalty)
- 14 Optional OR Scenarios (Trend-Up 5, Trend-Down 5, Range 4)
- Dynamic RR 2.0~2.5, TP1 70%/TP2 30%
- Guard Integration with Gradual Position Sizing

Design Document: docs/PHASE30/PHASE30_2_BTC15M_CORE_V2_STRATEGY_DESIGN_KR.md

Key Improvements over V1:
1. Higher TF Regime: 0.6 × (1H/4H) + 0.4 × (15m) → confidence 0.35-0.4
2. 2-Tier Filters: Absolute (block) vs Penalty (size 0.5-1.0x) → +30-40% trades
3. OR Scenarios: 8 → 14 (Breakout, Divergence, S/R, Fakeout) → +40-60% trades
4. RR 2.0: Win Rate 38% → EV +0.14 (V1: RR 1.5, WR 31.25% → EV -0.22)
5. Guard Sizing: 3-4 loss(80%), 5-6(60%), 7-8(40%) instead of block

Expected Performance (3M):
- Trades: 80-100 (V1: 48, +67-108%)
- Win Rate: 38-42% (V1: 31.25%, +6.75-10.75%p)
- Profit Factor: 1.15-1.25 (V1: 0.77, +49-62%)
"""
from typing import Dict, Any, Tuple, Optional, List
import pandas as pd
import numpy as np
import logging
from datetime import datetime

from common.calculations import leverage_suggestion
from common.registry.base_strategy import BaseStrategy
from common.registry.strategy_metadata import StrategyMetadata

logger = logging.getLogger(__name__)


# =====================================================
# Multi-Timeframe Regime Detection V2
# =====================================================

def detect_regime_mtf(
    df_15m: pd.DataFrame,
    df_1h: Optional[pd.DataFrame] = None,
    df_4h: Optional[pd.DataFrame] = None,
    config: dict = None
) -> Dict[str, Any]:
    """
    Multi-Timeframe Regime Detection V2
    
    V2 Design:
    - Combines Higher TF (1H/4H) + Local TF (15m)
    - Formula: confidence = 0.6 × HTF + 0.4 × LTF
    - Regimes: TREND_UP, TREND_DOWN, RANGE, CHOP
    - Min confidence: 0.35 (Trend), 0.40 (Range)
    
    Args:
        df_15m: 15m OHLCV + indicators
        df_1h: 1H OHLCV + indicators (optional, for MTF)
        df_4h: 4H OHLCV + indicators (optional, for MTF)
        config: Strategy config
    
    Returns:
        dict: {
            'regime': str,
            'confidence': float,
            'htf_regime': str,
            'ltf_regime': str,
            'htf_confidence': float,
            'ltf_confidence': float,
            'hysteresis_met': bool
        }
    """
    if config is None:
        config = {}
    
    regime_cfg = config.get('regime_detection', {})
    v2_light = config.get('v2_light', False)  # PHASE32-0: V2 Light 모드
    
    # Detect Local TF (15m)
    ltf_regime_info = _detect_single_tf_regime(df_15m, config, timeframe='15m')
    ltf_regime = ltf_regime_info['regime']
    ltf_confidence = ltf_regime_info['confidence']
    
    # Detect Higher TF (prefer 1H, fallback to 4H, fallback to 15m)
    if df_1h is not None and len(df_1h) >= 30:
        htf_regime_info = _detect_single_tf_regime(df_1h, config, timeframe='1h')
    elif df_4h is not None and len(df_4h) >= 30:
        htf_regime_info = _detect_single_tf_regime(df_4h, config, timeframe='4h')
    else:
        # No HTF available, use 15m only (fallback to V1 behavior)
        logger.warning("[V2 Regime] No Higher TF data, using 15m only (V1 fallback)")
        htf_regime_info = ltf_regime_info
    
    htf_regime = htf_regime_info['regime']
    htf_confidence = htf_regime_info['confidence']
    
    # Combine HTF + LTF
    htf_weight = regime_cfg.get('higher_tf_weight', 0.6)
    ltf_weight = regime_cfg.get('local_tf_weight', 0.4)
    
    # If HTF and LTF disagree on Regime, take HTF as priority
    if htf_regime != ltf_regime:
        # HTF dominates
        combined_regime = htf_regime
        combined_confidence = htf_confidence * htf_weight + ltf_confidence * ltf_weight * 0.5
    else:
        # HTF and LTF agree
        combined_regime = htf_regime
        combined_confidence = htf_confidence * htf_weight + ltf_confidence * ltf_weight
    
    # CHOP market detection (override)
    if ltf_regime == 'CHOP' or htf_regime == 'CHOP':
        combined_regime = 'CHOP'
        combined_confidence = 0.0
    
    # Hysteresis check (require 5 candles consistency on 15m)
    hysteresis_candles = regime_cfg.get('hysteresis_candles', 5)
    if v2_light and hysteresis_candles >= 5:  # PHASE32-0: Light 모드 완화
        hysteresis_candles = 3
    
    hysteresis_met = check_hysteresis_v2(
        df_15m,
        combined_regime,
        required_candles=hysteresis_candles,
        v2_light=v2_light
    )
    
    return {
        'regime': combined_regime,
        'confidence': combined_confidence,
        'htf_regime': htf_regime,
        'ltf_regime': ltf_regime,
        'htf_confidence': htf_confidence,
        'ltf_confidence': ltf_confidence,
        'hysteresis_met': hysteresis_met,
        'adx': ltf_regime_info.get('adx', 20),
        'atr_ratio': ltf_regime_info.get('atr_ratio', 1.0),
        'volume_ratio': ltf_regime_info.get('volume_ratio', 1.0)
    }


def _detect_single_tf_regime(df: pd.DataFrame, config: dict, timeframe: str = '15m') -> Dict[str, Any]:
    """
    Single Timeframe Regime Detection (same logic as V1, reusable)
    
    Uses: ADX + ATR + Volume + DI
    Regimes: TREND_UP, TREND_DOWN, RANGE, CHOP
    """
    if df is None or df.empty or len(df) < 30:
        return {
            'regime': 'CHOP',
            'confidence': 0.0,
            'reason': 'insufficient_data'
        }
    
    # PHASE32-1 FIX: DataFrame 타임스탬프 타입 확인
    if 'time' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['time']):
        df['time'] = pd.to_datetime(df['time'])
    
    # Get last row
    last = df.iloc[-1]
    recent = df.iloc[-20:]
    
    # Extract indicators
    adx = float(last.get('adx_14', 20))
    di_plus = float(last.get('di_plus_14', 0))
    di_minus = float(last.get('di_minus_14', 0))
    atr = float(last.get('atr_14', last['close'] * 0.002))
    volume = float(last.get('volume', 0))
    
    # Ratios
    avg_atr = float(recent['atr_14'].mean()) if 'atr_14' in recent.columns else atr
    avg_volume = float(recent['volume'].mean()) if 'volume' in recent.columns else volume
    atr_ratio = atr / avg_atr if avg_atr > 0 else 1.0
    volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
    di_diff = di_plus - di_minus
    
    # Price range
    price_high = float(recent['high'].max())
    price_low = float(recent['low'].min())
    price_range_pct = (price_high - price_low) / price_low if price_low > 0 else 0.0
    
    # Config thresholds
    regime_cfg = config.get('regime_detection', {})
    adx_trend_threshold = regime_cfg.get('adx_trend_threshold', 25)
    adx_range_threshold = regime_cfg.get('adx_range_threshold', 20)
    atr_high_vol_mult = regime_cfg.get('atr_high_vol_mult', 1.5)
    volume_high_vol_mult = regime_cfg.get('volume_high_vol_mult', 2.0)
    
    # Regime detection
    regime = 'UNKNOWN'
    confidence = 0.0
    
    # 1. CHOP (High Vol + Low ADX)
    if adx < adx_range_threshold and atr_ratio > atr_high_vol_mult and volume_ratio > volume_high_vol_mult:
        regime = 'CHOP'
        confidence = min(1.0, (atr_ratio - 1.0) * 0.5 + (volume_ratio - 1.0) * 0.3)
    
    # 2. TREND_UP
    elif adx > adx_trend_threshold and di_plus > di_minus and atr_ratio > 1.1 and volume_ratio > 0.9:
        regime = 'TREND_UP'
        adx_score = min(1.0, (adx - 20) / 20) * 0.4
        di_score = min(1.0, di_diff / max(di_plus, 1.0)) * 0.3
        atr_score = min(1.0, (atr_ratio - 1.0)) * 0.2
        vol_score = min(1.0, (volume_ratio - 0.9) / 0.5) * 0.1
        confidence = max(0.0, min(1.0, adx_score + di_score + atr_score + vol_score))
    
    # 3. TREND_DOWN
    elif adx > adx_trend_threshold and di_minus > di_plus and atr_ratio > 1.1 and volume_ratio > 0.9:
        regime = 'TREND_DOWN'
        adx_score = min(1.0, (adx - 20) / 20) * 0.4
        di_score = min(1.0, abs(di_diff) / max(di_minus, 1.0)) * 0.3
        atr_score = min(1.0, (atr_ratio - 1.0)) * 0.2
        vol_score = min(1.0, (volume_ratio - 0.9) / 0.5) * 0.1
        confidence = max(0.0, min(1.0, adx_score + di_score + atr_score + vol_score))
    
    # 4. RANGE
    elif adx < adx_range_threshold and atr_ratio < 1.0 and price_range_pct < 0.02:
        regime = 'RANGE'
        adx_score = (adx_range_threshold - adx) / adx_range_threshold * 0.5
        atr_score = (1.0 - atr_ratio) * 0.3
        range_score = (0.02 - price_range_pct) / 0.02 * 0.2
        confidence = max(0.0, min(1.0, adx_score + atr_score + range_score))
    
    else:
        regime = 'RANGE'  # Default fallback
        confidence = 0.15
    
    return {
        'regime': regime,
        'confidence': confidence,
        'adx': adx,
        'atr_ratio': atr_ratio,
        'volume_ratio': volume_ratio,
        'di_diff': di_diff
    }


def check_hysteresis_v2(
    df: pd.DataFrame,
    current_regime: str,
    required_candles: int = 5,
    regime_col: str = 'regime',
    v2_light: bool = False
) -> bool:
    """
    Hysteresis V2: 최근 N개 캔들이 모두 동일 Regime이어야 안정적으로 간주
    
    Args:
        df: OHLCV + regime 데이터
        current_regime: 현재 regime
        required_candles: 필요한 연속 개수 (V2: 5, Light: 3)
        regime_col: regime 컬럼명
        v2_light: V2 Light 모드 (완화된 기준)
    
    Returns:
        bool: hysteresis 충족 여부
    """
    # PHASE32-0: V2 Light 모드일 때 required_candles 자동 조정
    if v2_light and required_candles >= 5:
        required_candles = 3
    
    if len(df) < required_candles:
        return True  # Not enough data, allow regime
    
    recent_candles = df.iloc[-required_candles:]
    
    if current_regime == 'TREND_UP':
        # Require 4/5 candles to show TREND_UP conditions
        trend_up_count = sum([
            (row.get('adx_14', 0) > 25 and row.get('di_plus_14', 0) > row.get('di_minus_14', 0))
            for _, row in recent_candles.iterrows()
        ])
        return trend_up_count >= required_candles - 1
    
    elif current_regime == 'TREND_DOWN':
        trend_down_count = sum([
            (row.get('adx_14', 0) > 25 and row.get('di_minus_14', 0) > row.get('di_plus_14', 0))
            for _, row in recent_candles.iterrows()
        ])
        return trend_down_count >= required_candles - 1
    
    elif current_regime == 'RANGE':
        # Require all 5 candles to have ADX < 20
        range_count = sum([
            row.get('adx_14', 30) < 20
            for _, row in recent_candles.iterrows()
        ])
        return range_count >= required_candles
    
    elif current_regime == 'CHOP':
        # CHOP always blocks, no hysteresis needed
        return True
    
    # Unknown regime, allow
    return True


# =====================================================
# 2-Tier Core AND V2
# =====================================================

def check_absolute_conditions(
    regime_info: Dict[str, Any],
    df: pd.DataFrame,
    config: dict,
    portfolio_state: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """
    Tier 1: Absolute Conditions (ANY failure → block entry)
    
    V2 Design:
    - Regime confidence >= 0.35
    - CHOP regime → block
    - Hysteresis met
    - Guard allowed (externally checked)
    - DD < 80% of max_dd
    - Consecutive losses < 8
    
    Returns:
        (bool, str): (pass, reason)
    """
    regime_cfg = config.get('regime_detection', {})
    filters_cfg = config.get('filters', {})
    
    # 1. Regime Confidence (minimum threshold)
    regime = regime_info['regime']
    # Min confidence threshold (regime-dependent)
    # PHASE32-0: V2 Light 모드일 때 완화
    v2_light = config.get('v2_light', False)
    
    if regime in ['TREND_UP', 'TREND_DOWN']:
        min_confidence = regime_cfg.get('min_confidence_trend', 0.35)
        if v2_light:
            min_confidence = min(min_confidence, 0.25)  # Light: 0.25로 완화
    else:  # RANGE
        min_confidence = regime_cfg.get('min_confidence_range', 0.40)
        if v2_light:
            min_confidence = min(min_confidence, 0.30)  # Light: 0.30으로 완화
    
    if regime_info['confidence'] < min_confidence:
        return False, f"low_confidence_{regime_info['confidence']:.2f}"
    
    # 2. CHOP market block
    if regime == 'CHOP':
        return False, "chop_market_blocked"
    
    # 3. Hysteresis
    if not regime_info.get('hysteresis_met', False):
        return False, "hysteresis_not_met"
    
    # 4. Portfolio state checks (if available)
    if portfolio_state:
        max_dd = filters_cfg.get('max_dd_threshold', 0.12)
        current_dd = portfolio_state.get('current_dd', 0.0)
        if current_dd > max_dd * 0.8:  # 80% of max
            return False, f"dd_near_limit_{current_dd:.2%}"
        
        consecutive_losses = portfolio_state.get('consecutive_losses', 0)
        if consecutive_losses >= 8:
            return False, f"consecutive_loss_{consecutive_losses}"
    
    return True, "absolute_pass"


def calculate_position_penalty(
    df: pd.DataFrame,
    regime_info: Dict[str, Any],
    config: dict
) -> float:
    """
    Tier 2: Penalty Conditions (reduce position size, NOT block)
    
    V2 Design:
    - ATR < min → 0.7x, ATR < 1.2×min → 0.9x
    - Volume < min → 0.7x, Volume < 1.2×min → 0.9x
    - Confidence < 0.40 → 0.8x, < 0.45 → 0.9x
    - Min multiplier: 0.5 (never go below 50%)
    
    Returns:
        float: position_size_multiplier (0.5~1.0)
    """
    if len(df) < 20:
        return 0.5  # Insufficient data, heavy penalty
    
    last = df.iloc[-1]
    recent = df.iloc[-20:]
    filters_cfg = config.get('filters', {})
    
    multiplier = 1.0
    
    # 1. ATR Penalty
    atr = float(last.get('atr_14', 0))
    price = float(last['close'])
    atr_pct = atr / price if price > 0 else 0.0
    min_atr_pct = filters_cfg.get('min_atr_pct', 0.0015)
    
    if atr_pct < min_atr_pct:
        multiplier *= 0.7
    elif atr_pct < min_atr_pct * 1.2:
        multiplier *= 0.9
    
    # 2. Volume Penalty
    volume = float(last.get('volume', 0))
    avg_volume = float(recent['volume'].mean()) if len(recent) > 0 else volume
    volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
    min_volume_ratio = filters_cfg.get('min_volume_ratio', 0.5)
    
    if volume_ratio < min_volume_ratio:
        multiplier *= 0.7
    elif volume_ratio < min_volume_ratio * 1.2:
        multiplier *= 0.9
    
    # 3. Confidence Penalty
    confidence = regime_info['confidence']
    if confidence < 0.40:
        multiplier *= 0.8
    elif confidence < 0.45:
        multiplier *= 0.9
    
    # 4. Enforce minimum (50%)
    multiplier = max(multiplier, 0.5)
    
    return multiplier


# =====================================================
# Optional OR Scenarios V2 (14 Scenarios)
# =====================================================

def evaluate_trend_up_scenarios(df: pd.DataFrame, config: dict) -> Tuple[bool, Optional[str]]:
    """
    Trend-Up Mode: 5 LONG Scenarios
    
    V2 Scenarios:
    1. EMA Pullback (V1)
    2. RSI Oversold + Bounce (V1)
    3. BB Lower + Volume Spike (V1)
    4. Breakout + Confirmation (NEW)
    5. Bullish Divergence (NEW)
    """
    if len(df) < 30:
        return False, None
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    recent_20 = df.iloc[-20:]
    recent_5 = df.iloc[-5:]
    
    price = float(last['close'])
    open_price = float(last['open'])
    low = float(last['low'])
    high = float(last['high'])
    volume = float(last.get('volume', 0))
    
    ema_20 = float(last.get('ema_20', price))
    ema_50 = float(last.get('ema_50', price))
    rsi = float(last.get('rsi_14', 50))
    prev_rsi = float(prev.get('rsi_14', 50))
    bb_lower = float(last.get('bb_lower', price * 0.98))
    adx = float(last.get('adx_14', 20))
    
    avg_volume = float(recent_20['volume'].mean()) if len(recent_20) > 0 else volume
    recent_high = float(recent_20['high'].max())
    
    # Scenario 1: EMA Pullback
    if price > ema_50 and low <= ema_50 * 1.002 and price > open_price:
        return True, "ema_pullback_long"
    
    # Scenario 2: RSI Oversold + Bounce
    if rsi < 35 and rsi > prev_rsi and price > open_price:
        return True, "rsi_oversold_long"
    
    # Scenario 3: BB Lower + Volume Spike
    if low <= bb_lower * 1.001 and volume > avg_volume * 1.3 and price > (high + low) / 2:
        return True, "bb_lower_volume_long"
    
    # Scenario 4: Breakout + Confirmation (NEW)
    if price > recent_high * 0.9999 and volume > avg_volume * 1.5 and adx > 25:
        return True, "breakout_long"
    
    # Scenario 5: Bullish Divergence (NEW)
    prev_5_low = float(recent_5['low'].min())
    prev_5_rsi_low = float(recent_5['rsi_14'].min()) if 'rsi_14' in recent_5.columns else 50
    if price < prev_5_low and rsi > prev_5_rsi_low and volume > avg_volume * 1.2:
        return True, "divergence_bullish_long"
    
    return False, None


def evaluate_trend_down_scenarios(df: pd.DataFrame, config: dict) -> Tuple[bool, Optional[str]]:
    """
    Trend-Down Mode: 5 SHORT Scenarios
    
    V2 Scenarios (mirror of Trend-Up):
    1. EMA Pullback (V1)
    2. RSI Overbought + Drop (V1)
    3. BB Upper + Volume Spike (V1)
    4. Breakdown + Confirmation (NEW)
    5. Bearish Divergence (NEW)
    """
    if len(df) < 30:
        return False, None
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    recent_20 = df.iloc[-20:]
    recent_5 = df.iloc[-5:]
    
    price = float(last['close'])
    open_price = float(last['open'])
    low = float(last['low'])
    high = float(last['high'])
    volume = float(last.get('volume', 0))
    
    ema_20 = float(last.get('ema_20', price))
    ema_50 = float(last.get('ema_50', price))
    rsi = float(last.get('rsi_14', 50))
    prev_rsi = float(prev.get('rsi_14', 50))
    bb_upper = float(last.get('bb_upper', price * 1.02))
    adx = float(last.get('adx_14', 20))
    
    avg_volume = float(recent_20['volume'].mean()) if len(recent_20) > 0 else volume
    recent_low = float(recent_20['low'].min())
    
    # Scenario 1: EMA Pullback
    if price < ema_50 and high >= ema_50 * 0.998 and price < open_price:
        return True, "ema_pullback_short"
    
    # Scenario 2: RSI Overbought + Drop
    if rsi > 65 and rsi < prev_rsi and price < open_price:
        return True, "rsi_overbought_short"
    
    # Scenario 3: BB Upper + Volume Spike
    if high >= bb_upper * 0.999 and volume > avg_volume * 1.3 and price < (high + low) / 2:
        return True, "bb_upper_volume_short"
    
    # Scenario 4: Breakdown + Confirmation (NEW)
    if price < recent_low * 1.0001 and volume > avg_volume * 1.5 and adx > 25:
        return True, "breakdown_short"
    
    # Scenario 5: Bearish Divergence (NEW)
    prev_5_high = float(recent_5['high'].max())
    prev_5_rsi_high = float(recent_5['rsi_14'].max()) if 'rsi_14' in recent_5.columns else 50
    if price > prev_5_high and rsi < prev_5_rsi_high and volume > avg_volume * 1.2:
        return True, "divergence_bearish_short"
    
    return False, None


def evaluate_range_scenarios(df: pd.DataFrame, config: dict) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Range Mode: 4 Scenarios (2 LONG, 2 SHORT)
    
    V2 Scenarios:
    LONG:
    1. BB Lower Bounce (V1)
    2. Support Bounce (NEW)
    
    SHORT:
    3. BB Upper Fade (V1)
    4. Resistance Fade (NEW)
    """
    if len(df) < 30:
        return False, None, None
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    recent_20 = df.iloc[-20:]
    
    price = float(last['close'])
    open_price = float(last['open'])
    low = float(last['low'])
    high = float(last['high'])
    volume = float(last.get('volume', 0))
    
    rsi = float(last.get('rsi_14', 50))
    bb_lower = float(last.get('bb_lower', price * 0.98))
    bb_upper = float(last.get('bb_upper', price * 1.02))
    bb_middle = float(last.get('bb_middle', price))
    
    avg_volume = float(recent_20['volume'].mean()) if len(recent_20) > 0 else volume
    
    # Estimate Support/Resistance (simple: 20-candle min/max)
    support_level = float(recent_20['low'].min())
    resistance_level = float(recent_20['high'].max())
    
    # LONG Scenario 1: BB Lower Bounce
    if low <= bb_lower * 1.002 and rsi < 40 and price > open_price:
        return True, "bb_lower_bounce_long", "LONG"
    
    # LONG Scenario 2: Support Bounce (NEW)
    if price <= support_level * 1.005 and volume > avg_volume * 1.2 and price > open_price:
        return True, "support_bounce_long", "LONG"
    
    # SHORT Scenario 3: BB Upper Fade
    if high >= bb_upper * 0.998 and rsi > 60 and price < open_price:
        return True, "bb_upper_fade_short", "SHORT"
    
    # SHORT Scenario 4: Resistance Fade (NEW)
    if price >= resistance_level * 0.995 and volume > avg_volume * 1.2 and price < open_price:
        return True, "resistance_fade_short", "SHORT"
    
    return False, None, None


# =====================================================
# SL/TP V2 (Dynamic RR 2.0~2.5, TP1 70%/TP2 30%)
# =====================================================

def calculate_sl_tp_v2(
    regime: str,
    side: str,
    entry_price: float,
    atr: float,
    config: dict
) -> Dict[str, Any]:
    """
    SL/TP V2: Dynamic RR based on Regime
    
    V2 Design:
    - Trend: SL=1.8 ATR, TP1 RR=2.0, TP2 RR=3.5, TP1 70%, TP2 30%
    - Range: SL=1.5 ATR, TP1 RR=2.0, TP2 RR=3.0, TP1 70%, TP2 30%
    
    Returns:
        dict: {
            'sl': float,
            'tp1': float,
            'tp2': float,
            'sl_distance': float,
            'tp1_rr': float,
            'tp2_rr': float,
            'tp1_qty_pct': float,
            'tp2_qty_pct': float
        }
    """
    sl_tp_cfg = config.get('sl_tp', {})
    
    if regime in ['TREND_UP', 'TREND_DOWN']:
        sl_mult = sl_tp_cfg.get('sl_mult_trend', 1.8)
        tp1_rr = sl_tp_cfg.get('tp1_rr_trend', 2.0)
        tp2_rr = sl_tp_cfg.get('tp2_rr_trend', 3.5)
    else:  # RANGE
        sl_mult = sl_tp_cfg.get('sl_mult_range', 1.5)
        tp1_rr = sl_tp_cfg.get('tp1_rr_range', 2.0)
        tp2_rr = sl_tp_cfg.get('tp2_rr_range', 3.0)
    
    # TP Quantities (70%/30% split)
    tp1_qty_pct = sl_tp_cfg.get('tp1_qty_pct', 0.7)
    tp2_qty_pct = sl_tp_cfg.get('tp2_qty_pct', 0.3)
    
    sl_distance = atr * sl_mult
    
    if side == 'LONG':
        sl_price = entry_price - sl_distance
        tp1_price = entry_price + sl_distance * tp1_rr
        tp2_price = entry_price + sl_distance * tp2_rr
    else:  # SHORT
        sl_price = entry_price + sl_distance
        tp1_price = entry_price - sl_distance * tp1_rr
        tp2_price = entry_price - sl_distance * tp2_rr
    
    return {
        'sl': sl_price,
        'tp1': tp1_price,
        'tp2': tp2_price,
        'sl_distance': sl_distance,
        'tp1_rr': tp1_rr,
        'tp2_rr': tp2_rr,
        'tp1_qty_pct': tp1_qty_pct,
        'tp2_qty_pct': tp2_qty_pct
    }


# =====================================================
# Guard Integration: Gradual Position Sizing
# =====================================================

def calculate_guard_position_multiplier(
    consecutive_losses: int,
    current_dd: float,
    config: dict
) -> float:
    """
    Guard-Based Position Size Multiplier (Gradual Reduction)
    
    V2 Design:
    - Consecutive Losses: 0-2(1.0), 3-4(0.8), 5-6(0.6), 7-8(0.4), 9+(0.0 block)
    - DD: <6%(1.0), 6-8.4%(0.8), 8.4-10.2%(0.6), >10.2%(0.0 block)
    
    Returns:
        float: multiplier (0.0~1.0)
    """
    guard_cfg = config.get('guard', {})
    max_dd = guard_cfg.get('max_drawdown', 0.12)
    
    # 1. Consecutive Loss Multiplier
    if consecutive_losses <= 2:
        loss_mult = 1.0
    elif consecutive_losses <= 4:
        loss_mult = 0.8
    elif consecutive_losses <= 6:
        loss_mult = 0.6
    elif consecutive_losses <= 8:
        loss_mult = 0.4
    else:
        loss_mult = 0.0  # Block
    
    # 2. DD Multiplier
    dd_ratio = current_dd / max_dd if max_dd > 0 else 0.0
    if dd_ratio < 0.5:  # DD < 6%
        dd_mult = 1.0
    elif dd_ratio < 0.7:  # DD 6-8.4%
        dd_mult = 0.8
    elif dd_ratio < 0.85:  # DD 8.4-10.2%
        dd_mult = 0.6
    else:  # DD > 10.2%
        dd_mult = 0.0  # Block
    
    # Combined (take minimum of both)
    final_mult = min(loss_mult, dd_mult)
    
    return final_mult


# =====================================================
# Main Signal Logic (Core V2)
# =====================================================

def signal_logic(
    df: pd.DataFrame,
    config: dict,
    df_1h: Optional[pd.DataFrame] = None,
    df_4h: Optional[pd.DataFrame] = None,
    portfolio_state: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    BTC 15m Core V2 Strategy Logic
    
    PHASE30-3 Implementation:
    - Multi-TF Regime Detection (1H/4H + 15m)
    - 2-Tier Core AND (Absolute + Penalty)
    - 14 Optional OR Scenarios
    - Dynamic RR 2.0~2.5, TP1 70%/TP2 30%
    - Guard Integration with Gradual Sizing
    
    Args:
        df: 15m OHLCV + indicators
        config: Strategy config
        df_1h: 1H OHLCV + indicators (optional)
        df_4h: 4H OHLCV + indicators (optional)
        portfolio_state: Portfolio state (for Guard checks)
    
    Returns:
        dict: Signal info with Multi-TP structure
    """
    # === Auto-calculate indicators if missing ===
    required_indicators = [
        'rsi_14', 'adx_14', 'di_plus_14', 'di_minus_14',
        'ema_20', 'ema_50', 'ema_200', 'atr_14', 'volume_ma_20',
        'bb_upper', 'bb_middle', 'bb_lower'
    ]
    missing = [col for col in required_indicators if col not in df.columns]
    
    if missing:
        logger.info(f"[btc15m_core_v2] Missing indicators: {missing} → auto-calculating")
        from common.backtest_indicators import add_core_v1_indicators
        df = add_core_v1_indicators(df, config)
        logger.info(f"[btc15m_core_v2] Indicators added")
    
    # === Config validation ===
    lv = config.get("leverage", {})
    if not all(k in lv for k in ("min", "max", "default")):
        return {"side": None, "reason": "leverage_config_incomplete"}
    
    # === Data sufficiency ===
    min_bars = config.get('min_bars_for_signal', 100)
    if len(df) < min_bars:
        return {"side": None, "reason": f"insufficient_data_need_{min_bars}_bars"}
    
    # === Current candle info ===
    last = df.iloc[-1]
    price = float(last["close"])
    atr = float(last.get("atr_14", price * 0.002))
    
    # === STEP 1: Multi-TF Regime Detection V2 ===
    regime_info = detect_regime_mtf(df, df_1h, df_4h, config)
    regime = regime_info['regime']
    confidence = regime_info['confidence']
    
    logger.debug(
        f"[V2] Regime: {regime} (conf {confidence:.2f}), "
        f"HTF: {regime_info['htf_regime']} (conf {regime_info['htf_confidence']:.2f}), "
        f"LTF: {regime_info['ltf_regime']} (conf {regime_info['ltf_confidence']:.2f})"
    )
    
    # === STEP 2: Tier 1 - Absolute Conditions ===
    absolute_pass, absolute_reason = check_absolute_conditions(regime_info, df, config, portfolio_state)
    if not absolute_pass:
        return {"side": None, "reason": absolute_reason}
    
    # === STEP 3: Tier 2 - Position Penalty ===
    penalty_mult = calculate_position_penalty(df, regime_info, config)
    
    # === STEP 4: Guard-Based Position Multiplier ===
    guard_mult = 1.0
    if portfolio_state:
        consecutive_losses = portfolio_state.get('consecutive_losses', 0)
        current_dd = portfolio_state.get('current_dd', 0.0)
        guard_mult = calculate_guard_position_multiplier(consecutive_losses, current_dd, config)
    
    # === STEP 5: Final Position Size Multiplier ===
    final_size_mult = penalty_mult * guard_mult
    
    # If final multiplier < 20%, block entry
    if final_size_mult < 0.2:
        return {"side": None, "reason": f"size_too_small_{final_size_mult:.2f}"}
    
    # === STEP 6: Optional OR Scenarios ===
    side = None
    scenario = None
    
    if regime == 'TREND_UP':
        has_signal, scenario = evaluate_trend_up_scenarios(df, config)
        if has_signal:
            side = 'LONG'
    
    elif regime == 'TREND_DOWN':
        has_signal, scenario = evaluate_trend_down_scenarios(df, config)
        if has_signal:
            side = 'SHORT'
    
    elif regime == 'RANGE':
        has_signal, scenario, range_side = evaluate_range_scenarios(df, config)
        if has_signal:
            side = range_side
    
    if side is None:
        return {"side": None, "reason": f"no_scenario_triggered_{regime}"}
    
    # === STEP 7: Calculate SL/TP V2 ===
    sl_tp_info = calculate_sl_tp_v2(regime, side, price, atr, config)
    
    # === Return Signal ===
    return {
        "side": side,
        "reason": f"{regime}_{scenario}",
        "entry": price,
        "sl": sl_tp_info['sl'],
        "tp1": sl_tp_info['tp1'],
        "tp2": sl_tp_info['tp2'],
        "tp1_qty_pct": sl_tp_info['tp1_qty_pct'],
        "tp2_qty_pct": sl_tp_info['tp2_qty_pct'],
        "rr_tp1": sl_tp_info['tp1_rr'],
        "rr_tp2": sl_tp_info['tp2_rr'],
        "regime": regime,
        "regime_confidence": confidence,
        "scenario": scenario,
        "position_size_mult": final_size_mult,
        "penalty_mult": penalty_mult,
        "guard_mult": guard_mult,
        "metadata": {
            "strategy": "btc15m_core_v2",
            "regime": regime,
            "scenario": scenario,
            "htf_regime": regime_info.get('htf_regime'),
            "ltf_regime": regime_info.get('ltf_regime'),
            "confidence": confidence,
            "rr_tp1": sl_tp_info['tp1_rr'],
            "rr_tp2": sl_tp_info['tp2_rr'],
            "final_size_mult": final_size_mult
        }
    }


# =====================================================
# BaseStrategy Wrapper (for Engine Integration)
# =====================================================

class BTC15mCoreV2Strategy(BaseStrategy):
    """
    BTC 15m Core V2 Strategy (PHASE30-3)
    
    Wrapper for BaseStrategy interface compatibility with engine.
    """
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        # PHASE32-0: DecisionTrace 계측 시스템
        self._diag_enabled = config.get('diag_enabled', False) if config else False
        self._diag_counters = {}
        self._total_signals_checked = 0
        logger.info(f"[V2] DecisionTrace: {'ENABLED' if self._diag_enabled else 'DISABLED'}")
    
    def _diag_inc(self, reason: str):
        """차단 사유 카운터 증가"""
        if self._diag_enabled:
            self._diag_counters[reason] = self._diag_counters.get(reason, 0) + 1
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_name="btc15m_core_v2",
            strategy_type="core",
            supported_symbols=["BTCUSDT"],
            supported_timeframes=["15m"],
            version="2.0.0",
            description="BTC 15m Core V2: MTF Regime, 2-Tier AND, 14 OR Scenarios, Dynamic RR 2.0-2.5"
        )
    
    def compute_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Compute signal using signal_logic function.
        
        Args:
            df: 15m OHLCV + indicators
        
        Returns:
            dict: Signal info
        """
        # PHASE32-0: DecisionTrace 카운팅
        if self._diag_enabled:
            self._total_signals_checked += 1
        
        # Engine will provide df_1h/df_4h via config or separate mechanism
        # For now, pass None (fallback to 15m-only regime)
        df_1h = self.config.get('df_1h', None)
        df_4h = self.config.get('df_4h', None)
        portfolio_state = self.config.get('portfolio_state', None)
        
        # PHASE32-1: Exception handling with full traceback
        try:
            result = signal_logic(df, self.config, df_1h, df_4h, portfolio_state)
            
            # PHASE32-0: 차단 사유 추적
            if self._diag_enabled and result.get('side') is None:
                reason = result.get('reason', 'unknown')
                self._diag_inc(reason)
            
            return result
        except Exception as e:
            # PHASE32-1: 예외 상세 로깅 (스택 트레이스 + 메타데이터)
            logger.exception(
                f"❌ [btc15m_core_v2] 신호 계산 예외: {str(e)}\n"
                f"   - now_ts: {df.index[-1] if not df.empty else 'N/A'}\n"
                f"   - df.index.tz: {df.index.tz if hasattr(df.index, 'tz') else 'N/A'}\n"
                f"   - df_1h: {df_1h.index.tz if df_1h is not None and hasattr(df_1h.index, 'tz') else 'N/A'}\n"
                f"   - df_4h: {df_4h.index.tz if df_4h is not None and hasattr(df_4h.index, 'tz') else 'N/A'}"
            )
            
            # 예외를 차단 사유로 기록
            if self._diag_enabled:
                self._diag_inc(f"EXCEPTION_{type(e).__name__}")
            
            # 예외 발생 시 None 신호 반환 (엔진이 계속 진행 가능하도록)
            return {"side": None, "reason": f"exception_{type(e).__name__}"}
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """DecisionTrace 진단 결과 반환"""
        if not self._diag_enabled:
            return {}
        
        # 상위 차단 사유 정렬
        sorted_reasons = sorted(
            self._diag_counters.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        total_blocks = sum(self._diag_counters.values())
        
        return {
            'total_signals_checked': self._total_signals_checked,
            'total_blocks': total_blocks,
            'block_rate': total_blocks / self._total_signals_checked if self._total_signals_checked > 0 else 0.0,
            'top_blockers': sorted_reasons[:10],
            'all_counters': self._diag_counters
        }
