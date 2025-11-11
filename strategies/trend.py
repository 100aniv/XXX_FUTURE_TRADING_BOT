#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TREND Strategy
==============
추세 추종 전략 (EMA 크로스오버 + MACD)

전략 개요:
- 타임프레임: 1시간
- 핵심: 강한 추세 구간만 포착
- 조건: EMA 정렬 + MACD 크로스 + RSI 필터
"""
from typing import Dict, Any
import pandas as pd

from common.calculations import price_levels, leverage_suggestion
from indicators import regime, detect_volatility_regime


def signal_logic(df: pd.DataFrame, config: dict) -> Dict[str, Any]:
    """
    TREND 전략: EMA 크로스오버 + MACD 골든/데드크로스
    
    Args:
        df: OHLCV + 지표가 포함된 DataFrame
        config: 전략 설정 (CFG)
    
    Returns:
        dict: 신호 정보
            - side: "LONG" | "SHORT" | None
            - entry, sl, tp: 가격 레벨
            - lev: 레버리지
            - reason: 신호 이유
            - 기타 지표 값들
    
    전략 로직:
    - LONG: EMA 상승 정렬 + MACD 골든크로스 + RSI 40~70
    - SHORT: EMA 하락 정렬 + MACD 데드크로스 + RSI 30~60
    """
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
    
    # MACD 방향
    macd_up = last["macd"] > last["macd_signal"]
    macd_down = last["macd"] < last["macd_signal"]
    
    # 파라미터
    ema_strict = bool(config.get('ema_strict', True))
    rsi_long_min = float(config.get('rsi_long_min', 40))
    rsi_long_max = float(config.get('rsi_long_max', 70))
    rsi_short_max = float(config.get('rsi_short_max', 60))
    rsi_short_min = float(config.get('rsi_short_min', 30))
    short_allowed = (config.get('filters', {}) or {}).get('allow_short', config.get('allow_short', True))
    rsi_filter_on = bool((config.get('filters', {}) or {}).get('enable_rsi_filter', config.get('enable_rsi_filter', False)))

    # 간단한 레짐 프리셋(백테스트 파일명 기반)

    # EMA 정렬 (강한 추세)
    ema_bullish = (last["ema_fast"] > last["ema_mid"] > last["ema_slow"]) if ema_strict else (last["ema_fast"] > last["ema_mid"]) 
    ema_bearish = (last["ema_fast"] < last["ema_mid"] < last["ema_slow"]) if ema_strict else (last["ema_fast"] < last["ema_mid"]) 
    
    # RSI 조건 (과열 회피)
    rsi_long = (last["rsi"] >= rsi_long_min) and (last["rsi"] < rsi_long_max)
    rsi_short = (last["rsi"] <= rsi_short_max) and (last["rsi"] > rsi_short_min)
    
    # 신호 판단
    side = None
    action = None
    reason = []
    
    # LONG: EMA 상승 정렬 + MACD 방향 (+ 선택적 RSI)
    if ema_bullish and macd_up and (not rsi_filter_on or rsi_long):
        side = "LONG"
        action = "진입"
        reason.append("EMA 상승 정렬 (추세 확인)")
        reason.append("MACD 상방")
    
    # SHORT: EMA 하락 정렬 + MACD 방향 (+ 선택적 RSI)
    elif short_allowed and ema_bearish and macd_down and (not rsi_filter_on or rsi_short):
        side = "SHORT"
        action = "진입"
        reason.append("EMA 하락 정렬 (추세 확인)")
        reason.append("MACD 하방")
    
    # 가격 레벨 계산
    entry, sl, tp = (None, None, None)
    if side:
        entry, sl, tp = price_levels(
            side, price, atr, 
            config["rr"], 
            config["atr_mult_sl"],
            config=config  # ⭐ PHASE7-2 Phase 1: config 전달 (동적 SL/TP)
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
