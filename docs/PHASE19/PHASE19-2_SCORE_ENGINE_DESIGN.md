# PHASE19-2: Score Engine Design
**작성일**: 2025-11-19  
**목적**: Factor Calculator & Score Engine 프로토타입 설계

---

## 1. 개요

Ensemble Score System의 1차 구현으로, 다음을 제공:
- **Factor Calculator**: 시장 상황을 6개 수치로 계량화
- **StrategyMetadata 확장**: 전략별 특성 및 가중치 저장
- **Score Engine**: Factor + Metadata → Strategy Score 계산

---

## 2. Factor Calculator 설계

### 2.1 모듈 구조
```
common/ensemble/
├── __init__.py
├── factors.py          # Factor 계산 로직
└── score_engine.py     # Score 계산 엔진
```

### 2.2 Factor 정의 (6개)

| Factor | 정의 | 계산 방법 | 정규화 |
|--------|------|----------|--------|
| **momentum** | 가격 모멘텀 강도 | `(close - close[20]) / ATR` | sigmoid 또는 clip |
| **volatility** | 변동성 수준 | `ATR percentile(20)` | 0~1 |
| **volume** | 거래량 급증도 | `(volume / vol_ma) - 1` | clip to 0~1 |
| **trend_strength** | 추세 강도 | `(ema_fast - ema_slow) / ATR` | sigmoid 또는 clip |
| **overbought_oversold** | RSI 극단 정도 | `abs(RSI - 50) / 50` | 0~1 |
| **breakout_probability** | 돌파 확률 | `(close - dc_mid) / (dc_upper - dc_lower)` | clip to 0~1 |

### 2.3 구현 API

```python
# common/ensemble/factors.py

from typing import Dict
import pandas as pd
import numpy as np

FactorDict = Dict[str, float]

def compute_momentum_factor(df: pd.DataFrame, lookback: int = 20) -> float:
    """가격 모멘텀 (0~1)"""
    pass

def compute_volatility_factor(df: pd.DataFrame, window: int = 20) -> float:
    """변동성 percentile (0~1)"""
    pass

def compute_volume_factor(df: pd.DataFrame, ma_window: int = 20) -> float:
    """거래량 급증도 (0~1)"""
    pass

def compute_trend_strength_factor(
    df: pd.DataFrame,
    fast_col: str = "ema_fast",
    slow_col: str = "ema_slow"
) -> float:
    """추세 강도 (0~1)"""
    pass

def compute_overbought_oversold_factor(
    df: pd.DataFrame,
    rsi_col: str = "rsi"
) -> float:
    """RSI 극단 정도 (0~1)"""
    pass

def compute_breakout_probability_factor(
    df: pd.DataFrame,
    dc_upper_col: str = "dc_upper",
    dc_lower_col: str = "dc_lower"
) -> float:
    """돌파 확률 (0~1)"""
    pass

def compute_all_factors(df: pd.DataFrame) -> FactorDict:
    """모든 Factor 계산 (마지막 row 기준)"""
    return {
        "momentum": compute_momentum_factor(df),
        "volatility": compute_volatility_factor(df),
        "volume": compute_volume_factor(df),
        "trend_strength": compute_trend_strength_factor(df),
        "overbought_oversold": compute_overbought_oversold_factor(df),
        "breakout_probability": compute_breakout_probability_factor(df),
    }
```

---

## 3. StrategyMetadata 확장

### 3.1 추가 필드

```python
from typing import Dict, Optional
from dataclasses import dataclass, field

@dataclass
class StrategyMetadata:
    # 기존 필드...
    strategy_name: str
    strategy_type: str
    supported_symbols: List[str] = field(default_factory=list)
    supported_timeframes: List[str] = field(default_factory=list)
    version: str = 'v1.0'
    description: str = ''
    
    # ✨ PHASE19-2: Ensemble 관련 필드
    optimal_regime: Optional[str] = None      # "trending", "breakout", "ranging"
    worst_regime: Optional[str] = None
    base_weight: float = 1.0
    factor_weights: Dict[str, float] = field(default_factory=dict)
```

### 3.2 전략별 초기값

**출처**: `docs/PHASE19/PHASE19-2_ENSEMBLE_ANALYSIS.md`, `STRATEGY_PROFILES.md`

