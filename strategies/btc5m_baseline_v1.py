#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTCUSDT 5m Baseline Strategy V1 (PHASE27-3)
============================================
시장 레짐 기반 베이스라인 전략 (ADX 통합)

목적:
- Signal Dropout 문제 해결 (100% False → 실제 신호 발생)
- 현재 시장 레짐(저변동성 횡보)에서 실제 작동하는 전략
- 데이터 프로파일링 결과 기반 threshold 설정
- ADX 기반 추세/횡보 구분으로 적응형 진입 조건

설계 철학:
- **단순함**: 조건 2-3개 이하, AND 최소화
- **현실성**: 퍼센타일 기반 threshold (절대값 X)
- **빈도 우선**: False Positive 감수, Dropout 방지 우선
- **OR 로직**: 여러 조건 중 하나만 만족해도 신호
- **레짐 적응**: ADX 기반 Range/Trend 구분

데이터 프로파일링 결과 (2024-11-30 ~ 2024-12-30, 30일):
- RSI: p25=39.4, p75=60.8 (극단값 <30: 9.96%, >70: 10.25%)
- BB(1.0 std): 돌파 ~25%
- BB(1.5 std): 돌파 ~13%
- Volume: 평균 1.03x, >1.2x 발생률 26.1%
- ATR: 평균 0.21%, 중앙값 0.17%

신호 조건 (PHASE27-3: ADX 레짐 기반):

**Range Regime (ADX <= 25)**: Mean Reversion 강조
  LONG:
    1. RSI < 45 (p25 근처) OR
    2. Price < BB Lower (1.0 std) + 최근 모멘텀 하락 OR
    3. Price < BB Lower (1.5 std)
  SHORT:
    1. RSI > 55 (p75 근처) OR
    2. Price > BB Upper (1.0 std) + 최근 모멘텀 상승 OR
    3. Price > BB Upper (1.5 std)

**Trend Regime (ADX > 25)**: 극단적 조건 우선, 역추세 완화
  LONG:
    1. Price < BB Lower (1.5 std) OR
    2. (Price < BB Lower (1.0 std) AND RSI < 45)
  SHORT:
    1. Price > BB Upper (1.5 std) OR
    2. (Price > BB Upper (1.0 std) AND RSI > 55)

