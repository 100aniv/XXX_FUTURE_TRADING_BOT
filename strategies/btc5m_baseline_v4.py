#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTCUSDT 5m Baseline Strategy V4 (PHASE29-3.1)
=============================================
STATUS: ALPHA (Initial Implementation)

Regime-Aware Hybrid Strategy: OR + Score + Multi-TP

목적:
- V2 문제(OR 과잉 → Win Rate < 45%) 해결
- V3 문제(AND 과잉 → 신호 극소 17건/월) 해결
- OR 기반 + 가중치 점수 합산으로 신호 빈도와 품질 균형

설계 철학:
- "AND 과잉과 OR 과잉의 중간 지점"
- Score Threshold로 신호 빈도 조절 가능
- Regime별 전략 모드 분리 (V3 재사용)
- Multi-TP 구조 유지 (V3 재사용)

목표:
- 신호 빈도: 1주 20~60건, 1개월 80~240건
- Win Rate ≥ 45%
- Sharpe Ratio > 0
- Max DD ≤ 15% (1개월)

주요 변경 (V3 대비):
1. 진입 로직: AND → OR + Score (가중치 합산)
2. Trend Mode: RSI(3점) + BB(2점) + EMA(2점) + DI(1점)
3. Range Mode: RSI(3점) + BB(2점) + ADX(1점)
4. Threshold: trend_min_score=3, range_min_score=2
5. Regime Detection: V3 재사용 (detect_regime)
6. Multi-TP: V3 재사용 (TP1 60%, TP2 40%)
"""
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
import logging
from datetime import datetime, time

from common.calculations import leverage_suggestion
from common.registry.base_strategy import BaseStrategy
from common.registry.strategy_metadata import StrategyMetadata

# V3 모듈 재사용
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
    BTC 5m Baseline V4 전략 로직 (OR + Score + Multi-TP)
    
    Args:
        df: OHLCV + 지표가 포함된 DataFrame
        config: 전략 설정
    
    Returns:
        dict: 신호 정보 (Multi-TP 구조 포함)
    """
    # === PHASE29-3.3: 지표 자동 계산 (백테스트 호환성) ===
    required_indicators = ['rsi_14', 'adx_14', 'di_plus_14', 'di_minus_14', 
                          'ema_5', 'ema_20', 'ema_200', 'atr_14', 'volume_ma_20']
    missing_indicators = [col for col in required_indicators if col not in df.columns]
    
    if missing_indicators:
        logger.info(f"[V4] 지표 컬럼 누락 감지: {missing_indicators} → 자동 계산")
        from common.backtest_indicators import add_v4_indicators
        df = add_v4_indicators(df, config)
        logger.info(f"[V4] 지표 자동 계산 완료")
    
    # === Config 검증 ===
    lv = config.get("leverage", {})
    if not all(k in lv for k in ("min", "max", "default")):
        return {"side": None, "reason": "leverage_config_incomplete"}
    
    # 데이터 충분성 검사
    min_bars = config.get('min_bars_for_signal', 100)
    if len(df) < min_bars:
        return {"side": None, "reason": f"데이터 부족 (V4는 {min_bars}바 이상 필요)"}
    
    # === 현재 캔들 정보 ===
    last = df.iloc[-1]
    price = float(last["close"])
    atr = float(last.get("atr_14", price * 0.002))
    atr_pct = atr / price
    
    # === STEP 1: Regime Detection (V3 재사용) ===
    regime_info = detect_regime(df, config)
    regime = regime_info['regime']
    trend = regime_info['trend']
    volatility = regime_info['volatility']
    
    # Regime 모드 판정 (Trend vs Range)
    mode = "trend" if trend in ["BULL", "BEAR"] else "range"
    
    # === STEP 2: 필터 적용 (선택적) ===
    filter_result = _apply_filters(df, config, atr, atr_pct, regime_info)
    if not filter_result["passed"]:
        logger.debug(f"[V4] Filter 차단: {filter_result['reason']} | Regime: {regime} | ATR%: {atr_pct*100:.3f}%")
        return {
            "side": None,
            "reason": filter_result["reason"],
            "metadata": {
                "regime": regime,
                "mode": mode,
                "filter_fail": True
            }
        }
    
    # === STEP 3: 지표 값 추출 ===
    rsi = float(last.get("rsi_14", 50))
    adx = float(last.get("adx_14", regime_info.get('adx', 25)))
    di_plus = float(last.get("di_plus_14", 25))
    di_minus = float(last.get("di_minus_14", 25))
    ema_5 = float(last.get("ema_5", price))
    ema_20 = float(last.get("ema_20", price))
    
    # BB 계산 (V3 재사용)
    bb_mult_main, bb_mult_strong = get_bb_threshold(df, config, regime)
    bb_main = calculate_bb_bands(df, bb_mult_main, bb_period=20)
    bb_strong = calculate_bb_bands(df, bb_mult_strong, bb_period=20)
    
    # === STEP 4: RSI Threshold ===
    # Trend 모드: Dynamic Threshold (V2/V3 재사용)
    # Range 모드: Config 기반 고정 Threshold
    if mode == "trend":
        rsi_long_threshold, rsi_short_threshold = get_rsi_threshold(df, config, regime)
    else:  # range
        rsi_long_threshold = config.get('range_rsi_threshold', 40)
        rsi_short_threshold = 100 - rsi_long_threshold  # 대칭
    
    # === STEP 5: Score 계산 (OR + 가중치 합산) ===
    signal = None
    score = 0
    conditions = []
    
    if mode == "trend":
        # Trend 모드: Pullback 진입 + OR 기반 Score
        score, conditions, side = _calculate_trend_score(
            price, rsi, bb_main, ema_5, ema_20, adx, di_plus, di_minus,
            rsi_long_threshold, rsi_short_threshold, regime_info, config
        )
        
        # Threshold 체크
        trend_min_score = config.get('trend_min_score', 3)
        logger.debug(f"[V4] Trend Score: {score}/{trend_min_score} | Side: {side} | Conditions: {len(conditions)}")
        if score >= trend_min_score and side is not None:
            logger.info(f"[V4] ✅ Trend 신호: {side} | Score: {score}/{trend_min_score} | {', '.join(conditions[:2])}")
            signal = {
                "side": side,
                "reason": f"[TREND_{trend}] Score {score}/{trend_min_score}: {', '.join(conditions)}",
                "score": score,
                "conditions": conditions
            }
    
    else:  # mode == "range"
        # Range 모드: Mean Reversion + OR 기반 Score
        score, conditions, side = _calculate_range_score(
            price, rsi, bb_main, adx, di_plus, di_minus,
            rsi_long_threshold, rsi_short_threshold, regime_info, config
        )
        
        # Threshold 체크
        range_min_score = config.get('range_min_score', 2)
        logger.debug(f"[V4] Range Score: {score}/{range_min_score} | Side: {side} | Conditions: {len(conditions)}")
        if score >= range_min_score and side is not None:
            logger.info(f"[V4] ✅ Range 신호: {side} | Score: {score}/{range_min_score} | {', '.join(conditions[:2])}")
            signal = {
                "side": side,
                "reason": f"[RANGE] Score {score}/{range_min_score}: {', '.join(conditions)}",
                "score": score,
                "conditions": conditions
            }
    
    # 신호 없음
    if signal is None:
        return {
            "side": None,
            "reason": f"[{regime}] Score {score} 미달 (mode={mode})",
            "metadata": {
                "regime": regime,
                "mode": mode,
                "score": score,
                "rsi": rsi,
                "adx": adx
            }
        }
    
    # === STEP 6: 진입/손절/익절 계산 (Multi-TP, V3 재사용) ===
    side = signal["side"]
    entry = price
    
    # SL/TP 파라미터 (Regime별)
    if mode == "trend":
        atr_mult_sl = config.get('atr_mult_sl_trend', 2.0)
        tp1_mult = config.get('tp1_mult_trend', 1.2)
        tp2_mult = config.get('tp2_mult_trend', 3.0)
        max_hold_minutes = config.get('max_hold_minutes_trend', 120)
    else:  # range
        atr_mult_sl = config.get('atr_mult_sl_range', 1.5)
        tp1_mult = config.get('tp1_mult_range', 1.0)
        tp2_mult = config.get('tp2_mult_range', 2.0)
        max_hold_minutes = config.get('max_hold_minutes_range', 30)
    
    # TP 포지션 비율
    tp1_size_pct = config.get('tp1_size_pct', 0.6)
    tp2_size_pct = config.get('tp2_size_pct', 0.4)
    
    # SL 거리
    sl_distance = atr * atr_mult_sl
    
    # TP 거리
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
    
    # Leverage 계산
    leverage = leverage_suggestion(
        atr_pct=atr_pct,
        min_leverage=lv["min"],
        max_leverage=lv["max"]
    )
    
    # === 신호 정보 구성 (Multi-TP 구조, V3 호환) ===
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
            
            # Score 정보 (V4 핵심)
            "score": signal["score"],
            "conditions": signal["conditions"],
            
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
            
            # Multi-TP 정보
            "tp1": tp1,
            "tp2": tp2,
            "tp1_size_pct": tp1_size_pct,
            "tp2_size_pct": tp2_size_pct,
            "sl_distance_atr": sl_distance / atr,
            "tp1_rr": tp1_distance / sl_distance,
            "tp2_rr": tp2_distance / sl_distance,
        }
    }
    
    return signal_info


