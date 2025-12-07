#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTCUSDT 5m Baseline Strategy V2 (PHASE28-6/7)
==============================================
Regime-Aware + Dynamic Threshold 전략

목적:
- V1의 근본적 결함 해결 (Mean Reversion → Regime-Adaptive)
- 6-state Regime Detection (Bull/Bear/Range × High/Low Volatility)
- Dynamic Threshold (RSI/BB Rolling Percentile + Volatility 조정)
- 최소 목표: Sharpe ≥ 0 (모든 Period), Trade Count ≥ 20 (월)

설계 원칙:
- **Regime-Aware**: 시장 상태에 따라 진입/청산 조건 동적 변경
- **Dynamic Threshold**: 고정값 금지, 모든 threshold는 상대적 또는 동적
- **Multi-Period Survivable**: Bull/Bear/Range 모든 구간에서 최소 생존
- **Long/Short Balance**: Regime별 포지션 bias 자동 조정

V1 대비 주요 변경:
1. Regime Detection: ADX + DI+/DI- + ATR 기반 6-state 분류
2. RSI Threshold: 고정 45/55 → Rolling percentile (20%/80%)
3. BB Threshold: 고정 1.0/1.5 → Volatility 조정 (0.5-2.5)
4. ParamSpace: 2-3배 확장 (RSI 30-70, BB 0.5-2.5, RR 0.8-3.0)
5. Signal Logic: Regime별로 다른 진입 조건 (6개 상태별 최적화)
"""
from typing import Dict, Any
import pandas as pd
import numpy as np
import logging

from common.calculations import leverage_suggestion
from common.registry.base_strategy import BaseStrategy
from common.registry.strategy_metadata import StrategyMetadata

# V2 전용 모듈
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
    BTC 5m Baseline V2 전략 로직 (Regime-Aware + Dynamic Threshold)
    
    Args:
        df: OHLCV + 지표가 포함된 DataFrame (RSI, ADX, DI+, DI-, ATR, BB 필요)
        config: 전략 설정
    
    Returns:
        dict: 신호 정보
    """
    # === Config 검증 ===
    lv = config.get("leverage", {})
    if not all(k in lv for k in ("min", "max", "default")):
        return {"side": None, "reason": "leverage_config_incomplete"}
    
    # 데이터 충분성 검사
    min_bars = config.get('min_bars_for_signal', 100)  # V2는 100바 필요 (percentile 계산)
    if len(df) < min_bars:
        return {"side": None, "reason": "데이터 부족 (V2는 100바 이상 필요)"}
    
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
    
    logger.debug(f"Regime: {regime} (Trend: {trend}, Vol: {volatility})")
    
    # === STEP 2: Dynamic Threshold 계산 ===
    rsi_long_threshold, rsi_short_threshold = get_rsi_threshold(df, config, regime)
    bb_mult_main, bb_mult_strong = get_bb_threshold(df, config, regime)
    momentum_threshold = get_momentum_threshold(df, config, regime)
    
    # === STEP 3: 지표 값 추출 ===
    # RSI
    rsi = float(last.get('rsi', 50))
    
    # BB (Dynamic std multiplier 적용)
    bb_main = calculate_bb_bands(df, bb_mult_main, bb_period=20)
    bb_strong = calculate_bb_bands(df, bb_mult_strong, bb_period=20)
    
    # Momentum
    momentum_lookback = config.get('momentum_lookback', 5)
    if len(df) >= momentum_lookback:
        price_past = float(df.iloc[-momentum_lookback]['close'])
        momentum_pct = (price - price_past) / price_past
    else:
        momentum_pct = 0.0
    
    # === STEP 4: Risk Management 파라미터 ===
    atr_mult_sl = config.get('atr_mult_sl', 1.5)
    rr = config.get('rr', 1.5)
    max_hold_minutes = config.get('max_hold_minutes', 60)
    allow_short = config.get('filters', {}).get('allow_short', True)
    
    # === STEP 5: Regime별 신호 로직 ===
    long_signals = []
    short_signals = []
    
    # Regime별로 다른 신호 조건 적용
    if regime == 'bull_high_vol':
        long_signals, short_signals = _signal_bull_high_vol(
            price, rsi, bb_main, bb_strong, momentum_pct,
            rsi_long_threshold, rsi_short_threshold, momentum_threshold, regime_info
        )
    elif regime == 'bull_low_vol':
        long_signals, short_signals = _signal_bull_low_vol(
            price, rsi, bb_main, bb_strong, momentum_pct,
            rsi_long_threshold, rsi_short_threshold, momentum_threshold, regime_info
        )
    elif regime == 'bear_high_vol':
        long_signals, short_signals = _signal_bear_high_vol(
            price, rsi, bb_main, bb_strong, momentum_pct,
            rsi_long_threshold, rsi_short_threshold, momentum_threshold, regime_info
        )
    elif regime == 'bear_low_vol':
        long_signals, short_signals = _signal_bear_low_vol(
            price, rsi, bb_main, bb_strong, momentum_pct,
            rsi_long_threshold, rsi_short_threshold, momentum_threshold, regime_info
        )
    elif regime == 'range_high_vol':
        long_signals, short_signals = _signal_range_high_vol(
            price, rsi, bb_main, bb_strong, momentum_pct,
            rsi_long_threshold, rsi_short_threshold, momentum_threshold, regime_info
        )
    elif regime == 'range_low_vol':
        long_signals, short_signals = _signal_range_low_vol(
            price, rsi, bb_main, bb_strong, momentum_pct,
            rsi_long_threshold, rsi_short_threshold, momentum_threshold, regime_info
        )
    else:
        # Unknown regime → Default to range_low_vol
        long_signals, short_signals = _signal_range_low_vol(
            price, rsi, bb_main, bb_strong, momentum_pct,
            rsi_long_threshold, rsi_short_threshold, momentum_threshold, regime_info
        )
    
    # Short 허용 여부 확인
    if not allow_short:
        short_signals = []
    
    # === STEP 6: 신호 판정 (OR 로직) ===
    if long_signals:
        side = "LONG"
        reasons = long_signals
    elif short_signals:
        side = "SHORT"
        reasons = short_signals
    else:
        return {"side": None, "reason": f"[{regime}] 조건 미충족"}
    
    # === STEP 7: 진입/손절/익절 계산 ===
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
    
    # === 신호 정보 구성 ===
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
            "regime": regime,
            "trend": trend,
            "volatility": volatility,
            "rsi": rsi,
            "rsi_long_threshold": rsi_long_threshold,
            "rsi_short_threshold": rsi_short_threshold,
            "bb_mult_main": bb_mult_main,
            "bb_mult_strong": bb_mult_strong,
            "bb_main_upper": bb_main['upper'],
            "bb_main_lower": bb_main['lower'],
            "bb_strong_upper": bb_strong['upper'],
            "bb_strong_lower": bb_strong['lower'],
            "momentum_pct": momentum_pct,
            "momentum_threshold": momentum_threshold,
            "signal_count": len(reasons),
            "adx": regime_info['adx'],
            "di_plus": regime_info['di_plus'],
            "di_minus": regime_info['di_minus'],
            "atr_percentile": regime_info['atr_percentile'],
        }
    }
    
    return signal_info


