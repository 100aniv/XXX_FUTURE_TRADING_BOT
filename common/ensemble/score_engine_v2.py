#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Score Engine V2
===============
PHASE23-3: Score V2 기반 전략 점수 계산 엔진

**기존 vs V2**:
- AS-IS (PHASE19): Factor 기반 단일 score (0~1)
- TO-BE (PHASE23-3): Score V2 필드 기반 방향성 점수 (S_LONG, S_SHORT, S_NET)

**주요 기능**:
1. Signal에서 Score V2 필드 추출 (S_LONG, S_SHORT, S_RISK, S_QUALITY)
2. 파생 필드 계산 (S_NET, S_ABS, S_DIR)
3. Regime multiplier 적용 (optional)
4. Factor-based score와의 hybrid mode 지원
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional, Literal
import logging

from .factors import FactorDict
from common.registry.strategy_metadata import StrategyMetadata

logger = logging.getLogger(__name__)


@dataclass
class ScoreComponentsV2:
    """
    Score V2 전체 컴포넌트
    
    Attributes:
        S_LONG: LONG 신호 강도 [0.0, 1.0]
        S_SHORT: SHORT 신호 강도 [0.0, 1.0]
        S_NET: 순 신호 강도 [-1.0, 1.0] = S_LONG - S_SHORT
        S_ABS: 총 신호 강도 [0.0, 2.0] = S_LONG + S_SHORT
        S_RISK: 리스크 점수 [0.0, 1.0] (높을수록 위험)
        S_QUALITY: 신호 품질 [0.0, 1.0] (높을수록 신뢰도 높음)
        S_DIR: 방향 ('LONG' | 'SHORT' | None)
    """
    S_LONG: float
    S_SHORT: float
    S_NET: float
    S_ABS: float
    S_RISK: float
    S_QUALITY: float
    S_DIR: Optional[str]
    
    def __post_init__(self):
        """유효성 검사"""
        # Clamp values
        self.S_LONG = max(0.0, min(1.0, self.S_LONG))
        self.S_SHORT = max(0.0, min(1.0, self.S_SHORT))
        self.S_RISK = max(0.0, min(1.0, self.S_RISK))
        self.S_QUALITY = max(0.0, min(1.0, self.S_QUALITY))
        
        # Recalculate derived fields
        self.S_NET = self.S_LONG - self.S_SHORT
        self.S_ABS = self.S_LONG + self.S_SHORT
        
        # Determine direction
        if self.S_NET > 0.05:
            self.S_DIR = 'LONG'
        elif self.S_NET < -0.05:
            self.S_DIR = 'SHORT'
        else:
            self.S_DIR = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict 변환 (로깅용)"""
        return {
            'S_LONG': round(self.S_LONG, 3),
            'S_SHORT': round(self.S_SHORT, 3),
            'S_NET': round(self.S_NET, 3),
            'S_ABS': round(self.S_ABS, 3),
            'S_RISK': round(self.S_RISK, 3),
            'S_QUALITY': round(self.S_QUALITY, 3),
            'S_DIR': self.S_DIR,
        }


ScoreMode = Literal['score_v2', 'factor', 'hybrid']


class ScoreEngineV2:
    """
    Score Engine V2
    
    **사용 예시**:
    ```python
    engine = ScoreEngineV2()
    score_v2 = engine.compute_strategy_score_v2(
        signal=strategy.compute_signal(df),
        metadata=strategy.metadata,
        mode='score_v2'
    )
    
    print(f"S_NET: {score_v2.S_NET}, S_DIR: {score_v2.S_DIR}")
    ```
    """
    
    def __init__(self):
        """초기화"""
        pass
    
    def compute_strategy_score_v2(
        self,
        signal: Dict[str, Any],
        metadata: StrategyMetadata,
        factors: Optional[FactorDict] = None,
        regime: Optional[str] = None,
        mode: ScoreMode = 'score_v2',
        hybrid_weight: float = 0.7,  # hybrid mode에서 score_v2의 비중
    ) -> ScoreComponentsV2:
        """
        Score V2 계산
        
        **Modes**:
        - 'score_v2': Signal의 Score V2 필드만 사용
        - 'factor': Factor 기반 기존 score 사용 (PHASE19 호환)
        - 'hybrid': Score V2 + Factor 혼합
        
        Args:
            signal: Strategy의 compute_signal() 결과
            metadata: 전략 메타데이터
            factors: (Optional) Factor dict
            regime: 현재 Regime
            mode: 계산 모드
            hybrid_weight: hybrid mode에서 score_v2의 비중 (0~1)
        
        Returns:
            ScoreComponentsV2
        """
        if mode == 'score_v2':
            return self._compute_score_v2_only(signal, metadata, regime)
        elif mode == 'factor':
            return self._compute_factor_based(signal, metadata, factors, regime)
        elif mode == 'hybrid':
            return self._compute_hybrid(
                signal, metadata, factors, regime, hybrid_weight
            )
        else:
            logger.warning(f"⚠️  Unknown score mode '{mode}', using 'score_v2'")
            return self._compute_score_v2_only(signal, metadata, regime)
    
    def _compute_score_v2_only(
        self,
        signal: Dict[str, Any],
        metadata: StrategyMetadata,
        regime: Optional[str] = None
    ) -> ScoreComponentsV2:
        """
        Score V2 필드만 사용한 계산
        
        **처리 흐름**:
        1. Signal에서 S_LONG, S_SHORT, S_RISK, S_QUALITY 추출
        2. Regime multiplier 적용 (optional)
        3. ScoreComponentsV2 생성 (derived fields 자동 계산)
        
        Args:
            signal: Strategy signal dict
            metadata: 전략 메타데이터
            regime: 현재 Regime
        
        Returns:
            ScoreComponentsV2
        """
        # 1) Extract Score V2 fields
        S_LONG = signal.get('S_LONG', 0.0)
        S_SHORT = signal.get('S_SHORT', 0.0)
        S_RISK = signal.get('S_RISK', 0.5)  # Default: neutral risk
        S_QUALITY = signal.get('S_QUALITY', 0.5)  # Default: neutral quality
        
        # 2) Apply regime multiplier (optional)
        if regime:
            regime_mult = self._compute_regime_multiplier(metadata, regime)
            S_LONG *= regime_mult
            S_SHORT *= regime_mult
        
        # 3) Create ScoreComponentsV2 (auto-calculates S_NET, S_ABS, S_DIR)
        return ScoreComponentsV2(
            S_LONG=S_LONG,
            S_SHORT=S_SHORT,
            S_NET=0.0,  # Will be recalculated in __post_init__
            S_ABS=0.0,  # Will be recalculated in __post_init__
            S_RISK=S_RISK,
            S_QUALITY=S_QUALITY,
            S_DIR=None,  # Will be determined in __post_init__
        )
    
    def _compute_factor_based(
        self,
        signal: Dict[str, Any],
        metadata: StrategyMetadata,
        factors: Optional[FactorDict],
        regime: Optional[str]
    ) -> ScoreComponentsV2:
        """
        Factor 기반 score를 Score V2 형식으로 변환
        
        **변환 로직**:
        - factor_score (0~1) 계산
        - signal['side']에 따라 S_LONG or S_SHORT에 할당
        - S_RISK, S_QUALITY는 기본값 사용
        
        Args:
            signal: Strategy signal dict
            metadata: 전략 메타데이터
            factors: Factor dict
            regime: 현재 Regime
        
        Returns:
            ScoreComponentsV2
        """
        # Factor score 계산 (기존 ScoreEngine 로직)
        if not factors:
            logger.warning("⚠️  Factor dict 없음, 중립값 사용")
            factor_score = 0.5
        else:
            factor_score = self._compute_factor_score(metadata, factors)
            regime_mult = self._compute_regime_multiplier(metadata, regime)
            factor_score = metadata.base_weight * regime_mult * factor_score
            factor_score = max(0.0, min(1.0, factor_score))
        
        # Signal side에 따라 S_LONG or S_SHORT 할당
        side = signal.get('side') or signal.get('direction')
        if side == 'LONG':
            S_LONG = factor_score
            S_SHORT = 0.0
        elif side == 'SHORT':
            S_LONG = 0.0
            S_SHORT = factor_score
        else:
            # No signal
            S_LONG = 0.0
            S_SHORT = 0.0
        
        return ScoreComponentsV2(
            S_LONG=S_LONG,
            S_SHORT=S_SHORT,
            S_NET=0.0,
            S_ABS=0.0,
            S_RISK=0.5,
            S_QUALITY=factor_score,  # Use factor_score as quality proxy
            S_DIR=None,
        )
    
    def _compute_hybrid(
        self,
        signal: Dict[str, Any],
        metadata: StrategyMetadata,
        factors: Optional[FactorDict],
        regime: Optional[str],
        hybrid_weight: float
    ) -> ScoreComponentsV2:
        """
        Score V2 + Factor 혼합
        
        **혼합 공식**:
        S_LONG_final = hybrid_weight × S_LONG_v2 + (1 - hybrid_weight) × S_LONG_factor
        S_SHORT_final = hybrid_weight × S_SHORT_v2 + (1 - hybrid_weight) × S_SHORT_factor
        
        Args:
            signal: Strategy signal dict
            metadata: 전략 메타데이터
            factors: Factor dict
            regime: 현재 Regime
            hybrid_weight: Score V2의 비중 (0~1)
        
        Returns:
            ScoreComponentsV2
        """
        # Score V2 component
        score_v2 = self._compute_score_v2_only(signal, metadata, regime)
        
        # Factor component
        score_factor = self._compute_factor_based(signal, metadata, factors, regime)
        
        # Blend
        S_LONG = hybrid_weight * score_v2.S_LONG + (1 - hybrid_weight) * score_factor.S_LONG
        S_SHORT = hybrid_weight * score_v2.S_SHORT + (1 - hybrid_weight) * score_factor.S_SHORT
        S_RISK = hybrid_weight * score_v2.S_RISK + (1 - hybrid_weight) * score_factor.S_RISK
        S_QUALITY = hybrid_weight * score_v2.S_QUALITY + (1 - hybrid_weight) * score_factor.S_QUALITY
        
        return ScoreComponentsV2(
            S_LONG=S_LONG,
            S_SHORT=S_SHORT,
            S_NET=0.0,
            S_ABS=0.0,
            S_RISK=S_RISK,
            S_QUALITY=S_QUALITY,
            S_DIR=None,
        )
    
    # =========================================================================
    # Helper Methods (기존 ScoreEngine 로직 재사용)
    # =========================================================================
    
    def _compute_factor_score(
        self,
        metadata: StrategyMetadata,
        factors: FactorDict
    ) -> float:
        """
        Factor Weighted Sum 계산 (기존 ScoreEngine 로직)
        
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
        Regime에 따른 가중치 조정 (기존 ScoreEngine 로직)
        
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


# Export
__all__ = [
    'ScoreComponentsV2',
    'ScoreEngineV2',
    'ScoreMode',
]