# =====================================================
# V4 Filter 계층 (V3 재사용)
# =====================================================

def _apply_filters(df: pd.DataFrame, config: dict, atr: float, atr_pct: float, 
                   regime_info: dict) -> dict:
    """
    V4 Filter 계층: 진입 전 사전 차단
    
    Returns:
        dict: {"passed": bool, "reason": str}
    """
    filters_config = config.get('filters', {})
    
    # Filter 1: 최소 ATR
    min_atr_pct = filters_config.get('min_atr_pct', 0.0015)  # 0.15%
    if filters_config.get('enable_min_atr', True):
        if atr_pct < min_atr_pct:
            return {
                "passed": False,
                "reason": f"[FILTER] ATR 너무 낮음: {atr_pct*100:.3f}% < {min_atr_pct*100:.2f}%"
            }
    
    # Filter 2: 최소 Volume
    if filters_config.get('enable_volume_filter', True):
        last = df.iloc[-1]
        volume = float(last.get('volume', 0))
        volume_ma = float(last.get('volume_ma_20', volume))
        
        if volume_ma > 0:
            volume_ratio = volume / volume_ma
            min_vol_ratio = filters_config.get('min_volume_ratio', 0.5)
            if volume_ratio < min_vol_ratio:
                return {
                    "passed": False,
                    "reason": f"[FILTER] Volume 너무 낮음: {volume_ratio:.2f}x < {min_vol_ratio}x"
                }
    
    # 모든 필터 통과
    return {"passed": True, "reason": ""}


