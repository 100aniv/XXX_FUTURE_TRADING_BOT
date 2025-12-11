#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTCUSDT 5m Baseline Strategy V3 (PHASE29-1)
============================================
⚠️ STRATEGY STATUS: DEPRECATED
⚠️ REASON: PHASE29-2C-R — Structural signal deficiency. Unable to reach required trade frequency.
⚠️ DO NOT USE FOR BACKTEST, PAPER, OR LIVE.

Deprecation Details:
- PHASE29-2A: 1일 0건, 1주 1건 (Signal Rate 0.045%)
- PHASE29-2B Scenario A+: 1주 20건 (최소 목표 달성)
- PHASE29-2C-R: 1개월 17건 (목표 80-240건, 달성률 7.1~21.3%)
- 근본 원인: AND 로직 과잉 결합 + 엄격한 Threshold → 교집합 극소
- Config 파라미터 전달 버그 수정 후에도 거래 건수 동일 (구조적 문제 확인)

Regime-Aware Pullback + Multi-TP + Enhanced Filtering

목적 (설계 단계):
- V2의 근본적 문제 해결 (Win Rate < 45%, Drawdown 10% 조기 종료)
- Trend Pullback 진입 (추세 조정에서 재진입)
- Range Mean Reversion 강화
- Multi-TP 구조 (1차 TP 60%, 2차 TP 40%)
- Filter 계층 강화 (ATR/Volume/Time/Reentry)

목표 (PHASE29-0 설계):
- Win Rate ≥ 50%
- Average R:R ≥ 1.3 (Multi-TP 평균)
- Max Drawdown ≤ 15% (3개월)
- 전환율 10~20% (품질 우선)

V2 대비 주요 변경:
1. 진입 로직: OR → AND (RSI AND BB AND EMA/ADX Confirmation)
2. TP/SL: 단일 TP → Multi-TP (1차 1.2 ATR, 2차 3.0 ATR)
3. SL 거리: 1.5 ATR → 2.0 ATR (노이즈 필터링)
4. Filter: 최소 ATR/Volume, 시간대, 연속 신호 방지
5. Regime: Trend Pullback vs Range Mean Reversion 명확히 분리