# =====================================================
# Regime별 신호 로직 (구현 예정)
# =====================================================

def _signal_bull_high_vol(price, rsi, bb_main, bb_strong, momentum_pct,
                          rsi_long_thresh, rsi_short_thresh, momentum_thresh, regime_info):
    """Bull Trend + High Volatility 신호 로직 (추세 추종 + 돌파)"""
    long_signals = []
    short_signals = []
    
    # LONG 진입 (공격적)
    if price < bb_main['lower'] and rsi < rsi_long_thresh:
        long_signals.append(("BB_MAIN+RSI", f"Price < BB Main Lower & RSI < {rsi_long_thresh:.1f}"))
    
    if price < bb_strong['lower']:
        long_signals.append(("BB_STRONG", f"Price < BB Strong Lower"))
    
    if momentum_pct < -momentum_thresh and rsi < rsi_long_thresh:
        long_signals.append(("MOM+RSI", f"하락 모멘텀 & RSI < {rsi_long_thresh:.1f}"))
    
    # SHORT 진입 (매우 보수적)
    if price > bb_strong['upper'] and rsi > rsi_short_thresh * 1.2:  # 극단적 과열만
        short_signals.append(("BB_STRONG+RSI", f"Price > BB Strong Upper & RSI > {rsi_short_thresh*1.2:.1f}"))
    
    return long_signals, short_signals


