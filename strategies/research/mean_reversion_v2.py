#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mean Reversion Strategy V2 (PHASE22-1)
=======================================
5분봉 기반 평균 회귀 전략

전략 철학:
- Timeframe: 5m
- Bollinger Bands + RSI 극단값
- 과도한 가격 이탈 후 평균 회귀 포착
- 빠른 진입/청산

신호 조건 (LONG):
1. Price <= BB Lower × 1.01
2. RSI < 25 (극단 과매도)
3. Price Above Recent Low (Optional)

신호 조건 (SHORT):
1. Price >= BB Upper × 0.99
2. RSI > 75 (극단 과매수)
3. Price Below Recent High (Optional)

위험 관리:
- SL: ATR × 1.0
- TP: RR 1.5 또는 BB Middle
- 최대 보유: 30분
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
    Mean Reversion V2 전략: BB + RSI 극단값
    
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
    rsi_oversold = config.get('rsi_oversold', 25)
    rsi_overbought = config.get('rsi_overbought', 75)
    bb_touch_buffer = config.get('bb_touch_buffer', 0.01)  # 1% 버퍼
    rr = config.get('rr', 1.5)
    atr_mult_sl = config.get('atr_mult_sl', 1.0)
    max_hold_minutes = config.get('max_hold_minutes', 30)
    allow_short = config.get('filters', {}).get('allow_short', True)
    
    if not _PARAMS_LOGGED:
        logger.info("=" * 60)
        logger.info("[MEAN REVERSION V2 INIT] 파라미터 로드 완료")
        logger.info("=" * 60)
        logger.info(f" 신호 조건:")
        logger.info(f"  - RSI 과매도: < {rsi_oversold}")
        logger.info(f"  - RSI 과매수: > {rsi_overbought}")
        logger.info(f"  - BB Touch Buffer: {bb_touch_buffer * 100:.1f}%")
        logger.info(f" 위험 관리:")
        logger.info(f"  - RR: {rr}")
        logger.info(f"  - SL 배수: {atr_mult_sl}x ATR")
        logger.info(f"  - 최대 보유: {max_hold_minutes}분")
        logger.info(f"  - 숏 허용: {allow_short}")
        logger.info("=" * 60)
        _PARAMS_LOGGED = True
    
    # BB 밴드 (indicators에서 이미 계산됨)
    bb_upper = float(last.get('bb_upper', price * 1.02))
    bb_lower = float(last.get('bb_lower', price * 0.98))
    bb_middle = float(last.get('bb_middle', price))
    
    # RSI
    rsi = float(last["rsi"])
    
    # 신호 조건
    bb_lower_touch = price <= bb_lower * (1 + bb_touch_buffer)
    bb_upper_touch = price >= bb_upper * (1 - bb_touch_buffer)
    rsi_oversold_signal = rsi < rsi_oversold
    rsi_overbought_signal = rsi > rsi_overbought
    
    reversion_long = bb_lower_touch and rsi_oversold_signal
    reversion_short = bb_upper_touch and rsi_overbought_signal
    
    # 디버그 로그 (500캔들마다)
    if len(df) % 500 == 0:
        logger.info(f"🔍 [DEBUG][REVERSION] 신호 조건 체크 (캔들 #{len(df)}):")
        logger.info(f"  📊 Price: {price:.2f} | BB: [{bb_lower:.2f}, {bb_middle:.2f}, {bb_upper:.2f}]")
        logger.info(f"  📉 RSI: {rsi:.1f} | Oversold: {rsi_oversold_signal}, Overbought: {rsi_overbought_signal}")
        logger.info(f"  🎯 BB Touch: Lower={bb_lower_touch}, Upper={bb_upper_touch}")
        logger.info(f"  ✅ LONG: {reversion_long}, SHORT: {reversion_short}")
    
    # 신호 판단
    side = None
    action = None
    reason = []
    
    if reversion_long:
        side = "LONG"
        action = "진입"
        reason.append(f"BB Lower 터치 ({bb_lower:.2f})")
        reason.append(f"RSI 과매도 ({rsi:.1f})")
    
    elif allow_short and reversion_short:
        side = "SHORT"
        action = "진입"
        reason.append(f"BB Upper 터치 ({bb_upper:.2f})")
        reason.append(f"RSI 과매수 ({rsi:.1f})")
    
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
        "rsi": rsi,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "bb_middle": bb_middle,
    }


class MeanReversionStrategy(BaseStrategy):
    """
    Mean Reversion 전략 (PHASE22-1, 5m)
    
    **전략 특징**:
    - Timeframe: 5m
    - BB + RSI 극단값
    - RR: 1.5
    - 보유 시간: 짧음 (30분 이내)
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_name='reversion_v2',
            strategy_type='reversion',
            supported_symbols=['BTCUSDT', 'ETHUSDT'],
            supported_timeframes=['5m'],
            version='v2.0',
            description='5분봉 기반 BB + RSI Mean Reversion',
            optimal_regime='ranging',
            worst_regime='trending',
            base_weight=1.0,
            factor_weights={
                'momentum': 0.1,
                'volatility': 0.2,
                'volume': 0.1,
                'trend_strength': 0.0,
                'overbought_oversold': 0.5,
                'breakout_probability': 0.1,
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
        rsi = signal.get('rsi', 50)
        
        if side == 'LONG':
            # RSI가 낮을수록 강한 LONG 신호
            signal['S_LONG'] = min(1.0, 0.5 + (50 - rsi) / 50)
            signal['S_SHORT'] = 0.0
        elif side == 'SHORT':
            # RSI가 높을수록 강한 SHORT 신호
            signal['S_LONG'] = 0.0
            signal['S_SHORT'] = min(1.0, 0.5 + (rsi - 50) / 50)
        else:
            signal['S_LONG'] = 0.0
            signal['S_SHORT'] = 0.0
        
        # S_RISK: ATR% + mean reversion 위험 (반대 방향 추세 리스크)
        atr_pct = signal.get('atr_pct', 0.01)
        signal['S_RISK'] = min(1.0, atr_pct * 60)  # 평균 회귀는 위험 높음
        
        # S_QUALITY: RSI 극단값일수록 품질 높음
        if side == 'LONG':
            signal['S_QUALITY'] = min(1.0, (50 - rsi) / 25)  # RSI 25일 때 1.0
        elif side == 'SHORT':
            signal['S_QUALITY'] = min(1.0, (rsi - 50) / 25)  # RSI 75일 때 1.0
        else:
            signal['S_QUALITY'] = 0.0
        
        return signal
