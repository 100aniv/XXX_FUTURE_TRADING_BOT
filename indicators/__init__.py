#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Indicators 모듈
===============
기술적 지표 계산 및 시장 분석

현재 구조 (Phase 1):
  - core_indicators.py: 모든 지표 통합

향후 구조 (Phase 2, 지표 15개+ 될 때):
  - trend_indicators.py: EMA, MACD, ADX 등
  - momentum_indicators.py: RSI, Stochastic, CCI 등
  - volatility_indicators.py: ATR, BB, Keltner 등
  - volume_indicators.py: OBV, MFI 등
"""

from .core_indicators import (
    # Trend
    ema,
    macd,
    
    # Momentum
    rsi,
    
    # Volatility
    bb,
    atr,
    donchian,
    
    # Volume
    volume_ma,
    
    # 통합
    add_indicators,
    regime,
    detect_volatility_regime,  # ⭐ CRITICAL_ISSUES: 동적 SL 조정용
)

__all__ = [
    # Trend
    "ema",
    "macd",
    
    # Momentum
    "rsi",
    
    # Volatility
    "bb",
    "atr",
    "donchian",
    
    # Volume
    "volume_ma",
    
    # 통합
    "add_indicators",
    "regime",
    "detect_volatility_regime",  # ⭐ CRITICAL_ISSUES: 동적 SL 조정용
]
