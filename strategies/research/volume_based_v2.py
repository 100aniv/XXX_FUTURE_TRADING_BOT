#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Volume-Based Strategy V2 (PHASE22-1)
=====================================
5분봉 기반 거래량 기반 전략

전략 철학:
- Timeframe: 5m
- On-Balance Volume (OBV) 기반
- Volume Spike로 강한 방향성 확인
- 거래량 주도 움직임 포착

신호 조건 (LONG):
1. OBV > OBV MA (매수 압력 증가)
2. Volume > Volume MA × 2.0 (강한 매수)
3. Price > EMA(20) (가격도 상승)

신호 조건 (SHORT):
1. OBV < OBV MA (매도 압력 증가)
2. Volume > Volume MA × 2.0 (강한 매도)
3. Price < EMA(20) (가격도 하락)

위험 관리:
- SL: ATR × 1.2
- TP: RR 1.8
- 최대 보유: 45분
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


def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """
    On-Balance Volume (OBV) 계산
    
    Args:
        df: OHLCV DataFrame
    
    Returns:
        OBV 시리즈
    """
    obv = pd.Series(index=df.index, dtype=float)
    obv.iloc[0] = 0
    
    for i in range(1, len(df)):
        if df.iloc[i]['close'] > df.iloc[i-1]['close']:
            obv.iloc[i] = obv.iloc[i-1] + df.iloc[i]['volume']
        elif df.iloc[i]['close'] < df.iloc[i-1]['close']:
            obv.iloc[i] = obv.iloc[i-1] - df.iloc[i]['volume']
        else:
            obv.iloc[i] = obv.iloc[i-1]
    
    return obv


def signal_logic(df: pd.DataFrame, config: dict) -> Dict[str, Any]:
    """
    Volume-Based V2 전략: OBV + Volume Spike
    
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
    obv_ma_period = config.get('obv_ma_period', 20)
    vol_mult = config.get('vol_mult', 2.0)
    ema_period = config.get('ema_period', 20)
    rr = config.get('rr', 1.8)
    atr_mult_sl = config.get('atr_mult_sl', 1.2)
    max_hold_minutes = config.get('max_hold_minutes', 45)
    allow_short = config.get('filters', {}).get('allow_short', True)
    
    if not _PARAMS_LOGGED:
        logger.info("=" * 60)
        logger.info("[VOLUME-BASED V2 INIT] 파라미터 로드 완료")
        logger.info("=" * 60)
        logger.info(f" 신호 조건:")
        logger.info(f"  - OBV MA: {obv_ma_period}")
        logger.info(f"  - 거래량 배수: {vol_mult}x")
        logger.info(f"  - EMA: {ema_period}")
        logger.info(f" 위험 관리:")
        logger.info(f"  - RR: {rr}")
        logger.info(f"  - SL 배수: {atr_mult_sl}x ATR")
        logger.info(f"  - 최대 보유: {max_hold_minutes}분")
        logger.info(f"  - 숏 허용: {allow_short}")
        logger.info("=" * 60)
        _PARAMS_LOGGED = True
    
    # OBV 계산
    obv = calculate_obv(df)
    obv_value = float(obv.iloc[-1])
    obv_ma = float(obv.iloc[-obv_ma_period:].mean())
    
    # EMA 계산
    if len(df) >= ema_period:
        ema = float(df.iloc[-ema_period:]['close'].ewm(span=ema_period, adjust=False).mean().iloc[-1])
    else:
        ema = price
    
    # 거래량 확인
    volume = float(last["volume"])
    vol_ma = float(last["vol_ma"])
    vol_spike = volume > vol_ma * vol_mult
    
    # 신호 조건
    obv_rising = obv_value > obv_ma
    obv_falling = obv_value < obv_ma
    price_above_ema = price > ema
    price_below_ema = price < ema
    
    volume_long = obv_rising and vol_spike and price_above_ema
    volume_short = obv_falling and vol_spike and price_below_ema
    
    # 디버그 로그 (500캔들마다)
    if len(df) % 500 == 0:
        logger.info(f"🔍 [DEBUG][VOLUME] 신호 조건 체크 (캔들 #{len(df)}):")
        logger.info(f"  📊 Price: {price:.2f} | EMA: {ema:.2f}")
        logger.info(f"  📈 OBV: {obv_value:.0f} | OBV MA: {obv_ma:.0f} | Rising: {obv_rising}, Falling: {obv_falling}")
        logger.info(f"  📦 Volume: {volume:.0f} vs MA={vol_ma:.0f} | Spike: {vol_spike}")
        logger.info(f"  🎯 Price Above EMA: {price_above_ema}, Below: {price_below_ema}")
        logger.info(f"  ✅ LONG: {volume_long}, SHORT: {volume_short}")
    
    # 신호 판단
    side = None
    action = None
    reason = []
    
    if volume_long:
        side = "LONG"
        action = "진입"
        reason.append("OBV 상승 (매수 압력)")
        reason.append("Volume Spike")
        reason.append(f"Price > EMA ({ema:.2f})")
    
    elif allow_short and volume_short:
        side = "SHORT"
        action = "진입"
        reason.append("OBV 하락 (매도 압력)")
        reason.append("Volume Spike")
        reason.append(f"Price < EMA ({ema:.2f})")
    
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
        "obv": obv_value,
        "obv_ma": obv_ma,
        "ema": ema,
        "volume": volume,
        "vol_ma": vol_ma,
        "vol_spike": vol_spike,
    }


class VolumeBasedStrategy(BaseStrategy):
    """
    Volume-Based 전략 (PHASE22-1, 5m)
    
    **전략 특징**:
    - Timeframe: 5m
    - OBV + Volume Spike + EMA
    - RR: 1.8
    - 보유 시간: 중기 (45분 이내)
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_name='volume_v2',
            strategy_type='volume',
            supported_symbols=['BTCUSDT', 'ETHUSDT'],
            supported_timeframes=['5m'],
            version='v2.0',
            description='5분봉 기반 OBV + Volume Spike',
            optimal_regime='high_volume',
            worst_regime='low_volume',
            base_weight=1.0,
            factor_weights={
                'momentum': 0.2,
                'volatility': 0.1,
                'volume': 0.5,
                'trend_strength': 0.1,
                'overbought_oversold': 0.0,
                'breakout_probability': 0.1,
            }
        )
    
    def compute_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """신호 계산"""
        return signal_logic(df, self.config)