실제 결과 (FAIL):
- 신호 빈도 극소 (AND 로직 과잉)
- 1개월 17건 (목표 대비 78.8~92.9% 부족)
- 전략 폐기 결정 (PHASE29-3)
"""
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
import logging
from datetime import datetime, time

from common.calculations import leverage_suggestion
from common.registry.base_strategy import BaseStrategy
from common.registry.strategy_metadata import StrategyMetadata

# V2 모듈 재사용
from strategies.utils.regime_detector import detect_regime, get_regime_characteristics
from strategies.utils.dynamic_threshold import (
    get_rsi_threshold,
    get_bb_threshold,
    get_momentum_threshold,
    calculate_bb_bands
)

logger = logging.getLogger(__name__)


def signal_logic(df: pd.DataFrame, config: dict) -> Dict[str, Any]:
    """
    BTC 5m Baseline V3 전략 로직 (Trend Pullback + Multi-TP + Enhanced Filters)
    
    Args:
        df: OHLCV + 지표가 포함된 DataFrame (RSI, ADX, DI+, DI-, ATR, BB, EMA 필요)
        config: 전략 설정
    
    Returns:
        dict: 신호 정보 (Multi-TP 구조 포함)
    """
    # === Config 검증 ===
    lv = config.get("leverage", {})
    if not all(k in lv for k in ("min", "max", "default")):
        return {"side": None, "reason": "leverage_config_incomplete"}
    
    # 데이터 충분성 검사
    min_bars = config.get('min_bars_for_signal', 100)  # V3는 100바 필요 (percentile 계산)
    if len(df) < min_bars:
        return {"side": None, "reason": "데이터 부족 (V3는 100바 이상 필요)"}
    
    # === 현재 캔들 정보 ===
    last = df.iloc[-1]
    price = float(last["close"])
    atr = float(last.get("atr_14", price * 0.002))
    atr_pct = atr / price
    
    # === STEP 1: Regime Detection ===
    regime_info = detect_regime(df, config)
    regime = regime_info['regime']
    trend = regime_info['trend']
    volatility = regime_info['volatility']
    
    # Regime 모드 판정 (Trend vs Range)
    mode = "trend" if trend in ["BULL", "BEAR"] else "range"
    
    logger.debug(f"[V3] Regime: {regime} (Mode: {mode}, Trend: {trend}, Vol: {volatility})")
    
    # === STEP 2: V3 필터 계층 (진입 전 사전 차단) ===
    filter_result = _apply_filters(df, config, atr, atr_pct, regime_info)
    if filter_result["passed"] is False:
        return {
            "side": None,
            "reason": filter_result["reason"],
            "metadata": {
                "regime": regime,
                "mode": mode,
                "trend": trend,
                "volatility": volatility,
                "filter_blocked": filter_result["reason"]
            }
        }
    
    # === STEP 3: Threshold 계산 ===
    # Trend 모드: Dynamic Threshold (V2 재사용)
    # Range 모드: 고정 Threshold (PHASE29-2B Scenario A: 30 → 35/65)
    if mode == "trend":
        rsi_long_threshold, rsi_short_threshold = get_rsi_threshold(df, config, regime)
    else:  # range
        rsi_long_threshold = config.get('range_rsi_long_threshold', 35)  # PHASE29-2B Scenario A: 30 → 35
        rsi_short_threshold = config.get('range_rsi_short_threshold', 65)  # PHASE29-2B Scenario A: 70 → 65
    
    bb_mult_main, bb_mult_strong = get_bb_threshold(df, config, regime)
    momentum_threshold = get_momentum_threshold(df, config, regime)
    
    # === STEP 4: 지표 값 추출 ===
    # RSI
    rsi = float(last.get('rsi', 50))
    
    # BB (Dynamic std multiplier 적용)
    bb_main = calculate_bb_bands(df, bb_mult_main, bb_period=20)
    bb_strong = calculate_bb_bands(df, bb_mult_strong, bb_period=20)
    
    # EMA (Trend Pullback 진입 확인용)
    ema_5 = float(last.get('ema_5', price))
    ema_20 = float(last.get('ema_20', price))
    
    # ADX/DI (Trend 강도 확인)
    adx = float(regime_info['adx']) if regime_info['adx'] is not None else 20.0
    di_plus = float(regime_info['di_plus']) if regime_info['di_plus'] is not None else 15.0
    di_minus = float(regime_info['di_minus']) if regime_info['di_minus'] is not None else 15.0
    
    # Momentum
    momentum_lookback = config.get('momentum_lookback', 5)
    if len(df) >= momentum_lookback:
        price_past = float(df.iloc[-momentum_lookback]['close'])
        momentum_pct = (price - price_past) / price_past
    else:
        momentum_pct = 0.0
    
    # === STEP 5: Risk Management 파라미터 (V3 전용) ===
    # Multi-TP 구조
    atr_mult_sl_trend = config.get('atr_mult_sl_trend', 2.0)  # Trend 모드: 2.0 ATR
    atr_mult_sl_range = config.get('atr_mult_sl_range', 1.5)  # Range 모드: 1.5 ATR
    
    # TP 배수 (1차, 2차)
    tp1_mult = config.get('tp1_mult', 1.2)  # 1차 TP: 1.2 * SL distance
    tp2_mult = config.get('tp2_mult', 3.0)  # 2차 TP: 3.0 * SL distance
    
    # TP 포지션 비율 (1차, 2차)
    tp1_size_pct = config.get('tp1_size_pct', 0.6)  # 60%
    tp2_size_pct = config.get('tp2_size_pct', 0.4)  # 40%
    
    # 홀드 타임 (Regime별)
    max_hold_minutes_trend = config.get('max_hold_minutes_trend', 120)  # Trend: 120분
    max_hold_minutes_range = config.get('max_hold_minutes_range', 30)   # Range: 30분
    
    allow_short = config.get('filters', {}).get('allow_short', True)
    
    # ADX threshold (Trend vs Range 추가 확인)
    adx_trend_threshold = config.get('adx_trend_threshold', 25)
    adx_range_threshold = config.get('adx_range_threshold', 20)
    
    # Range 모드 AND 로직 최소 조건 (PHASE29-2B Scenario A: 3 → 2)
    range_min_conditions = config.get('range_min_conditions', 2)
    
    # === STEP 6: Regime별 신호 로직 (AND 로직 강화) ===
    signal = None
    
    if mode == "trend":
        # Trend 모드: Pullback 진입 + 추세 추종
        signal = _generate_trend_signal(
            price, rsi, bb_main, bb_strong, ema_5, ema_20, adx, di_plus, di_minus,
            momentum_pct, rsi_long_threshold, rsi_short_threshold, momentum_threshold,
            adx_trend_threshold, regime_info, allow_short
        )
    else:  # mode == "range"
        # Range 모드: Mean Reversion
        signal = _generate_range_signal(
            price, rsi, bb_main, bb_strong, adx, di_plus, di_minus,
            rsi_long_threshold, rsi_short_threshold, adx_range_threshold,
            regime_info, allow_short, range_min_conditions
        )
    
    # 신호 없음
    if signal is None:
        return {
            "side": None,
            "reason": f"[{regime}] AND 조건 미충족",
            "metadata": {
                "regime": regime,
                "mode": mode,
                "trend": trend,
                "volatility": volatility,
                "rsi": rsi,
                "adx": adx
            }
        }
    
    # === STEP 7: 진입/손절/익절 계산 (Multi-TP) ===
    side = signal["side"]
    entry = price
    
    # SL 거리 (Regime별)
    if mode == "trend":
        sl_distance = atr * atr_mult_sl_trend
        max_hold_minutes = max_hold_minutes_trend
    else:  # range
        sl_distance = atr * atr_mult_sl_range
        max_hold_minutes = max_hold_minutes_range
    
    # TP 거리 (Multi-TP)
    tp1_distance = sl_distance * tp1_mult
    tp2_distance = sl_distance * tp2_mult
    
    if side == "LONG":
        sl = entry - sl_distance
        tp1 = entry + tp1_distance
        tp2 = entry + tp2_distance
    else:  # SHORT
        sl = entry + sl_distance
        tp1 = entry - tp1_distance
        tp2 = entry - tp2_distance
    
    # Leverage 계산 (변동성 기반)
    leverage = leverage_suggestion(
        atr_pct=atr_pct,
        min_leverage=lv["min"],
        max_leverage=lv["max"]
    )
    
    # === 신호 정보 구성 (Multi-TP 구조) ===
    signal_info = {
        "side": side,
        "entry": entry,
        "sl": sl,
        "tp": tp1,  # 기본 TP는 tp1 (엔진 호환성)
        "take_profits": [
            {"price": tp1, "size_pct": tp1_size_pct, "label": "TP1"},
            {"price": tp2, "size_pct": tp2_size_pct, "label": "TP2"}
        ],
        "atr": atr,
        "atr_pct": atr_pct,
        "leverage": leverage,
        "max_hold_minutes": max_hold_minutes,
        "reason": signal["reason"],
        "metadata": {
            # Regime 정보
            "regime": regime,
            "mode": mode,
            "trend": trend,
            "volatility": volatility,
            
            # 지표 값
            "rsi": rsi,
            "rsi_long_threshold": rsi_long_threshold,
            "rsi_short_threshold": rsi_short_threshold,
            "adx": adx,
            "di_plus": di_plus,
            "di_minus": di_minus,
            "ema_5": ema_5,
            "ema_20": ema_20,
            
            # BB 정보
            "bb_mult_main": bb_mult_main,
            "bb_mult_strong": bb_mult_strong,
            "bb_main_upper": bb_main['upper'],
            "bb_main_lower": bb_main['lower'],
            "bb_strong_upper": bb_strong['upper'],
            "bb_strong_lower": bb_strong['lower'],
            
            # Multi-TP 정보
            "tp1": tp1,
            "tp2": tp2,
            "tp1_size_pct": tp1_size_pct,
            "tp2_size_pct": tp2_size_pct,
            "sl_distance_atr": sl_distance / atr,
            "tp1_rr": tp1_distance / sl_distance,
            "tp2_rr": tp2_distance / sl_distance,
            
            # 기타
            "momentum_pct": momentum_pct,
            "momentum_threshold": momentum_threshold,
            "atr_percentile": regime_info['atr_percentile'],
            
            # V3 신호 세부 정보
            "signal_conditions": signal.get("conditions", [])
        }
    }
    
    return signal_info


# =====================================================
# V3 Filter 계층 (진입 전 사전 차단)
# =====================================================

def _apply_filters(df: pd.DataFrame, config: dict, atr: float, atr_pct: float, 
                   regime_info: dict) -> dict:
    """
    V3 Filter 계층: 진입 전 사전 차단
    
    Returns:
        dict: {"passed": bool, "reason": str}
    """
    filters_config = config.get('v3_filters', {})
    
    # Filter 1: 최소 ATR (극단적 낮은 변동성 배제)
    # PHASE29-2B Scenario A: baseline 0.002 * 0.9 = 0.0018 (0.18%)
    min_atr_pct = filters_config.get('min_atr_pct', 0.0018)  # 0.18%
    if filters_config.get('enable_min_atr', True):
        if atr_pct < min_atr_pct:
            return {
                "passed": False,
                "reason": f"[FILTER] ATR 너무 낮음: {atr_pct*100:.3f}% < {min_atr_pct*100:.2f}%"
            }
    
    # Filter 2: 최소/최대 Volume (비정상 거래량 배제)
    if filters_config.get('enable_volume_filter', True):
        last = df.iloc[-1]
        volume = float(last.get('volume', 0))
        
        # Volume MA 대비 비율 확인
        # PHASE29-2B Scenario A: baseline 1.5 → 1.3 (즉, MA의 1.3배 이상 요구 → 더 낮은 threshold인 0.77배 통과 허용)
        volume_ma = float(last.get('volume_ma_20', volume))
        if volume_ma > 0:
            volume_ratio = volume / volume_ma
            min_vol_ratio = filters_config.get('min_volume_ratio', 0.77)
            if volume_ratio < min_vol_ratio:
                return {
                    "passed": False,
                    "reason": f"[FILTER] Volume 너무 낮음: {volume_ratio:.2f}x < {min_vol_ratio}x"
                }
    
    # Filter 3: 시간대 필터 (비유동 시간대 제한)
    if filters_config.get('enable_time_filter', False):
        last = df.iloc[-1]
        if 'timestamp' in df.columns or 'datetime' in df.columns:
            ts_col = 'timestamp' if 'timestamp' in df.columns else 'datetime'
            current_time = pd.to_datetime(last[ts_col]).time()
            
            # 비유동 시간대 (예: UTC 00:00~02:00, 새벽)
            blackout_start = time(0, 0)
            blackout_end = time(2, 0)
            
            if blackout_start <= current_time <= blackout_end:
                return {
                    "passed": False,
                    "reason": f"[FILTER] 비유동 시간대: {current_time}"
                }
    
    # Filter 4: 연속 신호 방지 (동일 방향 재진입 제한)
    # (이 필터는 전략 외부(SignalGenerator/Guard)에서도 처리되지만, 전략 내부에서도 추가 확인)
    # NOTE: 실제 구현 시 ctx 또는 state 필요, 여기서는 스킵
    
    # 모든 필터 통과
    return {"passed": True, "reason": ""}


# =====================================================
# Trend 모드: Pullback 진입 + 추세 추종
# =====================================================

def _generate_trend_signal(
    price: float, rsi: float, bb_main: dict, bb_strong: dict,
    ema_5: float, ema_20: float, adx: float, di_plus: float, di_minus: float,
    momentum_pct: float, rsi_long_thresh: float, rsi_short_thresh: float,
    momentum_thresh: float, adx_trend_threshold: float, regime_info: dict,
    allow_short: bool
) -> Optional[Dict[str, Any]]:
    """
    Trend 모드 신호 생성 (Pullback 진입 + AND 로직)
    
    V3 변경:
    - OR → AND 로직 (RSI AND BB AND EMA/ADX)
    - EMA Pullback 확인 (Price가 EMA 5/20 사이)
    - ADX ≥ 25 확인 (추세 강도)
    - DI+/DI- 방향 확인
    """
    trend = regime_info['trend']
    
    # ADX가 너무 낮으면 Trend 모드에서 진입하지 않음
    if adx < adx_trend_threshold:
        return None
    
    # LONG 신호 (Bull Trend에서 Pullback 진입)
    if trend == "BULL":
        conditions = []
        
        # 조건 1: RSI < threshold (과매도 구간)
        if rsi < rsi_long_thresh:
            conditions.append("RSI_PULLBACK")
        
        # 조건 2: Price < BB Main Lower (밴드 하단 근처)
        if price < bb_main['lower']:
            conditions.append("BB_LOWER")
        
        # 조건 3: EMA Pullback (Price가 EMA 5와 EMA 20 사이에 위치)
        #         → 추세 유지 중 조정 구간
        if ema_20 < price < ema_5:
            conditions.append("EMA_PULLBACK")
        
        # 조건 4: DI+ > DI- (Bull 방향 확인)
        if di_plus > di_minus:
            conditions.append("DI_BULL")
        
        # AND 로직: 최소 3개 조건 충족 시 진입
        if len(conditions) >= 3:
            return {
                "side": "LONG",
                "reason": f"[TREND_BULL] Pullback 진입: {', '.join(conditions)}",
                "conditions": conditions
            }
    
    # SHORT 신호 (Bear Trend에서 Pullback 진입)
    elif trend == "BEAR" and allow_short:
        conditions = []
        
        # 조건 1: RSI > threshold (과매수 구간)
        if rsi > rsi_short_thresh:
            conditions.append("RSI_PULLBACK")
        
        # 조건 2: Price > BB Main Upper (밴드 상단 근처)
        if price > bb_main['upper']:
            conditions.append("BB_UPPER")
        
        # 조건 3: EMA Pullback (Price가 EMA 20과 EMA 5 사이에 위치)
        #         → 추세 유지 중 조정 구간
        if ema_5 < price < ema_20:
            conditions.append("EMA_PULLBACK")
        
        # 조건 4: DI- > DI+ (Bear 방향 확인)
        if di_minus > di_plus:
            conditions.append("DI_BEAR")
        
        # AND 로직: 최소 3개 조건 충족 시 진입
        if len(conditions) >= 3:
            return {
                "side": "SHORT",
                "reason": f"[TREND_BEAR] Pullback 진입: {', '.join(conditions)}",
                "conditions": conditions
            }
    
    return None


# =====================================================
# Range 모드: Mean Reversion
# =====================================================

def _generate_range_signal(
    price: float, rsi: float, bb_main: dict, bb_strong: dict,
    adx: float, di_plus: float, di_minus: float,
    rsi_long_thresh: float, rsi_short_thresh: float, adx_range_threshold: float,
    regime_info: dict, allow_short: bool, range_min_conditions: int = 3
) -> Optional[Dict[str, Any]]:
    """
    Range 모드 신호 생성 (Mean Reversion + AND 로직)
    
    V3 변경:
    - OR → AND 로직 (RSI AND BB AND ADX < 20)
    - Range 확인: ADX < 20, DI+ ≈ DI-
    - RSI threshold: config 파라미터 (PHASE29-2B Scenario A: 35/65)
    - Min conditions: config 파라미터 (PHASE29-2B Scenario A: 2)
    """
    # ADX가 너무 높으면 Range 모드에서 진입하지 않음
    if adx > adx_range_threshold:
        return None
    
    # DI+/DI- 차이가 크면 Range가 아님
    di_diff = abs(di_plus - di_minus)
    if di_diff > 5:
        return None
    
    # LONG 신호 (하단 밴드에서 Mean Reversion)
    conditions = []
    
    # 조건 1: RSI < threshold (PHASE29-2B: 30 → 35 완화)
    if rsi < rsi_long_thresh:
        conditions.append("RSI_OVERSOLD")
    
    # 조건 2: Price < BB Lower (밴드 하단)
    if price < bb_main['lower']:
        conditions.append("BB_LOWER")
    
    # 조건 3: ADX < threshold (Range 확인)
    if adx < adx_range_threshold:
        conditions.append("ADX_RANGE")
    
    # AND 로직: 최소 N개 조건 충족 시 진입 (PHASE29-2B: 3 → 2 완화)
    if len(conditions) >= range_min_conditions:
        return {
            "side": "LONG",
            "reason": f"[RANGE] Mean Reversion 진입: {', '.join(conditions)}",
            "conditions": conditions
        }
    
    # SHORT 신호 (상단 밴드에서 Mean Reversion)
    if allow_short:
        conditions_short = []
        
        # 조건 1: RSI > threshold (PHASE29-2B: 70 → 65 완화)
        if rsi > rsi_short_thresh:
            conditions_short.append("RSI_OVERBOUGHT")
        
        # 조건 2: Price > BB Upper (밴드 상단)
        if price > bb_main['upper']:
            conditions_short.append("BB_UPPER")
        
        # 조건 3: ADX < threshold (Range 확인)
        if adx < adx_range_threshold:
            conditions_short.append("ADX_RANGE")
        
        # AND 로직: 최소 N개 조건 충족 시 진입 (PHASE29-2B: 3 → 2 완화)
        if len(conditions_short) >= range_min_conditions:
            return {
                "side": "SHORT",
                "reason": f"[RANGE] Mean Reversion 진입: {', '.join(conditions_short)}",
                "conditions": conditions_short
            }
    
    return None


# =====================================================
# BaseStrategy 클래스 (엔진 호환성)
# =====================================================

class Btc5mBaselineV3(BaseStrategy):
    """
    BTCUSDT 5m Baseline V3 전략 클래스
    
    DEPRECATED: PHASE29-3 - Structural signal deficiency (PHASE29-2C-R FAIL)
    
    PHASE27-5A: StrategyMetadata 통합
    """
    def __init__(self, config: dict):
        super().__init__(config)
        
        # PHASE29-3: Deprecated flag
        self.deprecated = True
        self.deprecation_reason = "PHASE29-2C-R: Structural signal deficiency. Trade count 17/80-240 (7.1~21.3% achievement rate)."
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_name='btc5m_baseline_v3',
            strategy_type='regime_aware',
            supported_symbols=['BTCUSDT'],
            supported_timeframes=['5m'],
            version='3.0.0-deprecated',
            description='[DEPRECATED] BTC 5m Regime-Aware Baseline V3 (Trend Pullback + Multi-TP)'
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
