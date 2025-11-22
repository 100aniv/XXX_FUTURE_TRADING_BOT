#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Volatility Breakout Strategy V2 (PHASE22-1)
============================================
15분봉 기반 변동성 돌파 전략

전략 철학:
- Timeframe: 15m
- 변동성 확대 구간에서 지지/저항 돌파 포착
- ATR 기반 동적 SR 레벨 계산
- Breakout 확인 후 진입

신호 조건 (LONG):
1. Price > Resistance Level (Recent High + ATR buffer)
2. Volume > Volume MA × 1.5
3. ATR > ATR MA (변동성 증가)

신호 조건 (SHORT):
1. Price < Support Level (Recent Low - ATR buffer)
2. Volume > Volume MA × 1.5
3. ATR > ATR MA

위험 관리:
- SL: ATR × 1.5
- TP: RR 2.0
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
    Volatility Breakout V2 전략: ATR 기반 SR 돌파
    
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
    min_bars = config.get('min_bars_for_signal', 60)
    if len(df) < min_bars:
        return {"side": None, "reason": "데이터 부족"}
    
    # 현재 캔들
    last = df.iloc[-1]
    price = float(last["close"])
    atr = float(last["atr"])
    atr_pct = atr / price
    
    # 파라미터 로드
    sr_lookback = config.get('sr_lookback', 20)
    atr_buffer_mult = config.get('atr_buffer_mult', 0.5)
    vol_mult = config.get('vol_mult', 1.5)
    atr_ma_period = config.get('atr_ma_period', 20)
    rr = config.get('rr', 2.0)
    atr_mult_sl = config.get('atr_mult_sl', 1.5)
    max_hold_minutes = config.get('max_hold_minutes', 60)
    allow_short = config.get('filters', {}).get('allow_short', True)
    
    if not _PARAMS_LOGGED:
        logger.info("=" * 60)
        logger.info("[VOLATILITY BREAKOUT V2 INIT] 파라미터 로드 완료")
        logger.info("=" * 60)
        logger.info(f" 신호 조건:")
        logger.info(f"  - SR Lookback: {sr_lookback}개 캔들")
        logger.info(f"  - ATR Buffer: {atr_buffer_mult}x ATR")
        logger.info(f"  - 거래량 배수: {vol_mult}x")
        logger.info(f"  - ATR MA: {atr_ma_period}")
        logger.info(f" 위험 관리:")
        logger.info(f"  - RR: {rr}")
        logger.info(f"  - SL 배수: {atr_mult_sl}x ATR")
        logger.info(f"  - 최대 보유: {max_hold_minutes}분")
        logger.info(f"  - 숏 허용: {allow_short}")
        logger.info("=" * 60)
        _PARAMS_LOGGED = True
    
    # SR 레벨 계산
    recent_highs = df.iloc[-sr_lookback:]['high']
    recent_lows = df.iloc[-sr_lookback:]['low']
    resistance = float(recent_highs.max()) + atr * atr_buffer_mult
    support = float(recent_lows.min()) - atr * atr_buffer_mult
    
    # ATR 확장 확인
    if len(df) >= atr_ma_period:
        atr_values = df.iloc[-atr_ma_period:]['atr']
        atr_ma = float(atr_values.mean())
        atr_expanding = atr > atr_ma
    else:
        atr_expanding = False
    
    # 거래량 확인
    volume = float(last["volume"])
    vol_ma = float(last["vol_ma"])
    vol_spike = volume > vol_ma * vol_mult
    
    # 신호 조건
    breakout_long = (price > resistance) and vol_spike and atr_expanding
    breakout_short = (price < support) and vol_spike and atr_expanding
    
    # 디버그 로그 (500캔들마다)
    if len(df) % 500 == 0:
        logger.info(f"🔍 [DEBUG][BREAKOUT] 신호 조건 체크 (캔들 #{len(df)}):")
        logger.info(f"  📊 Price: {price:.2f} | Resistance: {resistance:.2f} | Support: {support:.2f}")
        logger.info(f"  📈 ATR: {atr:.2f} | ATR MA: {atr_ma if len(df) >= atr_ma_period else 'N/A':.2f} | Expanding: {atr_expanding}")
        logger.info(f"  📦 Volume: {volume:.0f} vs MA={vol_ma:.0f} | Spike: {vol_spike}")
        logger.info(f"  ✅ LONG: {breakout_long}, SHORT: {breakout_short}")
    
    # 신호 판단
    side = None
    action = None
    reason = []
    
    if breakout_long:
        side = "LONG"
        action = "진입"
        reason.append(f"Resistance 돌파 ({resistance:.2f})")
        if vol_spike:
            reason.append("거래량 급증")
        if atr_expanding:
            reason.append("변동성 확대")
    
    elif allow_short and breakout_short:
        side = "SHORT"
        action = "진입"
        reason.append(f"Support 하향 돌파 ({support:.2f})")
        if vol_spike:
            reason.append("거래량 급증")
        if atr_expanding:
            reason.append("변동성 확대")
    
    # 가격 레벨 계산
    entry, sl, tp = (None, None, None)
    if side:
        entry, sl, tp = price_levels(side, price, atr, rr, atr_mult_sl)
    
    # 레버리지 계산
    lev = leverage_suggestion(
        atr_pct,
        config['leverage']['min'],
        config['leverage']['max']
    )
    
    return {
        "side": side,
        "action": action,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "lev": lev,
        "ts": int(last["time"].timestamp()) if hasattr(last["time"], 'timestamp') else int(last["time"]),
        "reason": reason,
        "price": price,
        "atr": atr,
        "atr_pct": atr_pct,
        "resistance": resistance,
        "support": support,
        "volume": volume,
        "vol_ma": vol_ma,
        "vol_spike": vol_spike,
        "atr_expanding": atr_expanding,
    }


class VolatilityBreakoutStrategy(BaseStrategy):
    """
    Volatility Breakout 전략 (PHASE22-1, 15m)
    
    **전략 특징**:
    - Timeframe: 15m
    - ATR 기반 SR 레벨 + Breakout 확인
    - RR: 2.0
    - 보유 시간: 중기 (60분 이내)
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_name='breakout_v2',
            strategy_type='breakout',
            supported_symbols=['BTCUSDT', 'ETHUSDT'],
            supported_timeframes=['15m'],
            version='v2.0',
            description='15분봉 기반 ATR Breakout + Volume Confirmation',
            optimal_regime='trending',
            worst_regime='low_volatility',
            base_weight=1.0,
            factor_weights={
                'momentum': 0.2,
                'volatility': 0.4,
                'volume': 0.2,
                'trend_strength': 0.1,
                'overbought_oversold': 0.0,
                'breakout_probability': 0.1,
            }
        )
    
    def compute_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """신호 계산"""
        return signal_logic(df, self.config)
