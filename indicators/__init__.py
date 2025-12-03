#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Indicators 모듈
===============
기술적 지표 계산 및 시장 분석

현재 구조 (PHASE26-3 통합 완료):
  - core_indicators.py: 모든 지표 통합
  - indicator_cache.py: Incremental Indicator Calculation Cache (PHASE26-3)

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

# PHASE26-3: Indicator Cache (성능 최적화)
from .indicator_cache import (
    IndicatorCache,
    indicator_cache,
    update_cached_indicators,
    get_cached_indicator,
    get_all_cached_indicators,
    get_cache_stats,
    clear_cache,
    enable_cache,
    disable_cache,
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
    
    # PHASE26-3: Indicator Cache
    "IndicatorCache",
    "indicator_cache",
    "update_cached_indicators",
    "get_cached_indicator",
    "get_all_cached_indicators",
    "get_cache_stats",
    "clear_cache",
    "enable_cache",
    "disable_cache",
]
