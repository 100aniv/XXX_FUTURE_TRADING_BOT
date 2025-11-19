#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Dict, Any
import pandas as pd

from common.calculations import price_levels, leverage_suggestion
from indicators import regime, detect_volatility_regime


def signal_logic(df: pd.DataFrame, config: dict) -> Dict[str, Any]:
    """
    REVERSION v3: 완화된 조건 + 확인 필터
    
    Args:
        df: OHLCV + 지표가 포함된 DataFrame
        config: 전략 설정
    
    Returns:
        dict: 신호 정보
    
    전략 로직 v3 (데이터 기반 재설계):
    - LONG 조건 (2단계):
      1) 과매도: RSI < 35 (완화) + BB 하단 근접 (98% 이하)
      2) 반전 확인: MACD 상승 전환 OR 양봉 + 거래량 증가
    
    - SHORT 조건 (2단계):
      1) 과매수: RSI > 65 (완화) + BB 상단 근접 (102% 이상)
      2) 반전 확인: MACD 하락 전환 OR 음봉 + 거래량 증가
    
    변경 이력:
    - Cycle 1: RSI 40, OR 조건 → 실패 (PF 0.41, 8,797건)
    - Cycle 2 v2: RSI 30, AND 조건 (엄격) → 실패 (PF 0.42, 72~90건, 승률 25%)
    - Cycle 2 v3: RSI 35, 2단계 필터 → 테스트 대기
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
    
    # === 파라미터 (튜닝 대상) ===
    rsi_oversold_threshold = float(config.get('rsi_threshold', 35))  # 완화: 30 → 35
    rsi_overbought_threshold = 100 - rsi_oversold_threshold
    bb_lower_pct = float(config.get('bb_lower_pct', 0.98))  # BB 하단 근접: 98%
    bb_upper_pct = float(config.get('bb_upper_pct', 1.02))  # BB 상단 근접: 102%
    volume_mult = float(config.get('volume_mult', 1.2))  # 거래량 증가: 1.2배

    # 간단한 레짐 프리셋(백테스트 파일명 기반) 보정
    
    # === 1단계: 과매도/과매수 영역 ===
    
    # RSI 임계값 (완화)
    rsi_oversold = last["rsi"] < rsi_oversold_threshold
    rsi_overbought = last["rsi"] > rsi_overbought_threshold
    
    # BB 밴드 근접 (완화: 터치 → 근접)
    bb_near_lower = last["close"] <= last["bb_lower"] * bb_lower_pct
    bb_near_upper = last["close"] >= last["bb_upper"] * bb_upper_pct
    
    # === 2단계: 반전 확인 필터 ===
    
    # MACD 방향 전환
    macd_turning_up = last["macd"] > last["macd_signal"] and prev["macd"] <= prev["macd_signal"]
    macd_turning_down = last["macd"] < last["macd_signal"] and prev["macd"] >= prev["macd_signal"]
    
    # 가격 액션 (양봉/음봉)
    bullish_candle = last["close"] > last["open"]
    bearish_candle = last["close"] < last["open"]
    
    # 거래량 증가
    volume_surge = last["volume"] > last["vol_ma"] * volume_mult
    volume_filter_required = bool(
        (config.get('filters', {}) or {}).get('volume_spike') or config.get('volume_spike', False)
    )
    
    # EMA 추세 (참고용, 필수 아님)
    in_downtrend = last["ema_fast"] < last["ema_mid"] < last["ema_slow"]
    in_uptrend = last["ema_fast"] > last["ema_mid"] > last["ema_slow"]
    
    # 옵션: EMA 컨텍스트(역배열/정배열) 요구 여부
    trend_ctx_required = bool(
        (config.get('filters', {}) or {}).get('trend_context_required') or config.get('trend_context_required', False)
    )
    # 옵션: 숏 허용 여부 (기본 True)
    short_allowed = (config.get('filters', {}) or {}).get('allow_short', config.get('allow_short', True))
    
    # === 신호 생성 (2단계 필터) ===
    side = None
    action = None
    reason = []
    
    # LONG 조건: 과매도 영역 + (옵션) 하락 추세 컨텍스트 + 반전 힌트
    if rsi_oversold and bb_near_lower:
        if (not trend_ctx_required) or in_downtrend:
            # 반전 힌트: MACD 전환 OR 양봉 OR 거래량 (완화)
            if volume_filter_required:
                has_reversal_hint = volume_surge and (macd_turning_up or bullish_candle)
            else:
                has_reversal_hint = macd_turning_up or bullish_candle or volume_surge
            
            if has_reversal_hint:
                side = "LONG"
                action = "진입"
                reason.append(f"RSI 과매도 (<{rsi_oversold_threshold})")
                reason.append(f"BB 하단 근접 (<{bb_lower_pct*100:.0f}%)")
                if macd_turning_up:
                    reason.append("MACD 상승 전환")
                if bullish_candle:
                    reason.append("양봉")
                if volume_surge:
                    reason.append("거래량 증가")
                if in_downtrend:
                    reason.append("하락 추세 중 반등")
    
    # SHORT 조건: 과매수 영역 + (옵션) 상승 추세 컨텍스트 + 반전 힌트
    elif short_allowed and rsi_overbought and bb_near_upper:
        if (not trend_ctx_required) or in_uptrend:
            # 반전 힌트: MACD 전환 OR 음봉 OR 거래량 (완화)
            if volume_filter_required:
                has_reversal_hint = volume_surge and (macd_turning_down or bearish_candle)
            else:
                has_reversal_hint = macd_turning_down or bearish_candle or volume_surge
            
            if has_reversal_hint:
                side = "SHORT"
                action = "진입"
                reason.append(f"RSI 과매수 (>{rsi_overbought_threshold})")
                reason.append(f"BB 상단 근접 (>{bb_upper_pct*100:.0f}%)")
                if macd_turning_down:
                    reason.append("MACD 하락 전환")
                if bearish_candle:
                    reason.append("음봉")
                if volume_surge:
                    reason.append("거래량 증가")
                if in_uptrend:
                    reason.append("상승 추세 중 조정")
    
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


class ReversionStrategy(BaseStrategy):
    """
    Reversion 전략 (평균회귀)
    
    **전략 특징**:
    - 타임프레임: 5m, 15m
    - RSI 극단 + BB 이탈 후 회귀
    - v3: 2단계 필터 (과매도/과매수 + 반전 확인)
    
    **PHASE19-1 래퍼**:
    - 기존 signal_logic() 함수 호출
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_name='reversion',
            strategy_type='reversion',
            supported_symbols=[],  # 모든 심볼 지원
            supported_timeframes=['5m', '15m', '30m'],
            version='v3.0',
            description='RSI 극단 + BB 이탈 후 평균회귀 포착 (2단계 필터)',
            # PHASE19-2: Ensemble Score System
            optimal_regime='ranging',
            worst_regime='trending',
            base_weight=0.6,
            factor_weights={
                'overbought_oversold': 0.5,
                'trend_strength': 0.3,
                'volatility': 0.1,
                'volume': 0.1,
            }
        )
    
    def compute_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """신호 계산 (기존 signal_logic 호출)"""
        return signal_logic(df, self.config)
