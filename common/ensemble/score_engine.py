#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Score Engine
============
PHASE19-2: 전략 점수 계산 엔진

**계산 로직**:
1. Factor Weighted Sum: Σ (factor_i × weight_i)
2. Regime Multiplier: optimal/worst regime에 따라 가중치 조정
3. Base Weight 적용: 전략 고유 신뢰도
4. 0~1 클리핑: 최종 점수 범위 제한
"""
from typing import Optional
from .factors import FactorDict
from common.registry.strategy_metadata import StrategyMetadata


class ScoreEngine:
    """
    전략 점수 계산 엔진
    
    **사용 예시**:
    ```python
    engine = ScoreEngine()
    score = engine.compute_strategy_score(
        metadata=strategy.metadata,
        factors={"momentum": 0.7, "volume": 0.8, ...},
        regime="trending"
    )
    ```
    """
    
    def __init__(self):
        """초기화 (현재는 stateless)"""
        pass
    
    def compute_strategy_score(
        self,
        metadata: StrategyMetadata,
        factors: FactorDict,
        regime: Optional[str] = None,
    ) -> float:
        """
        전략 점수 계산
        
        **계산식**:
        ```
        factor_score = Σ (metadata.factor_weights[name] × factors[name])
        regime_mult = 1.2 (optimal) | 0.3 (worst) | 1.0 (other)
        final_score = base_weight × regime_mult × factor_score
        final_score = clip(0, 1)
        ```
        
        Args:
            metadata: 전략 메타데이터 (factor_weights, base_weight 등 포함)
            factors: Factor 값 dict (6개)
            regime: 현재 시장 Regime (None이면 unknown)
        
        Returns:
            strategy_score: 0~1 범위 점수
        """
        # 1) Factor Weighted Sum
        factor_score = self._compute_factor_score(metadata, factors)
        
        # 2) Regime Multiplier
        regime_mult = self._compute_regime_multiplier(metadata, regime)
        
        # 3) Base Weight 적용
        final_score = metadata.base_weight * regime_mult * factor_score
        
        # 4) 0~1 클리핑
        return max(0.0, min(1.0, final_score))
    
    def _compute_factor_score(
        self,
        metadata: StrategyMetadata,
        factors: FactorDict
    ) -> float:
        """
        Factor Weighted Sum 계산
        
        Args:
            metadata: 전략 메타데이터
            factors: Factor 값 dict
        
        Returns:
            factor_score: 0~1 (가중 합산)
        """
        factor_names = [
            "momentum",
            "volatility",
            "volume",
            "trend_strength",
            "overbought_oversold",
            "breakout_probability",
        ]
        
        score = 0.0
        for name in factor_names:
            weight = metadata.factor_weights.get(name, 0.0)
            value = factors.get(name, 0.0)
            score += weight * value
        
        return score
    
    def _compute_regime_multiplier(
        self,
        metadata: StrategyMetadata,
        regime: Optional[str]
    ) -> float:
        """
        Regime에 따른 가중치 조정
        
        **규칙**:
        - optimal_regime: 1.2x
        - worst_regime: 0.3x
        - unknown/other: 1.0x
        
        Args:
            metadata: 전략 메타데이터
            regime: 현재 Regime (None이면 unknown)
        
        Returns:
            regime_multiplier: 0.3~1.2
        """
        if regime is None:
            return 1.0  # Unknown regime
        
        if regime == metadata.optimal_regime:
            return 1.2  # Optimal: 20% 증가
        
        if regime == metadata.worst_regime:
            return 0.3  # Worst: 70% 감소
        
        return 1.0  # Neutral regime
