"""
⚠️ DEPRECATED: common.indicators.indicator_cache
================================================

이 모듈은 **DEPRECATED**입니다.

✅ Canonical 구현 위치:
    indicators.indicator_cache

⚠️ 이 모듈은 하위 호환을 위한 thin shim입니다.
   새로운 코드는 반드시 canonical 모듈을 사용하세요:

    from indicators import (
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

통합 일자: PHASE26-3 Indicators Consolidation
향후 계획: 이 shim은 모든 import가 마이그레이션된 후 제거될 예정입니다.
"""

# ============================================
# Deprecated Shim: canonical 모듈에서 re-export
# ============================================

from indicators.indicator_cache import (
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
