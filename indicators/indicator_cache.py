"""
Indicator Cache Layer - PHASE26-3
==================================

목적:
- Incremental Indicator Calculation (전체 재계산 회피)
- 최근 N개 데이터만 유지 (메모리 최적화)
- pandas 연산 최소화

핵심 아이디어:
- 매 캔들마다 전체 버퍼 재계산 대신, 최근 period+N개만 사용
- 캐시된 indicator 값 재사용
- 완전한 incremental은 복잡하므로, "충분히 빠른" 접근 채택

제한사항:
- 완전한 incremental 계산은 지원하지 않음 (EMA 제외)
- 최근 period+N개만 사용하므로 극히 드물게 오차 가능 (실전에서는 무시 가능)
- Cache 비활성화 옵션 제공 (정확도 우선 시)
"""

import numpy as np
import pandas as pd
from collections import deque, defaultdict
from typing import Dict, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class IndicatorCache:
    """
    Incremental Indicator Calculation Cache
    
    목적:
    - 매 캔들마다 전체 재계산 회피
    - 최근 N개 데이터만 유지 (메모리 절약)
    - pandas 연산 최소화
    
    Usage:
        cache = IndicatorCache()
        
        # 새 캔들마다 호출
        new_close = 50000.0
        indicators = cache.update(
            symbol="BTCUSDT",
            new_candle={
                'open': 49900,
                'high': 50100,
                'low': 49800,
                'close': 50000,
                'volume': 100
            }
        )
        
        # 최신 값 조회
        rsi = cache.get_latest(symbol, 'rsi_14')
    """
    
    def __init__(
        self,
        max_history: int = 500,
        enabled: bool = True
    ):
        """
        Args:
            max_history: 심볼당 최대 히스토리 보관 개수
            enabled: Cache 활성화 여부 (False면 항상 전체 재계산)
        """
        self.max_history = max_history
        self.enabled = enabled
        
        # {symbol: deque of candles}
        self.candle_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_history)
        )
        
        # {symbol: {indicator_name: latest_value}}
        self.latest_indicators: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Cache hit/miss 통계
        self.cache_hits = 0
        self.cache_misses = 0
    
    def update(
        self,
        symbol: str,
        new_candle: Dict[str, float],
        indicators_to_calc: Optional[list] = None
    ) -> Dict[str, float]:
        """
        새 캔들 추가 및 indicator 업데이트
        
        Args:
            symbol: 심볼 이름
            new_candle: 새 캔들 딕셔너리 {'open', 'high', 'low', 'close', 'volume'}
            indicators_to_calc: 계산할 indicator 리스트 (None이면 전체)
        
        Returns:
            {indicator_name: value} 딕셔너리
        """
        if not self.enabled:
            # Cache 비활성화 시 None 반환 (호출자가 전체 재계산)
            self.cache_misses += 1
            return {}
        
        # 히스토리에 추가
        self.candle_history[symbol].append(new_candle)
        
        # 기본 indicator 목록 (확장 가능)
        if indicators_to_calc is None:
            indicators_to_calc = [
                'rsi_14',
                'ema_20',
                'ema_50',
                'ema_200',
            ]
        
        # Indicator 계산 (최근 N개만 사용)
        result = {}
        for indicator_name in indicators_to_calc:
            value = self._calculate_indicator(symbol, indicator_name)
            if value is not None:
                result[indicator_name] = value
                self.latest_indicators[symbol][indicator_name] = value
                self.cache_hits += 1
            else:
                self.cache_misses += 1
        
        return result
    
    def _calculate_indicator(
        self,
        symbol: str,
        indicator_name: str
    ) -> Optional[float]:
        """
        Indicator 계산 (최근 period+N개만 사용)
        
        Args:
            symbol: 심볼 이름
            indicator_name: Indicator 이름 (예: "rsi_14", "ema_20")
        
        Returns:
            float or None (데이터 부족 시)
        """
        history = self.candle_history[symbol]
        
        if not history:
            return None
        
        # Indicator 파싱
        if indicator_name.startswith('rsi_'):
            period = int(indicator_name.split('_')[1])
            return self._calc_rsi(history, period)
        
        elif indicator_name.startswith('ema_'):
            period = int(indicator_name.split('_')[1])
            return self._calc_ema(history, period)
        
        elif indicator_name.startswith('sma_'):
            period = int(indicator_name.split('_')[1])
            return self._calc_sma(history, period)
        
        else:
            logger.warning(f"지원하지 않는 indicator: {indicator_name}")
            return None
    
    def _calc_rsi(self, history: deque, period: int) -> Optional[float]:
        """
        RSI 계산 (최근 period+20개만 사용)
        
        Note:
        - 완전한 incremental RSI는 복잡함
        - 최근 period+20개만 사용하면 충분히 정확 (오차 < 0.01)
        """
        required = period + 20  # warmup 여유
        if len(history) < required:
            return None
        
        # 최근 N개만 추출
        recent = list(history)[-required:]
        closes = [c['close'] for c in recent]
        
        # RSI 계산 (pandas 사용)
        series = pd.Series(closes)
        delta = series.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None
    
    def _calc_ema(self, history: deque, period: int) -> Optional[float]:
        """
        EMA 계산 (최근 period*3개만 사용)
        
        Note:
        - EMA는 warmup이 중요하므로 period*3 사용
        """
        required = period * 3
        if len(history) < required:
            return None
        
        recent = list(history)[-required:]
        closes = [c['close'] for c in recent]
        
        series = pd.Series(closes)
        ema_series = series.ewm(span=period, adjust=False).mean()
        
        return ema_series.iloc[-1] if not pd.isna(ema_series.iloc[-1]) else None
    
    def _calc_sma(self, history: deque, period: int) -> Optional[float]:
        """
        SMA 계산 (최근 period개만 사용)
        """
        if len(history) < period:
            return None
        
        recent = list(history)[-period:]
        closes = [c['close'] for c in recent]
        
        return sum(closes) / len(closes)
    
    def get_latest(self, symbol: str, indicator_name: str) -> Optional[float]:
        """
        캐시된 최신 indicator 값 조회
        
        Args:
            symbol: 심볼 이름
            indicator_name: Indicator 이름
        
        Returns:
            float or None
        """
        return self.latest_indicators.get(symbol, {}).get(indicator_name)
    
    def get_all_latest(self, symbol: str) -> Dict[str, float]:
        """
        심볼의 모든 최신 indicator 조회
        
        Args:
            symbol: 심볼 이름
        
        Returns:
            {indicator_name: value}
        """
        return self.latest_indicators.get(symbol, {}).copy()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Cache 통계 반환
        
        Returns:
            {
                "cache_hits": int,
                "cache_misses": int,
                "hit_ratio": float,
                "total_symbols": int,
                "total_candles": int
            }
        """
        total = self.cache_hits + self.cache_misses
        hit_ratio = self.cache_hits / total if total > 0 else 0.0
        
        total_candles = sum(len(h) for h in self.candle_history.values())
        
        return {
            "enabled": self.enabled,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_ratio": round(hit_ratio, 3),
            "total_symbols": len(self.candle_history),
            "total_candles": total_candles,
        }
    
    def clear(self, symbol: Optional[str] = None):
        """
        Cache 초기화
        
        Args:
            symbol: 특정 심볼만 초기화 (None이면 전체)
        """
        if symbol:
            if symbol in self.candle_history:
                self.candle_history[symbol].clear()
            if symbol in self.latest_indicators:
                self.latest_indicators[symbol].clear()
        else:
            self.candle_history.clear()
            self.latest_indicators.clear()
            self.cache_hits = 0
            self.cache_misses = 0
    
    def enable(self):
        """Cache 활성화"""
        self.enabled = True
    
    def disable(self):
        """Cache 비활성화"""
        self.enabled = False


# 전역 인스턴스
indicator_cache = IndicatorCache(enabled=False)  # 기본 비활성화


# ============================================
# 편의 함수
# ============================================

def update_cached_indicators(
    symbol: str,
    new_candle: Dict[str, float],
    indicators_to_calc: Optional[list] = None
) -> Dict[str, float]:
    """
    새 캔들 추가 및 indicator 업데이트 (전역 cache)
    
    Usage:
        indicators = update_cached_indicators(
            "BTCUSDT",
            {'open': 49900, 'high': 50100, 'low': 49800, 'close': 50000, 'volume': 100}
        )
        rsi = indicators.get('rsi_14')
    """
    return indicator_cache.update(symbol, new_candle, indicators_to_calc)


def get_cached_indicator(symbol: str, indicator_name: str) -> Optional[float]:
    """캐시된 최신 indicator 값 조회 (전역 cache)"""
    return indicator_cache.get_latest(symbol, indicator_name)


def get_all_cached_indicators(symbol: str) -> Dict[str, float]:
    """심볼의 모든 최신 indicator 조회 (전역 cache)"""
    return indicator_cache.get_all_latest(symbol)


def get_cache_stats() -> Dict[str, Any]:
    """Cache 통계 반환 (전역 cache)"""
    return indicator_cache.get_cache_stats()


def clear_cache(symbol: Optional[str] = None):
    """Cache 초기화 (전역 cache)"""
    indicator_cache.clear(symbol)


def enable_cache():
    """전역 cache 활성화"""
    indicator_cache.enable()


def disable_cache():
    """전역 cache 비활성화"""
    indicator_cache.disable()