def _signal_bull_low_vol(price, rsi, bb_main, bb_strong, momentum_pct,
                         rsi_long_thresh, rsi_short_thresh, momentum_thresh, regime_info):
    """Bull Trend + Low Volatility 신호 로직 (조정 매수 + Mean Reversion)"""
    long_signals = []
    short_signals = []
    
    # LONG 진입 (중립)
    if rsi < rsi_long_thresh or price < bb_main['lower']:
        long_signals.append(("RSI_OR_BB", f"RSI < {rsi_long_thresh:.1f} OR Price < BB Main Lower"))
    
    if price < bb_strong['lower']:
        long_signals.append(("BB_STRONG", f"Price < BB Strong Lower"))
    
    # SHORT 진입 (보수적)
    if rsi > rsi_short_thresh and price > bb_strong['upper']:
        short_signals.append(("RSI+BB", f"RSI > {rsi_short_thresh:.1f} & Price > BB Strong Upper"))
    
    return long_signals, short_signals


def _signal_bear_high_vol(price, rsi, bb_main, bb_strong, momentum_pct,
                          rsi_long_thresh, rsi_short_thresh, momentum_thresh, regime_info):
    """Bear Trend + High Volatility 신호 로직 (추세 추종 + 돌파)"""
    long_signals = []
    short_signals = []
    
    # LONG 진입 (매우 보수적)
    if price < bb_strong['lower'] and rsi < rsi_long_thresh * 0.8:  # 극단적 과매도만
        long_signals.append(("BB_STRONG+RSI", f"Price < BB Strong Lower & RSI < {rsi_long_thresh*0.8:.1f}"))
    
    # SHORT 진입 (공격적)
    if price > bb_main['upper'] and rsi > rsi_short_thresh:
        short_signals.append(("BB_MAIN+RSI", f"Price > BB Main Upper & RSI > {rsi_short_thresh:.1f}"))
    
    if price > bb_strong['upper']:
        short_signals.append(("BB_STRONG", f"Price > BB Strong Upper"))
    
    if momentum_pct > momentum_thresh and rsi > rsi_short_thresh:
        short_signals.append(("MOM+RSI", f"상승 모멘텀 & RSI > {rsi_short_thresh:.1f}"))
    
    return long_signals, short_signals


def _signal_bear_low_vol(price, rsi, bb_main, bb_strong, momentum_pct,
                         rsi_long_thresh, rsi_short_thresh, momentum_thresh, regime_info):
    """Bear Trend + Low Volatility 신호 로직 (반등 매도 + Mean Reversion)"""
    long_signals = []
    short_signals = []
    
    # LONG 진입 (보수적)
    if rsi < rsi_long_thresh and price < bb_strong['lower']:
        long_signals.append(("RSI+BB", f"RSI < {rsi_long_thresh:.1f} & Price < BB Strong Lower"))
    
    # SHORT 진입 (중립)
    if rsi > rsi_short_thresh or price > bb_main['upper']:
        short_signals.append(("RSI_OR_BB", f"RSI > {rsi_short_thresh:.1f} OR Price > BB Main Upper"))
    
    if price > bb_strong['upper']:
        short_signals.append(("BB_STRONG", f"Price > BB Strong Upper"))
    
    return long_signals, short_signals


