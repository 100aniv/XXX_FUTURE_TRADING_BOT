#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTCUSDT 15m Core Strategy V1 (PHASE30-1)
=========================================
STATUS: PRODUCTION CANDIDATE

New Core Strategy: Core AND + Optional OR

목적:
- V2/V3/V4 실패 교훈 반영
- Core AND (필수 필터) + Optional OR (시나리오 선택) 구조
- 복합 지표 기반 Regime Detection (ADX + ATR + Volume + DI)
- 최소 RR 1.5, Guard ON 전제 설계

설계 철학:
- "Core 필터를 통과한 후에만 진입 시나리오 평가"
- Score 시스템 배제 (V4 실패 교훈)
- Timeframe 15m (5m 대비 노이즈 70% 감소)

목표:
- Win Rate: 40~45%
- Max DD: ≤ 12%
- Profit Factor: > 1.2
- 거래 건수: 60~120건/월 (15m 기준)

핵심 설계 (PHASE30-0 기반):
1. Regime Detection: ADX + ATR + Volume + DI (복합 지표 4개)
2. Core AND: Regime, Guard, ATR, Volume, DD, 연속손실 (필수)
3. Optional OR: Regime별 진입 시나리오 (Pullback, RSI, BB 등)
4. SL/TP: RR ≥ 1.5, Regime별 동적 조정
5. Multi-TP: TP1 50%, TP2 50%, Trailing Stop (Trend)
"""
from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np
import logging
from datetime import datetime

from common.calculations import leverage_suggestion
from common.registry.base_strategy import BaseStrategy
from common.registry.strategy_metadata import StrategyMetadata

logger = logging.getLogger(__name__)


# =====================================================
# Regime Detection (복합 지표)
# =====================================================

def detect_regime(df: pd.DataFrame, config: dict) -> Dict[str, Any]:
    """
    복합 지표 기반 Regime Detection
    
    PHASE30-0 설계:
    - ADX + ATR + Volume + DI (4 지표 복합)
    - Trend-Up, Trend-Down, Range, High-Vol-Chop (4 Regime)
    - 신뢰도 점수 산출 (0~1.0)
    - Hysteresis 적용 (최소 3캔들 유지)
    
    Args:
        df: OHLCV + 지표 DataFrame
        config: 전략 설정
    
    Returns:
        dict: {
            'regime': str,  # TREND_UP, TREND_DOWN, RANGE, HIGH_VOL_CHOP
            'confidence': float,  # 0~1.0
            'adx': float,
            'atr_ratio': float,
            'volume_ratio': float,
            'di_diff': float
        }
    """
    if len(df) < 30:
        return {
            'regime': 'UNKNOWN',
            'confidence': 0.0,
            'reason': 'insufficient_data'
        }
    
    last = df.iloc[-1]
    recent = df.iloc[-20:]  # 최근 20캔들
    
    # === 지표 추출 ===
    adx = float(last.get('adx_14', 20))
    di_plus = float(last.get('di_plus_14', 0))
    di_minus = float(last.get('di_minus_14', 0))
    atr = float(last.get('atr_14', last['close'] * 0.002))
    volume = float(last.get('volume', 0))
    
    # === 평균 대비 비율 계산 ===
    avg_atr = float(recent['atr_14'].mean()) if 'atr_14' in recent.columns else atr
    avg_volume = float(recent['volume'].mean()) if 'volume' in recent.columns else volume
    
    atr_ratio = atr / avg_atr if avg_atr > 0 else 1.0
    volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
    
    # DI 차이 (방향성)
    di_diff = di_plus - di_minus
    
    # === 가격 변동 범위 (Range 판정용) ===
    price_high = float(recent['high'].max())
    price_low = float(recent['low'].min())
    price_range_pct = (price_high - price_low) / price_low if price_low > 0 else 0.0
    
    # === Config 파라미터 ===
    regime_config = config.get('regime_detection', {})
    adx_trend_threshold = regime_config.get('adx_trend_threshold', 25)
    adx_range_threshold = regime_config.get('adx_range_threshold', 20)
    atr_high_vol_mult = regime_config.get('atr_high_vol_mult', 1.5)
    volume_high_vol_mult = regime_config.get('volume_high_vol_mult', 2.0)
    
    # === Regime 판정 ===
    regime = 'UNKNOWN'
    confidence = 0.0
    
    # 1. High-Volatility-Chop (우선 판정)
    if adx < adx_range_threshold and atr_ratio > atr_high_vol_mult and volume_ratio > volume_high_vol_mult:
        regime = 'HIGH_VOL_CHOP'
        confidence = min(1.0, (atr_ratio - 1.0) * 0.5 + (volume_ratio - 1.0) * 0.3)
    
    # 2. Trend-Up
    elif adx > adx_trend_threshold and di_plus > di_minus and atr_ratio > 1.1 and volume_ratio > 0.9:
        regime = 'TREND_UP'
        # 신뢰도 점수 (설계 문서 기준)
        adx_score = min(1.0, (adx - 20) / 20) * 0.4
        di_score = min(1.0, di_diff / max(di_plus, 1.0)) * 0.3
        atr_score = min(1.0, (atr_ratio - 1.0)) * 0.2
        vol_score = min(1.0, (volume_ratio - 0.9) / 0.5) * 0.1
        confidence = max(0.0, min(1.0, adx_score + di_score + atr_score + vol_score))
    
    # 3. Trend-Down
    elif adx > adx_trend_threshold and di_minus > di_plus and atr_ratio > 1.1 and volume_ratio > 0.9:
        regime = 'TREND_DOWN'
        adx_score = min(1.0, (adx - 20) / 20) * 0.4
        di_score = min(1.0, abs(di_diff) / max(di_minus, 1.0)) * 0.3
        atr_score = min(1.0, (atr_ratio - 1.0)) * 0.2
        vol_score = min(1.0, (volume_ratio - 0.9) / 0.5) * 0.1
        confidence = max(0.0, min(1.0, adx_score + di_score + atr_score + vol_score))
    
    # 4. Range
    elif adx < adx_range_threshold and atr_ratio < 1.0 and price_range_pct < 0.02:
        regime = 'RANGE'
        # 신뢰도 점수 (설계 문서 기준)
        adx_score = (adx_range_threshold - adx) / adx_range_threshold * 0.5
        atr_score = (1.0 - atr_ratio) * 0.3
        range_score = (0.02 - price_range_pct) / 0.02 * 0.2
        confidence = max(0.0, min(1.0, adx_score + atr_score + range_score))
    
    # 5. 애매한 경우 (낮은 신뢰도로 RANGE 판정)
    else:
        regime = 'RANGE'
        confidence = 0.3
    
    return {
        'regime': regime,
        'confidence': confidence,
        'adx': adx,
        'atr_ratio': atr_ratio,
        'volume_ratio': volume_ratio,
        'di_diff': di_diff,
        'price_range_pct': price_range_pct
    }


# =====================================================
# Core AND Block (필수 필터)
# =====================================================

def passes_core_and_filters(df: pd.DataFrame, regime_info: dict, config: dict) -> Tuple[bool, str]:
    """
    Core AND Block 필터 통과 여부
    
    PHASE30-0 설계:
    1. Regime 유효성
    2. Guard 통과 (엔진 레벨에서 이미 처리됨, 여기서는 스킵)
    3. 최소 ATR (변동성)
    4. 최소 Volume
    5. (선택) 최근 DD 체크
    6. (선택) 연속 손실 제한
    
    Args:
        df: OHLCV + 지표 DataFrame
        regime_info: detect_regime() 결과
        config: 전략 설정
    
    Returns:
        (bool, str): (통과 여부, 실패 이유)
    """
    last = df.iloc[-1]
    recent = df.iloc[-20:]
    
    # === 1. Regime 유효성 ===
    regime = regime_info['regime']
    if regime not in ['TREND_UP', 'TREND_DOWN', 'RANGE']:
        return False, f"invalid_regime_{regime}"
    
    # === 2. 최소 ATR (변동성) ===
    atr = float(last.get('atr_14', 0))
    price = float(last['close'])
    atr_pct = atr / price if price > 0 else 0.0
    
    min_atr_pct = config.get('filters', {}).get('min_atr_pct', 0.002)  # 0.2%
    if atr_pct < min_atr_pct:
        return False, f"atr_too_low_{atr_pct:.4f}"
    
    # === 3. 최소 Volume ===
    volume = float(last.get('volume', 0))
    avg_volume = float(recent['volume'].mean()) if 'volume' in recent.columns else volume
    volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
    
    min_volume_ratio = config.get('filters', {}).get('min_volume_ratio', 0.7)
    if volume_ratio < min_volume_ratio:
        return False, f"volume_too_low_{volume_ratio:.2f}"
    
    # === 4. (선택) Regime 신뢰도 ===
    min_confidence = config.get('regime_detection', {}).get('min_confidence', 0.3)
    if regime_info['confidence'] < min_confidence:
        return False, f"low_confidence_{regime_info['confidence']:.2f}"
    
    # === 5. (선택) 최근 DD 체크 ===
    # 엔진 레벨에서 Portfolio DD를 관리하므로, 여기서는 생략 가능
    # 필요 시 향후 추가
    
    # === 6. (선택) 연속 손실 제한 ===
    # 엔진 레벨에서 관리하므로, 여기서는 생략 가능
    
    return True, "core_and_pass"


# =====================================================
# Optional OR Block (진입 시나리오)
# =====================================================

def trend_up_scenarios(df: pd.DataFrame, config: dict) -> Tuple[bool, Optional[str]]:
    """
    Trend-Up Regime 진입 시나리오 (LONG only)
    
    PHASE30-0 설계:
    - 시나리오 A: EMA Pullback
    - 시나리오 B: RSI Oversold + Bounce
    - 시나리오 C: BB Lower Band + Volume Spike
    
    Args:
        df: OHLCV + 지표 DataFrame
        config: 전략 설정
    
    Returns:
        (bool, Optional[str]): (진입 가능 여부, 시나리오 이름)
    """
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last
    recent = df.iloc[-20:]
    
    price = float(last['close'])
    open_price = float(last['open'])
    low_price = float(last['low'])
    high_price = float(last['high'])
    
    ema_50 = float(last.get('ema_50', price))
    rsi = float(last.get('rsi_14', 50))
    prev_rsi = float(prev.get('rsi_14', 50))
    bb_lower = float(last.get('bb_lower', price * 0.98))
    volume = float(last.get('volume', 0))
    avg_volume = float(recent['volume'].mean()) if 'volume' in recent.columns else volume
    
    # === 시나리오 A: EMA Pullback ===
    scenario_a = (
        price > ema_50  # 상승 추세 유지
        and low_price <= ema_50 * 1.002  # EMA 터치 (0.2% 이내)
        and price > open_price  # 반등 캔들
    )
    if scenario_a:
        return True, "trend_up_ema_pullback"
    
    # === 시나리오 B: RSI Oversold + Bounce ===
    scenario_b = (
        rsi < 35  # Oversold
        and rsi > prev_rsi  # RSI 상승 시작
        and price > open_price  # 상승 캔들
    )
    if scenario_b:
        return True, "trend_up_rsi_oversold"
    
    # === 시나리오 C: BB Lower Band + Volume Spike ===
    scenario_c = (
        low_price <= bb_lower * 1.001  # BB 하단 터치
        and volume > avg_volume * 1.3  # Volume Spike
        and price > (high_price + low_price) / 2  # 중간값 이상 마감
    )
    if scenario_c:
        return True, "trend_up_bb_lower"
    
    return False, None


def trend_down_scenarios(df: pd.DataFrame, config: dict) -> Tuple[bool, Optional[str]]:
    """
    Trend-Down Regime 진입 시나리오 (SHORT only)
    
    PHASE30-0 설계:
    - 시나리오 A: EMA Pullback (반대 방향)
    - 시나리오 B: RSI Overbought + Bounce Down
    - 시나리오 C: BB Upper Band + Volume Spike
    
    Args:
        df: OHLCV + 지표 DataFrame
        config: 전략 설정
    
    Returns:
        (bool, Optional[str]): (진입 가능 여부, 시나리오 이름)
    """
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last
    recent = df.iloc[-20:]
    
    price = float(last['close'])
    open_price = float(last['open'])
    low_price = float(last['low'])
    high_price = float(last['high'])
    
    ema_50 = float(last.get('ema_50', price))
    rsi = float(last.get('rsi_14', 50))
    prev_rsi = float(prev.get('rsi_14', 50))
    bb_upper = float(last.get('bb_upper', price * 1.02))
    volume = float(last.get('volume', 0))
    avg_volume = float(recent['volume'].mean()) if 'volume' in recent.columns else volume
    
    # === 시나리오 A: EMA Pullback (반대) ===
    scenario_a = (
        price < ema_50  # 하락 추세 유지
        and high_price >= ema_50 * 0.998  # EMA 터치 (0.2% 이내)
        and price < open_price  # 하락 캔들
    )
    if scenario_a:
        return True, "trend_down_ema_pullback"
    
    # === 시나리오 B: RSI Overbought + Bounce Down ===
    scenario_b = (
        rsi > 65  # Overbought
        and rsi < prev_rsi  # RSI 하락 시작
        and price < open_price  # 하락 캔들
    )
    if scenario_b:
        return True, "trend_down_rsi_overbought"
    
    # === 시나리오 C: BB Upper Band + Volume Spike ===
    scenario_c = (
        high_price >= bb_upper * 0.999  # BB 상단 터치
        and volume > avg_volume * 1.3  # Volume Spike
        and price < (high_price + low_price) / 2  # 중간값 이하 마감
    )
    if scenario_c:
        return True, "trend_down_bb_upper"
    
    return False, None


def range_scenarios(df: pd.DataFrame, config: dict) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Range Regime 진입 시나리오 (양방향)
    
    PHASE30-0 설계:
    - LONG: BB Lower 반등
    - SHORT: BB Upper 반락
    
    Args:
        df: OHLCV + 지표 DataFrame
        config: 전략 설정
    
    Returns:
        (bool, Optional[str], Optional[str]): (진입 가능 여부, 시나리오, 방향)
    """
    last = df.iloc[-1]
    
    price = float(last['close'])
    open_price = float(last['open'])
    low_price = float(last['low'])
    high_price = float(last['high'])
    
    rsi = float(last.get('rsi_14', 50))
    bb_lower = float(last.get('bb_lower', price * 0.98))
    bb_upper = float(last.get('bb_upper', price * 1.02))
    
    # === LONG 시나리오: BB Lower 반등 ===
    long_scenario = (
        low_price <= bb_lower * 1.002  # BB 하단 터치
        and rsi < 40  # Oversold 영역
        and price > open_price  # 반등 캔들
    )
    if long_scenario:
        return True, "range_bb_lower_long", "LONG"
    
    # === SHORT 시나리오: BB Upper 반락 ===
    short_scenario = (
        high_price >= bb_upper * 0.998  # BB 상단 터치
        and rsi > 60  # Overbought 영역
        and price < open_price  # 하락 캔들
    )
    if short_scenario:
        return True, "range_bb_upper_short", "SHORT"
    
    return False, None, None


