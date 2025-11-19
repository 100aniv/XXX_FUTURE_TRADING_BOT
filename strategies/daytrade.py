#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DAYTRADE Strategy
=================
단타 전략 (EMA 정렬 + RSI + MACD)

전략 개요:
- 타임프레임: 15분
- 핵심: EMA 정렬 + MACD 전환 + RSI 확인
- 조건: 상용 표준 (레짐 필터 제거)
"""
from typing import Dict, Any
import pandas as pd

from common.calculations import price_levels, leverage_suggestion
from indicators import regime, detect_volatility_regime


def signal_logic(df: pd.DataFrame, config: dict) -> Dict[str, Any]:
    """
    DAYTRADE 전략: EMA 정렬 + RSI + MACD (15분봉)
    
    Args:
        df: OHLCV + 지표가 포함된 DataFrame
        config: 전략 설정 (CFG)
    
    Returns:
        dict: 신호 정보
    
    전략 로직 (상용 표준):
    - LONG: EMA 정렬 + RSI 35+ + MACD 상승전환
    - SHORT: EMA 정렬 + RSI 65- + MACD 하락전환
    - BB 돌파: 추가 신호
    - 레짐 필터: 제거됨 (상용에서 거의 안씀)
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
    
    # MACD 방향 (상용 표준: 크로스 요구 제거)
    macd_up = last["macd"] > last["macd_signal"]  # 위에 있으면 OK
    macd_down = last["macd"] < last["macd_signal"]  # 아래 있으면 OK
    
    # 파라미터
    rsi_long_min = float(config.get('rsi_long_min', 35))
    rsi_short_max = float(config.get('rsi_short_max', 65))
    ema_strict = bool(config.get('ema_strict', True))
    allow_breakout = bool(config.get('allow_breakout', True))
    short_allowed = (config.get('filters', {}) or {}).get('allow_short', config.get('allow_short', True))
    rsi_filter_on = bool((config.get('filters', {}) or {}).get('enable_rsi_filter', config.get('enable_rsi_filter', False)))

    # 간단한 레짐 프리셋(백테스트 파일명 기반) 보정

    # EMA 정렬 (상용 표준: close 조건 제거, 3선 정렬만)
    ema_ok_long = (
        last["ema_fast"] > last["ema_mid"] > last["ema_slow"]
    ) if ema_strict else (
        last["ema_fast"] > last["ema_mid"]
    )
    ema_ok_short = (
        last["ema_fast"] < last["ema_mid"] < last["ema_slow"]
    ) if ema_strict else (
        last["ema_fast"] < last["ema_mid"]
    ) 

    pullback_long = (
        ema_ok_long and
        macd_up and
        (not rsi_filter_on or last["rsi"] >= rsi_long_min)
    )

    pullback_short = (
        ema_ok_short and
        macd_down and
        (not rsi_filter_on or last["rsi"] <= rsi_short_max)
    )

    # BB 돌파
    breakout_long = allow_breakout and (last["close"] > last["bb_upper"]) and macd_up
    breakdown_short = allow_breakout and (last["close"] < last["bb_lower"]) and macd_down
    
    # 신호 판단
    side = None
    action = None
    reason = []
    
    if pullback_long or breakout_long:
        side = "LONG"
        action = "진입"
        if pullback_long:
            reason.append("EMA 정렬 + RSI 확인 + MACD 상승전환")
        if breakout_long:
            reason.append("볼린저밴드 상단 돌파 + 상승 모멘텀")
    
    elif short_allowed and (pullback_short or breakdown_short):
        side = "SHORT"
        action = "진입"
        if pullback_short:
            reason.append("EMA 정렬 + RSI 확인 + MACD 하락전환")
        if breakdown_short:
            reason.append("볼린저밴드 하단 이탈 + 하락 모멘텀")
    
    # 가격 레벨 계산
    entry, sl, tp = (None, None, None)
    if side:
        # ⭐ CRITICAL: 변동성 레짐 감지 (고변동성 시 SL 더 넓게)
        vol_regime = detect_volatility_regime(df)
        
        # SL 배수 조정 (고변동성 +20%, 저변동성 -10%)
        atr_mult_adjusted = config["atr_mult_sl"]
        if vol_regime == 'high_vol':
            atr_mult_adjusted *= 1.2
        elif vol_regime == 'low_vol':
            atr_mult_adjusted *= 0.9
        
        entry, sl, tp = price_levels(
            side, price, atr,
            config["rr"],
            atr_mult_adjusted  # 조정된 배수 사용
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


# ============================================================================
# PHASE19-1: BaseStrategy 래퍼
# ============================================================================
from common.registry.base_strategy import BaseStrategy
from common.registry.strategy_metadata import StrategyMetadata


class DaytradeStrategy(BaseStrategy):
    """Daytrade 전략 (데이 트레이딩)"""
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_name='daytrade',
            strategy_type='daytrade',
            supported_symbols=[],
            supported_timeframes=['15m', '30m', '1h'],
            version='v1.0',
            description='15분/30분/1시간 기반 데이 트레이딩',
            # PHASE19-2: Ensemble Score System
            optimal_regime='trending',
            worst_regime='ranging',
            base_weight=0.9,
            factor_weights={
                'trend_strength': 0.4,
                'breakout_probability': 0.2,
                'momentum': 0.1,
                'volatility': 0.1,
            }
        )
    
    def compute_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        return signal_logic(df, self.config)