| 전략 | optimal_regime | worst_regime | base_weight | factor_weights |
|------|----------------|--------------|-------------|----------------|
| **scalping** | trending | ranging | 1.0 | momentum=0.4, trend_strength=0.3, volume=0.2, volatility=0.1 |
| **breakout** | breakout | ranging | 0.8 | breakout_prob=0.5, volatility=0.2, volume=0.2, trend_strength=0.1 |
| **reversion** | ranging | trending | 0.6 | overbought_oversold=0.5, trend_strength=0.3, volatility=0.1, volume=0.1 |
| **trend** | trending | ranging | 1.2 | trend_strength=0.5, momentum=0.1, volatility=0.1, volume=0.0 |
| **swing** | trending | ranging | 1.0 | trend_strength=0.4, momentum=0.1, breakout_prob=0.2, volatility=0.1, volume=0.0 |
| **swing_bb** | ranging | trending | 0.4 | overbought_oversold=0.3, trend_strength=0.0, volatility=0.1, volume=0.1, momentum=0.0 |
| **daytrade** | trending | ranging | 0.9 | trend_strength=0.4, momentum=0.1, breakout_prob=0.2, volatility=0.1 |

---

## 4. Score Engine 설계

### 4.1 계산 로직

```python
# common/ensemble/score_engine.py

class ScoreEngine:
    def compute_strategy_score(
        self,
        metadata: StrategyMetadata,
        factors: FactorDict,
        regime: Optional[str] = None,
    ) -> float:
        """
        전략 점수 계산
        
        Args:
            metadata: 전략 메타데이터
            factors: Factor 값 dict (6개)
            regime: 현재 Regime (None이면 unknown)
        
        Returns:
            strategy_score: 0~1 범위 점수
        """
        # 1) Factor Weighted Sum
        factor_score = sum(
            metadata.factor_weights.get(name, 0.0) * factors.get(name, 0.0)
            for name in ["momentum", "volatility", "volume",
                         "trend_strength", "overbought_oversold",
                         "breakout_probability"]
        )
        
        # 2) Regime Multiplier
        regime_mult = self._compute_regime_multiplier(metadata, regime)
        
        # 3) Base Weight 적용
        final_score = metadata.base_weight * regime_mult * factor_score
        
        # 4) 0~1 클리핑
        return max(0.0, min(1.0, final_score))
    
    def _compute_regime_multiplier(
        self,
        metadata: StrategyMetadata,
        regime: Optional[str]
    ) -> float:
        """Regime에 따른 가중치"""
        if regime is None:
            return 1.0
        if regime == metadata.optimal_regime:
            return 1.2
        if regime == metadata.worst_regime:
            return 0.3
        return 1.0
```

### 4.2 확장 가능성

**PHASE19-3 이후 추가 예정**:
- Performance Feedback (Win Rate, PF 기반 동적 조정)
- Multi-Strategy Aggregation (여러 전략 점수 통합)
- Confidence Threshold (최소 점수 필터)

---

## 5. 구현 계획

### 5.1 파일 생성

1. `common/ensemble/__init__.py` (새 폴더)
2. `common/ensemble/factors.py` (Factor 계산)
3. `common/ensemble/score_engine.py` (Score 계산)

### 5.2 파일 수정

1. `common/registry/strategy_metadata.py` (필드 추가)
2. `strategies/scalping.py` (metadata 확장)
3. `strategies/breakout.py` (metadata 확장)
4. `strategies/reversion.py` (metadata 확장)
5. `strategies/trend.py` (metadata 확장)
6. `strategies/swing.py` (metadata 확장)
7. `strategies/swing_bb.py` (metadata 확장)
8. `strategies/daytrade.py` (metadata 확장)

### 5.3 테스트

**파일**: `tests/test_phase19_2_score_engine.py`

**항목**:
1. Factor 계산 정확도 (0~1 범위)
2. StrategyMetadata 확장 필드 검증
3. ScoreEngine.compute_strategy_score() 계산 로직
4. Regime Multiplier 적용 확인
5. 실제 전략 metadata로 통합 테스트

---

## 6. Acceptance Criteria

- [x] `common/ensemble/factors.py` 6개 Factor 함수 구현
- [x] `StrategyMetadata` 4개 필드 추가
- [x] 7개 전략 metadata에 초기값 세팅
- [x] `common/ensemble/score_engine.py` ScoreEngine 구현
- [x] pytest 100% PASS
- [x] 짧은 REAL PAPER 에러 없이 실행
- [x] 설계 문서 + 완료 리포트 작성
- [x] Git commit

---

## 7. TO-DO (다음 단계)

**PHASE19-3**: Signal Aggregation
- 여러 전략 점수 통합
- Voting / Weighted Sum / Tiered Approach
- Ensemble 진입 결정 로직

**PHASE19-4**: Regime Detection
- ATR/BB/EMA 기반 Regime 분류기
- Regime History 추적
- 전략 활성화/비활성화 자동화

---

**END OF DESIGN DOC**