# =====================================================
# V4 Trend Mode: OR + Score (Pullback-in-Trend)
# =====================================================

def _calculate_trend_score(
    price: float, rsi: float, bb_main: dict,
    ema_5: float, ema_20: float, adx: float, di_plus: float, di_minus: float,
    rsi_long_thresh: float, rsi_short_thresh: float, regime_info: dict, config: dict
) -> Tuple[int, List[str], Optional[str]]:
    """
    Trend 모드 Score 계산 (OR 기반 + 가중치 합산)
    
    Returns:
        (score, conditions, side): Score, 충족 조건 목록, 진입 방향
    """
    trend = regime_info['trend']
    
    # ADX 기본 체크
    adx_trend_threshold = config.get('adx_trend_threshold', 25)
    if adx < adx_trend_threshold:
        return (0, [], None)  # Trend 모드에서 ADX 낮으면 진입 안 함
    
    # 가중치 (Config에서 로드)
    weight_rsi = config.get('trend_weight_rsi', 3)
    weight_bb = config.get('trend_weight_bb', 2)
    weight_ema = config.get('trend_weight_ema', 2)
    weight_di = config.get('trend_weight_di', 1)
    
    # SHORT 허용 여부
    allow_short = config.get('filters', {}).get('allow_short', True)
    
    # LONG 신호 (Bull Trend)
    if trend == "BULL":
        score = 0
        conditions = []
        
        # 조건 1: RSI < threshold (Pullback)
        trend_rsi_threshold = config.get('trend_rsi_threshold', 45)
        if rsi < trend_rsi_threshold:
            score += weight_rsi
            conditions.append(f"RSI_PULLBACK({rsi:.1f}<{trend_rsi_threshold})")
        
        # 조건 2: Price < BB Main Lower (조정 구간)
        if price < bb_main['lower']:
            score += weight_bb
            conditions.append(f"BB_LOWER({price:.2f}<{bb_main['lower']:.2f})")
        
        # 조건 3: EMA Pullback (EMA 20 < Price < EMA 5)
        if ema_20 < price < ema_5:
            score += weight_ema
            conditions.append(f"EMA_PULLBACK({ema_20:.2f}<{price:.2f}<{ema_5:.2f})")
        
        # 조건 4: DI+ > DI- (Bull 방향 확인)
        if di_plus > di_minus:
            score += weight_di
            conditions.append(f"DI_BULL({di_plus:.1f}>{di_minus:.1f})")
        
        return (score, conditions, "LONG")
    
    # SHORT 신호 (Bear Trend)
    elif trend == "BEAR" and allow_short:
        score = 0
        conditions = []
        
        # 조건 1: RSI > threshold (Pullback)
        trend_rsi_threshold = config.get('trend_rsi_threshold', 55)  # SHORT는 대칭
        if rsi > 100 - trend_rsi_threshold:  # 대칭: 100 - 45 = 55
            score += weight_rsi
            conditions.append(f"RSI_PULLBACK({rsi:.1f}>{100-trend_rsi_threshold})")
        
        # 조건 2: Price > BB Main Upper
        if price > bb_main['upper']:
            score += weight_bb
            conditions.append(f"BB_UPPER({price:.2f}>{bb_main['upper']:.2f})")
        
        # 조건 3: EMA Pullback (EMA 5 < Price < EMA 20)
        if ema_5 < price < ema_20:
            score += weight_ema
            conditions.append(f"EMA_PULLBACK({ema_5:.2f}<{price:.2f}<{ema_20:.2f})")
        
        # 조건 4: DI- > DI+ (Bear 방향 확인)
        if di_minus > di_plus:
            score += weight_di
            conditions.append(f"DI_BEAR({di_minus:.1f}>{di_plus:.1f})")
        
        return (score, conditions, "SHORT")
    
    return (0, [], None)


