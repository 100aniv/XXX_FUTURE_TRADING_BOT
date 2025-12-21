#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BREAKOUT Strategy
=================
돌파 전략 (Donchian Channel + ATR 급등)

전략 개요:
- 타임프레임: 15분
- 핵심: 20일 고점/저점 돌파 (추세 전환 초입)
- 조건: Donchian 돌파 + ATR 급등 + EMA 정렬
"""
from typing import Dict, Any
import pandas as pd

from common.calculations import price_levels, leverage_suggestion
from indicators import regime, detect_volatility_regime


def signal_logic(df: pd.DataFrame, config: dict) -> Dict[str, Any]:
    """
    BREAKOUT 전략: Donchian Channel 돌파 + ATR 급등
    
    Args:
        df: OHLCV + 지표가 포함된 DataFrame (dc_upper, dc_lower 포함)
        config: 전략 설정 (CFG)
    
    Returns:
        dict: 신호 정보
    
    전략 로직:
    - LONG: Donchian 고점 돌파 + EMA 상승 + ATR 급등
    - SHORT: Donchian 저점 돌파 + EMA 하락 + ATR 급등
    - 거래량 급증 = 더 강한 신호
    """
    # PHASE22-1: leverage config 검증
    lv = config.get("leverage", {})
    if not all(k in lv for k in ("min", "max", "default")):
        return {"signal": 0, "reason": "leverage_config_incomplete"}
    
    # 데이터 부족 시 skip (iloc[-2] 안전성)
    if len(df) < 2:
        return {"signal": 0, "reason": "insufficient_data"}
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 기본 정보
    reg = regime(last)
    price = float(last["close"])
    atr = float(last["atr"])
    atr_pct = atr / price
    
    # ✅ Donchian Channel 돌파
    dc_upper_break = last["close"] > last["dc_upper"]  # 상단 돌파
    dc_lower_break = last["close"] < last["dc_lower"]  # 하단 돌파
    
    # ✅ 이전 캔들이 채널 안에 있었는지 확인 (진짜 돌파)
    prev_inside = prev["dc_lower"] < prev["close"] < prev["dc_upper"]
    
    # ⭐ 변동성 확대 (ATR 증가)
    atr_prev = float(prev["atr"])
    atr_expanding_mult = float(config.get('atr_expanding_mult', 1.1))
    atr_expanding = atr > atr_prev * atr_expanding_mult  # ATR 증가 확인
    
    # ⭐ EMA 정렬 (추세 확인)
    ema_align_long = last["ema_fast"] > last["ema_mid"] > last["ema_slow"]
    ema_align_short = last["ema_fast"] < last["ema_mid"] < last["ema_slow"]
    
    # ⭐ MACD 방향
    macd_up = last["macd"] > last["macd_signal"]
    macd_down = last["macd"] < last["macd_signal"]
    
    # 파라미터화: RSI 범위, 숏 허용
    rsi_min = float(config.get('rsi_min', 30))
    rsi_max = float(config.get('rsi_max', 70))
    rsi_ok = rsi_min < last["rsi"] < rsi_max
    short_allowed = (config.get('filters', {}) or {}).get('allow_short', config.get('allow_short', True))
    use_rsi_filter = bool((config.get('filters', {}) or {}).get('enable_rsi_filter', config.get('enable_rsi_filter', False)))
    
    # ⭐ 거래량 급증
    vol_mult = float(config.get('volume_mult', 1.5))
    vol_surge = last["volume"] > last["vol_ma"] * vol_mult

    # 간단한 레짐 프리셋(백테스트 파일명 기반) 보정
    
    # ⭐ 신호 조건 (극도로 간소화 - 테스트용)
    side = None
    action = None
    reason = []
    
    # LONG: Donchian 돌파 + EMA 상승 (기본)
    if (dc_upper_break and last["ema_fast"] > last["ema_slow"] and ((not use_rsi_filter) or rsi_ok)):
        side = "LONG"
        action = "진입"
        reason.append("Donchian 상단 돌파")
        reason.append("EMA 상승 추세")
        if atr_expanding:
            reason.append("변동성 확대")
        if vol_surge:
            reason.append("거래량 급증")
    
    # SHORT: Donchian 돌파 + EMA 하락 (기본)
    elif short_allowed and (dc_lower_break and last["ema_fast"] < last["ema_slow"] and ((not use_rsi_filter) or rsi_ok)):
        side = "SHORT"
        action = "진입"
        reason.append("Donchian 하단 돌파")
        reason.append("EMA 하락 추세")
        if atr_expanding:
            reason.append("변동성 확대")
        if vol_surge:
            reason.append("거래량 급증")
    
    # 가격 레벨 계산
    entry, sl, tp = (None, None, None)
    if side:
        # ⭐ CRITICAL: 변동성 레짐 감지

        vol_regime = detect_volatility_regime(df)

        atr_mult_adjusted = config["atr_mult_sl"]

        if vol_regime == 'high_vol':

            atr_mult_adjusted *= 1.2

        elif vol_regime == 'low_vol':

            atr_mult_adjusted *= 0.9

        

        entry, sl, tp = price_levels(
            side, price, atr,
            config["rr"],

            atr_mult_adjusted
        )
    
    # 레버리지 제안
    lev = leverage_suggestion(
        atr_pct,
        config['leverage']['min'],
        config['leverage']['max']
    )
    
    return {
        "regime": reg,
        "price": price,
        "atr": atr,
        "atr_pct": atr_pct,
        "rsi": float(last["rsi"]),
        "macd": float(last["macd"]),
        "macd_signal": float(last["macd_signal"]),
        "dc_upper": float(last["dc_upper"]),
        "dc_lower": float(last["dc_lower"]),
        "dc_mid": float(last["dc_mid"]),
        "bb_upper": float(last["bb_upper"]),
        "bb_lower": float(last["bb_lower"]),
        "ema_fast": float(last["ema_fast"]),
        "ema_mid": float(last["ema_mid"]),
        "ema_slow": float(last["ema_slow"]),
        "side": side,
        "action": action,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "lev": lev,
        "ts": int(last["time"].timestamp()) if hasattr(last["time"], 'timestamp') else int(last["time"]),
        "reason": reason,
        "volume": float(last["volume"]),
        "vol_ma": float(last["vol_ma"]),
    }


# ============================================================================
# PHASE19-1: BaseStrategy 래퍼
# ============================================================================
from common.registry.base_strategy import BaseStrategy
from common.registry.strategy_metadata import StrategyMetadata
from typing import Dict, Any


class BreakoutStrategy(BaseStrategy):
    """
    Breakout 전략 (돌파)
    
    **전략 특징**:
    - 타임프레임: 15m
    - Donchian Channel 돌파 + ATR 급등
    - 추세 전환 초입 포착
    
    **PHASE19-1 래퍼**:
    - 기존 signal_logic() 함수 호출
    - BaseStrategy 인터페이스 구현
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_name='breakout',
            strategy_type='breakout',
            supported_symbols=[],  # 모든 심볼 지원
            supported_timeframes=['15m', '30m', '1h'],
            version='v1.0',
            description='Donchian Channel 돌파 + ATR 급등 기반 추세 전환 포착',
            # PHASE19-2: Ensemble Score System
            optimal_regime='breakout',
            worst_regime='ranging',
            base_weight=0.8,
            factor_weights={
                'breakout_probability': 0.5,
                'volatility': 0.2,
                'volume': 0.2,
                'trend_strength': 0.1,
            }
        )
    
    def compute_signal(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """신호 계산 (기존 signal_logic 호출)"""
        return signal_logic(df, self.config)