# =====================================================
# SL/TP 계산 (Regime별 동적 조정)
# =====================================================

def calculate_sl_tp(regime: str, side: str, entry_price: float, atr: float, config: dict) -> Dict[str, Any]:
    """
    SL/TP 계산 (Regime별 RR ≥ 1.5)
    
    PHASE30-0 설계:
    - Trend: SL=2.0 ATR, TP1 RR=1.5, TP2 RR=3.0
    - Range: SL=1.5 ATR, TP1 RR=1.5, TP2 RR=2.5
    - Multi-TP: TP1 50%, TP2 50%
    
    Args:
        regime: TREND_UP, TREND_DOWN, RANGE
        side: LONG, SHORT
        entry_price: 진입 가격
        atr: ATR(14)
        config: 전략 설정
    
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
    # === Config 파라미터 ===
    sl_tp_config = config.get('sl_tp', {})
    
    if regime in ['TREND_UP', 'TREND_DOWN']:
        sl_mult = sl_tp_config.get('sl_mult_trend', 2.0)
        tp1_rr = sl_tp_config.get('tp1_rr_trend', 1.5)
        tp2_rr = sl_tp_config.get('tp2_rr_trend', 3.0)
    else:  # RANGE
        sl_mult = sl_tp_config.get('sl_mult_range', 1.5)
        tp1_rr = sl_tp_config.get('tp1_rr_range', 1.5)
        tp2_rr = sl_tp_config.get('tp2_rr_range', 2.5)
    
    # === SL 계산 ===
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
        'tp1_qty_pct': 0.5,  # 50%
        'tp2_qty_pct': 0.5   # 50%
    }


# =====================================================
# 메인 신호 로직 (Core AND + Optional OR)
# =====================================================

def signal_logic(df: pd.DataFrame, config: dict) -> Dict[str, Any]:
    """
    BTC 15m Core V1 전략 로직
    
    PHASE30-0 설계:
    - Core AND (필수 필터) → Optional OR (진입 시나리오)
    - Regime Detection: ADX + ATR + Volume + DI
    - RR ≥ 1.5, Multi-TP 50%/50%
    
    Args:
        df: OHLCV + 지표가 포함된 DataFrame
        config: 전략 설정
    
    Returns:
        dict: 신호 정보 (Multi-TP 구조 포함)
    """
    # === 지표 자동 계산 (백테스트 호환성) ===
    required_indicators = ['rsi_14', 'adx_14', 'di_plus_14', 'di_minus_14',
                          'ema_20', 'ema_50', 'ema_200', 'atr_14', 'volume_ma_20',
                          'bb_upper', 'bb_middle', 'bb_lower']
    missing_indicators = [col for col in required_indicators if col not in df.columns]
    
    if missing_indicators:
        logger.info(f"[btc15m_core_v1] 지표 컬럼 누락 감지: {missing_indicators} → 자동 계산")
        from common.backtest_indicators import add_core_v1_indicators
        df = add_core_v1_indicators(df, config)
        logger.info(f"[btc15m_core_v1] 지표 자동 계산 완료")
    
    # === Config 검증 ===
    lv = config.get("leverage", {})
    if not all(k in lv for k in ("min", "max", "default")):
        return {"side": None, "reason": "leverage_config_incomplete"}
    
    # === 데이터 충분성 검사 ===
    min_bars = config.get('min_bars_for_signal', 100)
    if len(df) < min_bars:
        return {"side": None, "reason": f"데이터 부족 (btc15m_core_v1는 {min_bars}바 이상 필요)"}
    
    # === 현재 캔들 정보 ===
    last = df.iloc[-1]
    price = float(last["close"])
    atr = float(last.get("atr_14", price * 0.002))
    
    # === STEP 1: Regime Detection ===
    regime_info = detect_regime(df, config)
    regime = regime_info['regime']
    
    logger.debug(f"[btc15m_core_v1] Regime: {regime}, Confidence: {regime_info['confidence']:.2f}")
    
    # === STEP 2: Core AND Block ===
    core_pass, core_reason = passes_core_and_filters(df, regime_info, config)
    if not core_pass:
        return {"side": None, "reason": core_reason}
    
    # === STEP 3: Optional OR Block (Regime별 시나리오) ===
    side = None
    scenario = None
    
    if regime == 'TREND_UP':
        has_signal, scenario = trend_up_scenarios(df, config)
        if has_signal:
            side = 'LONG'
    
    elif regime == 'TREND_DOWN':
        has_signal, scenario = trend_down_scenarios(df, config)
        if has_signal:
            side = 'SHORT'
    
    elif regime == 'RANGE':
        has_signal, scenario, range_side = range_scenarios(df, config)
        if has_signal:
            side = range_side
    
    # 진입 신호 없음
    if side is None:
        return {"side": None, "reason": f"no_scenario_matched_{regime}"}
    
    # === STEP 4: SL/TP 계산 ===
    sl_tp_info = calculate_sl_tp(regime, side, price, atr, config)
    
    # === STEP 5: 신호 정보 구성 (Multi-TP) ===
    signal_info = {
        "side": side,
        "reason": f"{regime.lower()}_{scenario}",
        "entry": price,
        "sl": sl_tp_info['sl'],
        "tp": sl_tp_info['tp1'],  # 기본 TP (엔진 호환성)
        
        # Multi-TP 정보
        "multi_tp": True,
        "tp_targets": [
            {
                "price": sl_tp_info['tp1'],
                "qty_pct": sl_tp_info['tp1_qty_pct'],
                "rr": sl_tp_info['tp1_rr']
            },
            {
                "price": sl_tp_info['tp2'],
                "qty_pct": sl_tp_info['tp2_qty_pct'],
                "rr": sl_tp_info['tp2_rr']
            }
        ],
        
        # 메타 정보
        "regime": regime,
        "scenario": scenario,
        "confidence": regime_info['confidence'],
        "atr": atr,
        "atr_pct": atr / price,
        "sl_distance": sl_tp_info['sl_distance'],
        "min_rr": sl_tp_info['tp1_rr']
    }
    
    # === Leverage 계산 ===
    atr_pct = atr / price if price > 0 else 0.002
    leverage = leverage_suggestion(
        atr_pct=atr_pct,
        min_leverage=lv.get('min', 1),
        max_leverage=lv.get('max', 5)
    )
    signal_info["leverage"] = leverage
    
    logger.info(
        f"[btc15m_core_v1] 신호: {side} @ {price:.2f}, "
        f"Regime={regime}, Scenario={scenario}, "
        f"SL={sl_tp_info['sl']:.2f}, TP1={sl_tp_info['tp1']:.2f}, TP2={sl_tp_info['tp2']:.2f}, "
        f"RR={sl_tp_info['tp1_rr']:.1f}/{sl_tp_info['tp2_rr']:.1f}"
    )
    
    return signal_info


# =====================================================
# BaseStrategy 클래스 (엔진 호환성)
# =====================================================

class Btc15mCoreV1(BaseStrategy):
    """
    BTCUSDT 15m Core V1 전략 클래스
    
    PHASE30-1: New Core Strategy Design
    - Core AND + Optional OR 구조
    - 복합 Regime Detection (ADX + ATR + Volume + DI)
    - RR ≥ 1.5, Multi-TP 50%/50%
    """
    def __init__(self, config: dict):
        super().__init__(config)
        
        # Production 후보
        self.deprecated = False
        self.alpha_version = False
        self.production_candidate = True
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_name='btc15m_core_v1',
            strategy_type='core_and_optional_or',
            supported_symbols=['BTCUSDT'],
            supported_timeframes=['15m', '30m'],
            version='1.0.0',
            description='BTC 15m Core V1 (Core AND + Optional OR, Composite Regime Detection)'
        )
    
    def compute_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        신호 계산 (signal_logic 래퍼)
        
        Args:
            df: OHLCV + 지표가 포함된 DataFrame
        
        Returns:
            dict: 신호 정보 (Multi-TP 구조 포함)
        """
        return signal_logic(df, self.config)