def _signal_range_high_vol(price, rsi, bb_main, bb_strong, momentum_pct,
                           rsi_long_thresh, rsi_short_thresh, momentum_thresh, regime_info):
    """Range + High Volatility 신호 로직 (경계 거래 + 빠른 익절)"""
    long_signals = []
    short_signals = []
    
    # LONG 진입 (하단 경계)
    if price < bb_main['lower'] and rsi < rsi_long_thresh:
        long_signals.append(("BB_MAIN+RSI", f"Price < BB Main Lower & RSI < {rsi_long_thresh:.1f}"))
    
    if price < bb_strong['lower']:
        long_signals.append(("BB_STRONG", f"Price < BB Strong Lower"))
    
    # SHORT 진입 (상단 경계)
    if price > bb_main['upper'] and rsi > rsi_short_thresh:
        short_signals.append(("BB_MAIN+RSI", f"Price > BB Main Upper & RSI > {rsi_short_thresh:.1f}"))
    
    if price > bb_strong['upper']:
        short_signals.append(("BB_STRONG", f"Price > BB Strong Upper"))
    
    return long_signals, short_signals


def _signal_range_low_vol(price, rsi, bb_main, bb_strong, momentum_pct,
                          rsi_long_thresh, rsi_short_thresh, momentum_thresh, regime_info):
    """Range + Low Volatility 신호 로직 (Mean Reversion, V1 로직 유사)"""
    long_signals = []
    short_signals = []
    
    # LONG 진입
    if rsi < rsi_long_thresh or price < bb_main['lower']:
        long_signals.append(("RSI_OR_BB", f"RSI < {rsi_long_thresh:.1f} OR Price < BB Main Lower"))
    
    if price < bb_strong['lower']:
        long_signals.append(("BB_STRONG", f"Price < BB Strong Lower"))
    
    if price < bb_main['lower'] and momentum_pct < -momentum_thresh:
        long_signals.append(("BB+MOM", f"Price < BB Main Lower & 하락 모멘텀"))
    
    # SHORT 진입 (대칭)
    if rsi > rsi_short_thresh or price > bb_main['upper']:
        short_signals.append(("RSI_OR_BB", f"RSI > {rsi_short_thresh:.1f} OR Price > BB Main Upper"))
    
    if price > bb_strong['upper']:
        short_signals.append(("BB_STRONG", f"Price > BB Strong Upper"))
    
    if price > bb_main['upper'] and momentum_pct > momentum_thresh:
        short_signals.append(("BB+MOM", f"Price > BB Main Upper & 상승 모멘텀"))
    
    return long_signals, short_signals


# =====================================================
# BaseStrategy 인터페이스 구현
# =====================================================

class BTC5mBaselineV2(BaseStrategy):
    """
    BTCUSDT 5m Baseline Strategy V2
    
    PHASE28-6/7: Regime-Aware + Dynamic Threshold
    V1 대비 근본적 재설계로 "생존 가능한 전략" 구현
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_name='btc5m_baseline_v2',
            strategy_type='baseline',
            version='v2.0',
            supported_symbols=['BTCUSDT'],
            supported_timeframes=['5m'],
            description='BTC 5m 베이스라인 V2 - Regime-Aware + Dynamic Threshold (PHASE28-6/7)',
        )
    
    def compute_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """신호 계산 (BaseStrategy 인터페이스 구현)"""
        return signal_logic(df, self.config)


# 하위 호환성: 기존 방식 지원
def check_signal(df: pd.DataFrame, config: dict) -> Dict[str, Any]:
    """하위 호환: signal_logic 래퍼"""
    return signal_logic(df, config)
