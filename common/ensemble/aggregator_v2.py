#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ensemble Aggregator V2
======================
PHASE23-3: Score V2 기반 앙상블 의사결정 엔진

**기존 vs V2**:
- AS-IS (PHASE19): Factor 기반 단일 score → 3-Tier
- TO-BE (PHASE23-3): Score V2 (S_LONG, S_SHORT, S_NET) → 3-Tier + Diversity Constraints

**주요 기능**:
1. Score V2 기반 3-Tier 의사결정 (High-Confidence / Consensus / Skip)
2. 지배 전략 방지 (max_strategy_weight cap)
3. Risk/Quality 필터링
4. 가중 평균 기반 앙상블 집계
"""
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict, Tuple
import logging

from .score_engine_v2 import ScoreEngineV2, ScoreComponentsV2
from common.registry.strategy_metadata import StrategyMetadata

logger = logging.getLogger(__name__)


@dataclass
class StrategyDecisionV2:
    """
    개별 전략의 Score V2 기반 의사결정
    
    Attributes:
        name: 전략 이름
        score_v2: Score V2 컴포넌트 (S_LONG, S_SHORT, S_NET, etc.)
        raw_signal: 전략의 compute_signal() 결과 (entry, sl, tp 등 포함)
        metadata: 전략 메타데이터
        weight: 전략 가중치 (config에서 설정, 기본값 1.0)
    """
    name: str
    score_v2: ScoreComponentsV2
    raw_signal: Dict[str, Any]
    metadata: StrategyMetadata
    weight: float = 1.0


@dataclass
class EnsembleDecisionV2:
    """
    Ensemble 최종 의사결정 V2
    
    Attributes:
        side: 'LONG' | 'SHORT' | None
        action: '진입' | 'EXIT' | 'HOLD'
        entry: 진입 가격
        sl: Stop Loss
        tp: Take Profit
        reason: 결정 이유 (리스트)
        
        # Ensemble Meta
        strategy_votes: {strategy_name: net_score} (참여 전략별 점수)
        dominant_strategies: max_strategy_weight 초과한 전략 목록
        tier: 'tier1' | 'tier2' | 'skip'
        confidence: 최종 신뢰도 (0~1)
        
        # Aggregated Scores
        agg_S_LONG: 가중 평균 S_LONG
        agg_S_SHORT: 가중 평균 S_SHORT
        agg_S_NET: 가중 평균 S_NET
        agg_S_RISK: 가중 평균 S_RISK
        agg_S_QUALITY: 가중 평균 S_QUALITY
        
        # Original
        decisions: 모든 전략 결정 (디버깅용)
        regime: 현재 Regime
    """
    side: Optional[str]
    action: str
    entry: Optional[float]
    sl: Optional[float]
    tp: Optional[float]
    reason: List[str]
    
    strategy_votes: Dict[str, float] = field(default_factory=dict)
    dominant_strategies: List[str] = field(default_factory=list)
    tier: str = 'skip'
    confidence: float = 0.0
    
    agg_S_LONG: float = 0.0
    agg_S_SHORT: float = 0.0
    agg_S_NET: float = 0.0
    agg_S_RISK: float = 0.5
    agg_S_QUALITY: float = 0.5
    
    decisions: List[StrategyDecisionV2] = field(default_factory=list)
    regime: Optional[str] = None


class EnsembleAggregatorV2:
    """
    Ensemble Aggregator V2
    
    **역할**:
    - Score V2 기반 여러 전략의 신호를 통합
    - 3-Tier 규칙으로 최종 Ensemble 의사결정 생성
    - 지배 전략 방지 (diversity constraint)
    
    **사용 예시**:
    ```python
    aggregator = EnsembleAggregatorV2(score_engine_v2, config)
    decision = aggregator.aggregate_v2(decisions_v2, regime='trending')
    
    if decision.side:
        logger.info(f"✅ Ensemble: {decision.side} (tier={decision.tier})")
    else:
        logger.info(f"⏸️  Ensemble: Skip ({decision.reason})")
    ```
    """
    
    def __init__(
        self,
        score_engine: ScoreEngineV2,
        config: Dict[str, Any]
    ):
        """
        초기화
        
        Args:
            score_engine: ScoreEngineV2 인스턴스
            config: Ensemble config dict
        """
        self.score_engine = score_engine
        self.config = config
        
        # Extract ensemble params
        ensemble_cfg = config.get('ensemble', {})
        self.high_conf_threshold = ensemble_cfg.get('high_conf_threshold', 0.7)
        self.consensus_threshold = ensemble_cfg.get('consensus_threshold', 0.4)
        self.min_strategies = ensemble_cfg.get('min_strategies', 2)
        self.max_strategy_weight = ensemble_cfg.get('max_strategy_weight', 0.6)
        self.max_risk = ensemble_cfg.get('max_risk', 0.8)
        self.min_quality = ensemble_cfg.get('min_quality', 0.3)
        
        logger.info(
            f"🔧 [ENSEMBLE V2] Config: "
            f"high_conf={self.high_conf_threshold}, "
            f"consensus={self.consensus_threshold}, "
            f"min_strat={self.min_strategies}, "
            f"max_weight={self.max_strategy_weight}"
        )
    
    def aggregate_v2(
        self,
        decisions_v2: List[StrategyDecisionV2],
        regime: Optional[str] = None
    ) -> EnsembleDecisionV2:
        """
        Score V2 기반 3-Tier 통합
        
        **3-Tier Logic**:
        1. Tier 1 (High-Confidence): abs(S_NET) >= high_conf_threshold
        2. Tier 2 (Consensus): weighted avg >= consensus_threshold, >=min_strategies agree
        3. Tier 3 (Skip): 조건 미달
        
        **Diversity Constraint**:
        - 한 전략의 기여도가 max_strategy_weight 초과 시 Skip
        
        Args:
            decisions_v2: List[StrategyDecisionV2]
            regime: 현재 Regime
        
        Returns:
            EnsembleDecisionV2
        """
        if not decisions_v2:
            return self._create_skip_decision(
                reason='no_signals',
                decisions=decisions_v2,
                regime=regime
            )
        
        # Aggregate scores
        agg_scores = self._aggregate_scores(decisions_v2)
        
        # Risk/Quality filter
        if agg_scores['agg_S_RISK'] > self.max_risk:
            return self._create_skip_decision(
                reason=f'high_risk (S_RISK={agg_scores["agg_S_RISK"]:.3f} > {self.max_risk})',
                decisions=decisions_v2,
                regime=regime,
                agg_scores=agg_scores
            )
        
        if agg_scores['agg_S_QUALITY'] < self.min_quality:
            return self._create_skip_decision(
                reason=f'low_quality (S_QUALITY={agg_scores["agg_S_QUALITY"]:.3f} < {self.min_quality})',
                decisions=decisions_v2,
                regime=regime,
                agg_scores=agg_scores
            )
        
        # Tier 1: High-Confidence
        tier1_result = self._try_tier1(decisions_v2, agg_scores, regime)
        if tier1_result:
            return tier1_result
        
        # Tier 2: Consensus
        tier2_result = self._try_tier2(decisions_v2, agg_scores, regime)
        if tier2_result:
            return tier2_result
        
        # Tier 3: Skip
        return self._create_skip_decision(
            reason='tier1/tier2_conditions_not_met',
            decisions=decisions_v2,
            regime=regime,
            agg_scores=agg_scores
        )
    
    # =========================================================================
    # Private Methods: Tier Logic
    # =========================================================================
    
    def _try_tier1(
        self,
        decisions_v2: List[StrategyDecisionV2],
        agg_scores: Dict[str, float],
        regime: Optional[str]
    ) -> Optional[EnsembleDecisionV2]:
        """
        Tier 1: High-Confidence 시도
        
        **조건**:
        - 어떤 전략이든 abs(S_NET) >= high_conf_threshold
        - 지배 전략 방지 (max_strategy_weight)
        
        Returns:
            EnsembleDecisionV2 또는 None (조건 미달 시)
        """
        # Find high-confidence decisions
        high_conf_decisions = [
            d for d in decisions_v2
            if abs(d.score_v2.S_NET) >= self.high_conf_threshold
        ]
        
        if not high_conf_decisions:
            return None
        
        # Select best (highest abs(S_NET))
        best = max(high_conf_decisions, key=lambda x: abs(x.score_v2.S_NET))
        
        # Check dominance
        is_valid, dominant_list = self._check_dominance(decisions_v2)
        if not is_valid:
            logger.warning(
                f"⚠️  [ENSEMBLE V2] Tier1: Dominance violation - {dominant_list}"
            )
            return self._create_skip_decision(
                reason=f'tier1_dominance_violation (dominant={dominant_list})',
                decisions=decisions_v2,
                regime=regime,
                agg_scores=agg_scores,
                dominant_strategies=dominant_list
            )
        
        # Success: Tier 1
        side = best.score_v2.S_DIR
        entry = best.raw_signal.get('entry')
        sl = best.raw_signal.get('sl')
        tp = best.raw_signal.get('tp')
        
        return EnsembleDecisionV2(
            side=side,
            action='진입' if side else 'HOLD',
            entry=entry,
            sl=sl,
            tp=tp,
            reason=[
                f"tier1_high_confidence",
                f"chosen_strategy={best.name}",
                f"S_NET={best.score_v2.S_NET:.3f}"
            ],
            strategy_votes={d.name: d.score_v2.S_NET for d in decisions_v2},
            dominant_strategies=[],
            tier='tier1',
            confidence=abs(best.score_v2.S_NET),
            agg_S_LONG=agg_scores['agg_S_LONG'],
            agg_S_SHORT=agg_scores['agg_S_SHORT'],
            agg_S_NET=agg_scores['agg_S_NET'],
            agg_S_RISK=agg_scores['agg_S_RISK'],
            agg_S_QUALITY=agg_scores['agg_S_QUALITY'],
            decisions=decisions_v2,
            regime=regime
        )
    
    def _try_tier2(
        self,
        decisions_v2: List[StrategyDecisionV2],
        agg_scores: Dict[str, float],
        regime: Optional[str]
    ) -> Optional[EnsembleDecisionV2]:
        """
        Tier 2: Consensus 시도
        
        **조건**:
        - abs(weighted_avg_S_NET) >= consensus_threshold
        - ≥min_strategies가 같은 방향 지지
        - 지배 전략 방지 (max_strategy_weight)
        
        Returns:
            EnsembleDecisionV2 또는 None (조건 미달 시)
        """
        agg_S_NET = agg_scores['agg_S_NET']
        
        # Check weighted avg threshold
        if abs(agg_S_NET) < self.consensus_threshold:
            return None
        
        # Determine consensus direction
        consensus_dir = 'LONG' if agg_S_NET > 0 else 'SHORT'
        
        # Count agreeing strategies
        agreeing_strategies = [
            d for d in decisions_v2
            if d.score_v2.S_DIR == consensus_dir
        ]
        
        if len(agreeing_strategies) < self.min_strategies:
            return None
        
        # Check dominance
        is_valid, dominant_list = self._check_dominance(decisions_v2)
        if not is_valid:
            logger.warning(
                f"⚠️  [ENSEMBLE V2] Tier2: Dominance violation - {dominant_list}"
            )
            return self._create_skip_decision(
                reason=f'tier2_dominance_violation (dominant={dominant_list})',
                decisions=decisions_v2,
                regime=regime,
                agg_scores=agg_scores,
                dominant_strategies=dominant_list
            )
        
        # Select representative signal (highest S_NET among agreeing)
        representative = max(agreeing_strategies, key=lambda x: abs(x.score_v2.S_NET))
        entry = representative.raw_signal.get('entry')
        sl = representative.raw_signal.get('sl')
        tp = representative.raw_signal.get('tp')
        
        return EnsembleDecisionV2(
            side=consensus_dir,
            action='진입',
            entry=entry,
            sl=sl,
            tp=tp,
            reason=[
                f"tier2_consensus",
                f"agreeing_strategies={len(agreeing_strategies)}",
                f"weighted_S_NET={agg_S_NET:.3f}"
            ],
            strategy_votes={d.name: d.score_v2.S_NET for d in decisions_v2},
            dominant_strategies=[],
            tier='tier2',
            confidence=abs(agg_S_NET),
            agg_S_LONG=agg_scores['agg_S_LONG'],
            agg_S_SHORT=agg_scores['agg_S_SHORT'],
            agg_S_NET=agg_S_NET,
            agg_S_RISK=agg_scores['agg_S_RISK'],
            agg_S_QUALITY=agg_scores['agg_S_QUALITY'],
            decisions=decisions_v2,
            regime=regime
        )
    
    # =========================================================================
    # Private Methods: Helpers
    # =========================================================================
    
    def _aggregate_scores(
        self,
        decisions_v2: List[StrategyDecisionV2]
    ) -> Dict[str, float]:
        """
        전략들의 Score V2를 가중 평균으로 집계
        
        Args:
            decisions_v2: List[StrategyDecisionV2]
        
        Returns:
            {
                'agg_S_LONG': float,
                'agg_S_SHORT': float,
                'agg_S_NET': float,
                'agg_S_RISK': float,
                'agg_S_QUALITY': float
            }
        """
        if not decisions_v2:
            return {
                'agg_S_LONG': 0.0,
                'agg_S_SHORT': 0.0,
                'agg_S_NET': 0.0,
                'agg_S_RISK': 0.5,
                'agg_S_QUALITY': 0.5
            }
        
        total_weight = sum(d.weight for d in decisions_v2)
        
        agg_S_LONG = sum(d.weight * d.score_v2.S_LONG for d in decisions_v2) / total_weight
        agg_S_SHORT = sum(d.weight * d.score_v2.S_SHORT for d in decisions_v2) / total_weight
        agg_S_NET = agg_S_LONG - agg_S_SHORT
        agg_S_RISK = sum(d.weight * d.score_v2.S_RISK for d in decisions_v2) / total_weight
        agg_S_QUALITY = sum(d.weight * d.score_v2.S_QUALITY for d in decisions_v2) / total_weight
        
        return {
            'agg_S_LONG': agg_S_LONG,
            'agg_S_SHORT': agg_S_SHORT,
            'agg_S_NET': agg_S_NET,
            'agg_S_RISK': agg_S_RISK,
            'agg_S_QUALITY': agg_S_QUALITY
        }
    
    def _check_dominance(
        self,
        decisions_v2: List[StrategyDecisionV2]
    ) -> Tuple[bool, List[str]]:
        """
        지배 전략 방지 검사
        
        **규칙**:
        - 전략이 1개뿐이면 dominance check 스킵 (당연히 100% 기여)
        - 한 전략의 기여도 = abs(S_NET × weight) / total_abs_contribution
        - 기여도 > max_strategy_weight 이면 지배 전략으로 판정
        
        Args:
            decisions_v2: List[StrategyDecisionV2]
        
        Returns:
            (is_valid, dominant_strategies)
            - is_valid: True if no dominance
            - dominant_strategies: list of dominant strategy names
        """
        if not decisions_v2:
            return (True, [])
        
        # PHASE23-3: 단일 전략일 때는 dominance check 스킵
        if len(decisions_v2) == 1:
            return (True, [])
        
        # Calculate total absolute contribution
        total_abs_contribution = sum(
            abs(d.score_v2.S_NET * d.weight) for d in decisions_v2
        )
        
        if total_abs_contribution == 0:
            return (True, [])
        
        # Check each strategy's contribution
        dominant_strategies = []
        for d in decisions_v2:
            contribution = abs(d.score_v2.S_NET * d.weight) / total_abs_contribution
            if contribution > self.max_strategy_weight:
                dominant_strategies.append(d.name)
                logger.debug(
                    f"⚠️  [ENSEMBLE V2] Dominant strategy: {d.name} "
                    f"(contribution={contribution:.2%} > {self.max_strategy_weight:.2%})"
                )
        
        return (len(dominant_strategies) == 0, dominant_strategies)
    
    def _create_skip_decision(
        self,
        reason: str,
        decisions: List[StrategyDecisionV2],
        regime: Optional[str],
        agg_scores: Optional[Dict[str, float]] = None,
        dominant_strategies: Optional[List[str]] = None
    ) -> EnsembleDecisionV2:
        """
        Skip 결정 생성 (helper)
        
        Args:
            reason: Skip 이유
            decisions: 전략 결정 목록
            regime: 현재 Regime
            agg_scores: (Optional) 집계된 점수
            dominant_strategies: (Optional) 지배 전략 목록
        
        Returns:
            EnsembleDecisionV2 (side=None, tier='skip')
        """
        if agg_scores is None:
            agg_scores = self._aggregate_scores(decisions)
        
        return EnsembleDecisionV2(
            side=None,
            action='HOLD',
            entry=None,
            sl=None,
            tp=None,
            reason=[f"skip: {reason}"],
            strategy_votes={d.name: d.score_v2.S_NET for d in decisions},
            dominant_strategies=dominant_strategies or [],
            tier='skip',
            confidence=0.0,
            agg_S_LONG=agg_scores['agg_S_LONG'],
            agg_S_SHORT=agg_scores['agg_S_SHORT'],
            agg_S_NET=agg_scores['agg_S_NET'],
            agg_S_RISK=agg_scores['agg_S_RISK'],
            agg_S_QUALITY=agg_scores['agg_S_QUALITY'],
            decisions=decisions,
            regime=regime
        )


# Export
__all__ = [
    'StrategyDecisionV2',
    'EnsembleDecisionV2',
    'EnsembleAggregatorV2',
]