# =====================================================
# V4 Range Mode: OR + Score (Mean Reversion)
# =====================================================

def _calculate_range_score(
    price: float, rsi: float, bb_main: dict,
    adx: float, di_plus: float, di_minus: float,
    rsi_long_thresh: float, rsi_short_thresh: float, regime_info: dict, config: dict
) -> Tuple[int, List[str], Optional[str]]:
    """
    Range 모드 Score 계산 (OR 기반 + 가중치 합산)
    
    Returns:
        (score, conditions, side): Score, 충족 조건 목록, 진입 방향
    """
    # ADX 기본 체크
    adx_range_threshold = config.get('adx_range_threshold', 20)
    if adx > adx_range_threshold:
        return (0, [], None)  # Range 모드에서 ADX 높으면 진입 안 함
    
    # DI+/DI- 차이가 크면 Range가 아님
    di_diff = abs(di_plus - di_minus)
    if di_diff > 5:
        return (0, [], None)
    
    # 가중치 (Config에서 로드)
    weight_rsi = config.get('range_weight_rsi', 3)
    weight_bb = config.get('range_weight_bb', 2)
    weight_adx = config.get('range_weight_adx', 1)
    
    # SHORT 허용 여부
    allow_short = config.get('filters', {}).get('allow_short', True)
    
    # LONG 신호 (Mean Reversion)
    score_long = 0
    conditions_long = []
    
    # 조건 1: RSI < threshold (Oversold)
    range_rsi_threshold = config.get('range_rsi_threshold', 40)
    if rsi < range_rsi_threshold:
        score_long += weight_rsi
        conditions_long.append(f"RSI_OVERSOLD({rsi:.1f}<{range_rsi_threshold})")
    
    # 조건 2: Price < BB Main Lower
    if price < bb_main['lower']:
        score_long += weight_bb
        conditions_long.append(f"BB_LOWER({price:.2f}<{bb_main['lower']:.2f})")
    
    # 조건 3: ADX < threshold (Range 확인)
    if adx < adx_range_threshold:
        score_long += weight_adx
        conditions_long.append(f"ADX_RANGE({adx:.1f}<{adx_range_threshold})")
    
    # SHORT 신호 (Mean Reversion)
    score_short = 0
    conditions_short = []
    
    if allow_short:
        # 조건 1: RSI > threshold (Overbought)
        if rsi > 100 - range_rsi_threshold:  # 대칭: 100 - 40 = 60
            score_short += weight_rsi
            conditions_short.append(f"RSI_OVERBOUGHT({rsi:.1f}>{100-range_rsi_threshold})")
        
        # 조건 2: Price > BB Main Upper
        if price > bb_main['upper']:
            score_short += weight_bb
            conditions_short.append(f"BB_UPPER({price:.2f}>{bb_main['upper']:.2f})")
        
        # 조건 3: ADX < threshold
        if adx < adx_range_threshold:
            score_short += weight_adx
            conditions_short.append(f"ADX_RANGE({adx:.1f}<{adx_range_threshold})")
    
    # 높은 Score 방향 선택
    if score_long > score_short:
        return (score_long, conditions_long, "LONG")
    elif score_short > 0:
        return (score_short, conditions_short, "SHORT")
    else:
        return (0, [], None)


# =====================================================
# BaseStrategy 클래스 (엔진 호환성)
# =====================================================

class Btc5mBaselineV4(BaseStrategy):
    """
    BTCUSDT 5m Baseline V4 전략 클래스
    
    PHASE29-3.1: Regime-Aware Hybrid (OR + Score + Multi-TP)
    """
    def __init__(self, config: dict):
        super().__init__(config)
        
        # V4 플래그 (Production Ready 아님)
        self.deprecated = False
        self.alpha_version = True
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_name='btc5m_baseline_v4',
            strategy_type='regime_aware_hybrid',
            supported_symbols=['BTCUSDT'],
            supported_timeframes=['5m'],
            version='4.0.0-alpha',
            description='BTC 5m Regime-Aware Hybrid V4 (OR + Score + Multi-TP)'
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