위험 관리:
- SL: ATR × 1.5
- TP: RR 1.5
- 최대 보유: 60분
"""
from typing import Dict, Any
import pandas as pd
import numpy as np
import logging

from common.calculations import price_levels, leverage_suggestion
from common.registry.base_strategy import BaseStrategy
from common.registry.strategy_metadata import StrategyMetadata

logger = logging.getLogger(__name__)

# 파라미터 로그 플래그
_PARAMS_LOGGED = False


def signal_logic(df: pd.DataFrame, config: dict) -> Dict[str, Any]:
    """
    BTC 5m Baseline V1 전략 로직
    
    Args:
        df: OHLCV + 지표가 포함된 DataFrame
        config: 전략 설정
    
    Returns:
        dict: 신호 정보
    """
    global _PARAMS_LOGGED
    
    # Config 검증
    lv = config.get("leverage", {})
    if not all(k in lv for k in ("min", "max", "default")):
        return {"side": None, "reason": "leverage_config_incomplete"}
    
    # 데이터 충분성 검사
    min_bars = config.get('min_bars_for_signal', 50)
    if len(df) < min_bars:
        return {"side": None, "reason": "데이터 부족"}
    
    # 현재 캔들
    last = df.iloc[-1]
    price = float(last["close"])
    atr = float(last.get("atr", price * 0.002))  # Default 0.2%
    atr_pct = atr / price
    
    # 파라미터 로드
    rsi_long_threshold = config.get('rsi_long_threshold', 45)
    rsi_short_threshold = config.get('rsi_short_threshold', 55)
    bb_std_main = config.get('bb_std_main', 1.0)  # 주요 BB std
    bb_std_strong = config.get('bb_std_strong', 1.5)  # 강한 신호 BB std
    momentum_lookback = config.get('momentum_lookback', 5)
    momentum_threshold = config.get('momentum_threshold', 0.001)  # 0.1%
    
    # ADX 레짐 파라미터
    use_adx = config.get('use_adx', False)
    adx_period = config.get('adx_period', 14)
    adx_trend_threshold = config.get('adx_trend_threshold', 25)
    
    rr = config.get('rr', 1.5)
    atr_mult_sl = config.get('atr_mult_sl', 1.5)
    max_hold_minutes = config.get('max_hold_minutes', 60)
    allow_short = config.get('filters', {}).get('allow_short', True)
    
    if not _PARAMS_LOGGED:
        logger.info("=" * 60)
        logger.info("[BTC 5m BASELINE V1 INIT] 파라미터 로드 완료 (PHASE27-3 ADX 통합)")
        logger.info("=" * 60)
        logger.info(f"📊 신호 조건:")
        logger.info(f"  - RSI LONG: < {rsi_long_threshold}")
        logger.info(f"  - RSI SHORT: > {rsi_short_threshold}")
        logger.info(f"  - BB Main: {bb_std_main} std")
        logger.info(f"  - BB Strong: {bb_std_strong} std")
        logger.info(f"  - Momentum: {momentum_lookback}캔들, {momentum_threshold*100:.1f}% 기준")
        logger.info(f"🔄 ADX 레짐:")
        logger.info(f"  - ADX 사용: {use_adx}")
        if use_adx:
            logger.info(f"  - ADX Period: {adx_period}")
            logger.info(f"  - Trend 임계값: {adx_trend_threshold}")
        logger.info(f"⚙️ 위험 관리:")
        logger.info(f"  - RR: {rr}")
        logger.info(f"  - SL 배수: {atr_mult_sl}x ATR")
        logger.info(f"  - 최대 보유: {max_hold_minutes}분")
        logger.info(f"  - 숏 허용: {allow_short}")
        logger.info("=" * 60)
        _PARAMS_LOGGED = True
    
    # BB 밴드 (indicators에서 이미 계산됨, 2.0 std 기본)
    bb_upper_default = float(last.get('bb_upper', price * 1.005))
    bb_lower_default = float(last.get('bb_lower', price * 0.995))
    bb_middle = (bb_upper_default + bb_lower_default) / 2
    
    # BB std 조정 (2.0 기본 → 요청한 std로 변환)
    bb_width_default = bb_upper_default - bb_lower_default
    bb_upper_main = bb_middle + (bb_width_default / 2) * (bb_std_main / 2.0)
    bb_lower_main = bb_middle - (bb_width_default / 2) * (bb_std_main / 2.0)
    bb_upper_strong = bb_middle + (bb_width_default / 2) * (bb_std_strong / 2.0)
    bb_lower_strong = bb_middle - (bb_width_default / 2) * (bb_std_strong / 2.0)
    
    # RSI
    rsi = float(last.get('rsi', 50))
    
    # 최근 모멘텀
    if len(df) >= momentum_lookback:
        price_past = float(df.iloc[-momentum_lookback]['close'])
        momentum_pct = (price - price_past) / price_past
    else:
        momentum_pct = 0.0
    
    # ADX 레짐 판정
    adx_col = f"adx_{adx_period}"
    if use_adx and adx_col in last.index:
        adx = float(last[adx_col])
        is_trend = adx >= adx_trend_threshold
        is_range = not is_trend
        regime = "TREND" if is_trend else "RANGE"
    else:
        # ADX 미사용 또는 컬럼 없음 → Range로 간주 (기존 로직)
        adx = None
        is_range = True
        is_trend = False
        regime = "RANGE (ADX OFF)"
    
    # === LONG 신호 조건 (레짐 기반) ===
    long_signals = []
    
    if is_range:
        # Range Regime: Mean Reversion 강조 (기존 PHASE27-2 로직)
        if rsi < rsi_long_threshold:
            long_signals.append(("RSI", f"RSI={rsi:.1f} < {rsi_long_threshold}"))
        
        if price < bb_lower_main and momentum_pct < -momentum_threshold:
            long_signals.append(("BB_MAIN+MOM", f"Price < BB({bb_std_main}std) & 하락모멘텀"))
        
        if price < bb_lower_strong:
            long_signals.append(("BB_STRONG", f"Price < BB({bb_std_strong}std)"))
    
    else:  # is_trend
        # Trend Regime: 극단적 조건 우선, RSI 단독 완화
        if price < bb_lower_strong:
            long_signals.append(("BB_STRONG", f"Price < BB({bb_std_strong}std) [TREND]"))
        
        if price < bb_lower_main and rsi < rsi_long_threshold:
            long_signals.append(("BB_MAIN+RSI", f"Price < BB({bb_std_main}std) & RSI < {rsi_long_threshold} [TREND]"))
    
    # === SHORT 신호 조건 (레짐 기반) ===
    short_signals = []
    
    if allow_short:
        if is_range:
            # Range Regime
            if rsi > rsi_short_threshold:
                short_signals.append(("RSI", f"RSI={rsi:.1f} > {rsi_short_threshold}"))
            
            if price > bb_upper_main and momentum_pct > momentum_threshold:
                short_signals.append(("BB_MAIN+MOM", f"Price > BB({bb_std_main}std) & 상승모멘텀"))
            
            if price > bb_upper_strong:
                short_signals.append(("BB_STRONG", f"Price > BB({bb_std_strong}std)"))
        
        else:  # is_trend
            # Trend Regime
            if price > bb_upper_strong:
                short_signals.append(("BB_STRONG", f"Price > BB({bb_std_strong}std) [TREND]"))
            
            if price > bb_upper_main and rsi > rsi_short_threshold:
                short_signals.append(("BB_MAIN+RSI", f"Price > BB({bb_std_main}std) & RSI > {rsi_short_threshold} [TREND]"))
    
    # === 신호 판정 (OR 로직) ===
    if long_signals:
        side = "LONG"
        reasons = long_signals
    elif short_signals:
        side = "SHORT"
        reasons = short_signals
    else:
        return {"side": None, "reason": "조건 미충족"}
    
    # === 진입/손절/익절 계산 ===
    entry = price
    sl_distance = atr * atr_mult_sl
    tp_distance = sl_distance * rr
    
    if side == "LONG":
        sl = entry - sl_distance
        tp = entry + tp_distance
    else:  # SHORT
        sl = entry + sl_distance
        tp = entry - tp_distance
    
    # Leverage 계산 (변동성 기반)
    leverage = leverage_suggestion(
        atr_pct=atr_pct,
        min_leverage=lv["min"],
        max_leverage=lv["max"]
    )
    
    # 신호 정보 구성
    signal_info = {
        "side": side,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "atr": atr,
        "atr_pct": atr_pct,
        "leverage": leverage,
        "max_hold_minutes": max_hold_minutes,
        "reason": f"[{regime}] {reasons[0][0]}: {reasons[0][1]}",
        "all_reasons": [f"{r[0]}: {r[1]}" for r in reasons],
        "metadata": {
            "rsi": rsi,
            "bb_middle": bb_middle,
            "bb_upper_main": bb_upper_main,
            "bb_lower_main": bb_lower_main,
            "momentum_pct": momentum_pct,
            "signal_count": len(reasons),
            "regime": regime,
            "adx": adx,
            "use_adx": use_adx,
        }
    }
    
    return signal_info


class BTC5mBaselineV1(BaseStrategy):
    """
    BTCUSDT 5m Baseline Strategy V1
    
    PHASE27-3: Signal Dropout 해결 + ADX 레짐 기반 적응형 전략
    Range/Trend regime에 따라 진입 조건 자동 조정
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_name='btc5m_baseline_v1',
            strategy_type='baseline',
            version='v1.1',
            supported_symbols=['BTCUSDT'],
            supported_timeframes=['5m'],
            description='BTC 5m 베이스라인 전략 - 퍼센타일 + ADX 레짐 기반 (PHASE27-3)',
        )
    
    def compute_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """신호 계산 (BaseStrategy 인터페이스 구현)"""
        return signal_logic(df, self.config)


# 하위 호환성: 기존 방식 지원
def check_signal(df: pd.DataFrame, config: dict) -> Dict[str, Any]:
    """하위 호환: signal_logic 래퍼"""
    return signal_logic(df, config)
