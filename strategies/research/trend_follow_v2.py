#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trend Following Strategy V2 (PHASE22-1)
========================================
1시간봉 기반 추세 추종 전략

전략 철학:
- Timeframe: 1h
- 이중 이동평균 (SMA 50/200) + MACD
- 장기 추세 확인 후 진입
- 추세 내 위치 확인

신호 조건 (LONG):
1. SMA50 > SMA200 (Golden Cross)
2. Price > SMA50
3. MACD > Signal Line
4. MACD Histogram > 0

신호 조건 (SHORT):
1. SMA50 < SMA200 (Death Cross)
2. Price < SMA50
3. MACD < Signal Line
4. MACD Histogram < 0

위험 관리:
- SL: SMA50 ± ATR × 1.0
- TP: RR 2.5
- 최대 보유: 240분 (4시간)
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
    Trend Following V2 전략: SMA + MACD
    
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
    
    # 데이터 충분성 검사 (SMA200 필요)
    min_bars = config.get('min_bars_for_signal', 210)
    if len(df) < min_bars:
        return {"side": None, "reason": "데이터 부족"}
    
    # 현재 캔들
    last = df.iloc[-1]
    price = float(last["close"])
    atr = float(last["atr"])
    atr_pct = atr / price
    
    # 파라미터 로드
    sma_fast = config.get('sma_fast', 50)
    sma_slow = config.get('sma_slow', 200)
    rr = config.get('rr', 2.5)
    atr_mult_sl = config.get('atr_mult_sl', 1.0)
    max_hold_minutes = config.get('max_hold_minutes', 240)
    allow_short = config.get('filters', {}).get('allow_short', True)
    
    if not _PARAMS_LOGGED:
        logger.info("=" * 60)
        logger.info("[TREND FOLLOWING V2 INIT] 파라미터 로드 완료")
        logger.info("=" * 60)
        logger.info(f" 신호 조건:")
        logger.info(f"  - SMA Fast: {sma_fast}")
        logger.info(f"  - SMA Slow: {sma_slow}")
        logger.info(f" 위험 관리:")
        logger.info(f"  - RR: {rr}")
        logger.info(f"  - SL 배수: {atr_mult_sl}x ATR")
        logger.info(f"  - 최대 보유: {max_hold_minutes}분")
        logger.info(f"  - 숏 허용: {allow_short}")
        logger.info("=" * 60)
        _PARAMS_LOGGED = True
    
    # SMA 계산
    if len(df) >= sma_slow:
        sma50 = float(df.iloc[-sma_fast:]['close'].mean())
        sma200 = float(df.iloc[-sma_slow:]['close'].mean())
    else:
        return {"side": None, "reason": "SMA 계산 불가 (데이터 부족)"}
    
    # MACD (indicators에서 이미 계산됨)
    macd = float(last.get('macd', 0))
    macd_signal = float(last.get('macd_signal', 0))
    macd_hist = float(last.get('macd_hist', 0))
    
    # 신호 조건
    golden_cross = sma50 > sma200
    death_cross = sma50 < sma200
    price_above_sma50 = price > sma50
    price_below_sma50 = price < sma50
    macd_bullish = (macd > macd_signal) and (macd_hist > 0)
    macd_bearish = (macd < macd_signal) and (macd_hist < 0)
    
    trend_long = golden_cross and price_above_sma50 and macd_bullish
    trend_short = death_cross and price_below_sma50 and macd_bearish
    
    # 디버그 로그 (500캔들마다)
    if len(df) % 500 == 0:
        logger.info(f"🔍 [DEBUG][TREND] 신호 조건 체크 (캔들 #{len(df)}):")
        logger.info(f"  📊 Price: {price:.2f} | SMA50: {sma50:.2f} | SMA200: {sma200:.2f}")
        logger.info(f"  📈 Golden Cross: {golden_cross}, Death Cross: {death_cross}")
        logger.info(f"  📉 MACD: {macd:.2f} | Signal: {macd_signal:.2f} | Hist: {macd_hist:.2f}")
        logger.info(f"  🎯 Price Above SMA50: {price_above_sma50}, Below: {price_below_sma50}")
        logger.info(f"  ✅ LONG: {trend_long}, SHORT: {trend_short}")
    
    # 신호 판단
    side = None
    action = None
    reason = []
    
    if trend_long:
        side = "LONG"
        action = "진입"
        reason.append("Golden Cross (SMA50 > SMA200)")
        reason.append(f"Price > SMA50 ({sma50:.2f})")
        reason.append("MACD Bullish")
    
    elif allow_short and trend_short:
        side = "SHORT"
        action = "진입"
        reason.append("Death Cross (SMA50 < SMA200)")
        reason.append(f"Price < SMA50 ({sma50:.2f})")
        reason.append("MACD Bearish")
    
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
        "sma50": sma50,
        "sma200": sma200,
        "macd": macd,
        "macd_signal": macd_signal,
        "macd_hist": macd_hist,
        "golden_cross": golden_cross,
        "death_cross": death_cross,
    }


class TrendFollowingStrategy(BaseStrategy):
    """
    Trend Following 전략 (PHASE22-1, 1h)
    
    **전략 특징**:
    - Timeframe: 1h
    - SMA 50/200 + MACD
    - RR: 2.5
    - 보유 시간: 장기 (4시간 이내)
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_name='trend_v2',
            strategy_type='trend',
            supported_symbols=['BTCUSDT', 'ETHUSDT'],
            supported_timeframes=['1h'],
            version='v2.0',
            description='1시간봉 기반 SMA 50/200 + MACD Trend Following',
            optimal_regime='trending',
            worst_regime='ranging',
            base_weight=1.0,
            factor_weights={
                'momentum': 0.1,
                'volatility': 0.1,
                'volume': 0.1,
                'trend_strength': 0.6,
                'overbought_oversold': 0.1,
                'breakout_probability': 0.0,
            }
        )
    
    def compute_signal(self, df: pd.DataFrame, config: dict = None) -> Dict[str, Any]:
        """
        신호 계산 (PHASE23-2: Ensemble Score V2 필드 추가)
        
        Args:
            df: OHLCV + 지표 DataFrame
            config: Override config (기본은 self.config)
        
        Returns:
            dict: 신호 정보 + Ensemble Score V2 필드
        """
        cfg = config if config is not None else self.config
        signal = signal_logic(df, cfg)
        
        # PHASE23-2: Ensemble Score V2 필드 추가
        side = signal.get('side')
        macd_hist = signal.get('macd_hist', 0)
        
        if side == 'LONG':
            # MACD histogram 강도 기반
            signal['S_LONG'] = min(1.0, 0.5 + abs(macd_hist) * 0.1)
            signal['S_SHORT'] = 0.0
        elif side == 'SHORT':
            signal['S_LONG'] = 0.0
            signal['S_SHORT'] = min(1.0, 0.5 + abs(macd_hist) * 0.1)
        else:
            signal['S_LONG'] = 0.0
            signal['S_SHORT'] = 0.0
        
        # S_RISK: ATR% 기반 (장기 포지션이므로 위험 높음)
        atr_pct = signal.get('atr_pct', 0.01)
        signal['S_RISK'] = min(1.0, atr_pct * 45)
        
        # S_QUALITY: SMA 강한 정렬 + MACD 강한 확인
        quality = 0.0
        if signal.get('golden_cross'): quality += 0.4
        if signal.get('death_cross'): quality += 0.4
        if abs(macd_hist) > 5: quality += 0.3
        if side: quality += 0.2
        signal['S_QUALITY'] = min(1.0, quality)
        
        return signal
