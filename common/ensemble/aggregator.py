#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ensemble Signal Aggregator
===========================
PHASE19-3: 여러 전략의 신호를 통합하여 최종 Ensemble 의사결정 생성

**3-Tier Aggregation**:
- Tier 1: High-Confidence (score >= 0.8)
- Tier 2: Consensus (0.5 <= score < 0.8, 2+ votes)
- Tier 3: Skip (조건 미달)
"""
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
import pandas as pd
import logging

from .factors import compute_all_factors
from .score_engine import ScoreEngine
from common.registry.strategy_registry import StrategyRegistry
from common.registry.strategy_metadata import StrategyMetadata

logger = logging.getLogger(__name__)


@dataclass
class StrategyDecision:
    """
    개별 전략의 신호 + 점수
    
    Attributes:
        name: 전략 이름 (예: 'scalping')
        side: 'LONG' | 'SHORT' | None
        score: 0~1 (ScoreEngine 계산 결과)
        confidence: 0~1 (score와 동일하거나 추가 조정)
        raw_signal: 기존 signal_logic 결과 (dict)
        metadata: 전략 메타데이터
    """
    name: str
    side: Optional[str]
    score: float
    confidence: float
    raw_signal: Any
    metadata: StrategyMetadata


@dataclass
class EnsembleDecision:
    """
    Ensemble 최종 의사결정
    
    Attributes:
        side: 최종 방향 ('LONG' | 'SHORT' | None)
        confidence: 0~1 (최종 신뢰도)
        chosen_strategy: 선택된 전략 (Tier1 경우)
        contributing_strategies: 기여한 전략 목록
        tier: 'tier1' | 'tier2' | 'skip'
        decisions: 모든 전략 결정 (디버깅용)
        regime: 현재 Regime (참고용)
        reason: 결정 이유 (로그용)
    """
    side: Optional[str]
    confidence: float
    chosen_strategy: Optional[str] = None
    contributing_strategies: List[str] = field(default_factory=list)
    tier: str = 'skip'
    decisions: List[StrategyDecision] = field(default_factory=list)
    regime: Optional[str] = None
    reason: str = ''


class EnsembleAggregator:
    """
    Ensemble Signal Aggregator
    
    **역할**:
    - 여러 전략의 신호를 평가하고 점수화
    - 3-Tier 규칙으로 최종 Ensemble 의사결정 생성
    
    **사용 예시**:
    ```python
    aggregator = EnsembleAggregator(registry, score_engine)
    ensemble_decision = aggregator.decide(
        strategy_names=['scalping', 'trend', 'breakout'],
        df=df,
        regime='trending'
    )
    
    if ensemble_decision.side:
        # 진입
        execute(ensemble_decision.side)
    else:
        # 건너뛰기
        logger.info(f"Skip: {ensemble_decision.reason}")
    ```
    """
    
    def __init__(
        self,
        registry: StrategyRegistry,
        score_engine: ScoreEngine,
        min_tier1_score: float = 0.8,
        min_tier2_score: float = 0.5,
        tier1_conflict_diff: float = 0.15,
        min_tier2_votes: int = 2,
    ):
        """
        초기화
        
        Args:
            registry: StrategyRegistry 인스턴스
            score_engine: ScoreEngine 인스턴스
            min_tier1_score: Tier 1 최소 점수 (기본값: 0.8)
            min_tier2_score: Tier 2 최소 점수 (기본값: 0.5)
            tier1_conflict_diff: Tier 1 충돌 시 최소 차이 (기본값: 0.15)
            min_tier2_votes: Tier 2 최소 투표 수 (기본값: 2)
        """
        self.registry = registry
        self.score_engine = score_engine
        self.min_tier1_score = min_tier1_score
        self.min_tier2_score = min_tier2_score
        self.tier1_conflict_diff = tier1_conflict_diff
        self.min_tier2_votes = min_tier2_votes
    
    def evaluate_strategies(
        self,
        strategy_names: List[str],
        df: pd.DataFrame,
        regime: Optional[str] = None,
    ) -> List[StrategyDecision]:
        """
        여러 전략을 평가하여 StrategyDecision 리스트 생성
        
        **처리 흐름**:
        1. 각 전략에 대해 compute_signal(df) 호출
        2. 신호가 있으면 Factor 계산 (compute_all_factors)
        3. Score 계산 (score_engine.compute_strategy_score)
        4. StrategyDecision 생성
        
        Args:
            strategy_names: 평가할 전략 이름 리스트
            df: OHLCV + 지표 포함 DataFrame
            regime: 현재 시장 Regime (None이면 unknown)
        
        Returns:
            List[StrategyDecision]: 신호가 있는 전략들의 결정 리스트
        """
        decisions = []
        
        # Factor 계산 (모든 전략이 공통으로 사용)
        try:
            factors = compute_all_factors(df)
        except Exception as e:
            logger.warning(f"⚠️  Factor 계산 실패: {e}, 중립값 사용")
            factors = {
                'momentum': 0.5,
                'volatility': 0.5,
                'volume': 0.5,
                'trend_strength': 0.5,
                'overbought_oversold': 0.5,
                'breakout_probability': 0.5,
            }
        
        for strategy_name in strategy_names:
            try:
                # 전략 인스턴스 생성
                metadata = self.registry.get_metadata(strategy_name)
                if not metadata:
                    logger.warning(f"⚠️  전략 '{strategy_name}' 메타데이터 없음, 스킵")
                    continue
                
                # Config 준비 (기본값 사용)
                config = self._get_default_config(strategy_name)
                
                # 전략 인스턴스 생성
                strategy_instance = self.registry.get(strategy_name, config)
                if not strategy_instance:
                    logger.warning(f"⚠️  전략 '{strategy_name}' 생성 실패, 스킵")
                    continue
                
                # 신호 계산
                raw_signal = strategy_instance.compute_signal(df)
                
                # 신호 유효성 검사
                if not raw_signal or not raw_signal.get('direction'):
                    # 신호 없음 or direction=None → 스킵
                    continue
                
                side = raw_signal.get('direction')
                if side not in ['LONG', 'SHORT']:
                    # 유효하지 않은 방향 → 스킵
                    continue
                
                # Score 계산
                score = self.score_engine.compute_strategy_score(
                    metadata=metadata,
                    factors=factors,
                    regime=regime
                )
                
                # StrategyDecision 생성
                decision = StrategyDecision(
                    name=strategy_name,
                    side=side,
                    score=score,
                    confidence=score,  # 현재는 동일, 미래에 추가 조정 가능
                    raw_signal=raw_signal,
                    metadata=metadata,
                )
                
                decisions.append(decision)
                
                logger.debug(
                    f"📊 [ENSEMBLE] {strategy_name}: {side} (score={score:.3f})"
                )
            
            except Exception as e:
                logger.warning(f"⚠️  전략 '{strategy_name}' 평가 실패: {e}", exc_info=True)
                continue
        
        return decisions
    
    def aggregate(
        self,
        decisions: List[StrategyDecision],
        regime: Optional[str] = None,
    ) -> EnsembleDecision:
        """
        여러 StrategyDecision을 3-Tier 규칙으로 통합
        
        **3-Tier 규칙**:
        - Tier 1: High-Confidence (score >= 0.8)
        - Tier 2: Consensus (0.5 <= score < 0.8, 2+ votes)
        - Tier 3: Skip (조건 미달)
        
        Args:
            decisions: StrategyDecision 리스트
            regime: 현재 Regime (참고용)
        
        Returns:
            EnsembleDecision: 최종 의사결정
        """
        if not decisions:
            return EnsembleDecision(
                side=None,
                confidence=0.0,
                tier='skip',
                reason='No signals',
                decisions=[],
                regime=regime,
            )
        
        # Tier 1: High-Confidence
        tier1_result = self._try_tier1(decisions, regime)
        if tier1_result:
            return tier1_result
        
        # Tier 2: Consensus
        tier2_result = self._try_tier2(decisions, regime)
        if tier2_result:
            return tier2_result
        
        # Tier 3: Skip
        return EnsembleDecision(
            side=None,
            confidence=0.0,
            tier='skip',
            reason='No confident signals (Tier 1/2 조건 미달)',
            decisions=decisions,
            regime=regime,
        )
    
    def decide(
        self,
        strategy_names: List[str],
        df: pd.DataFrame,
        regime: Optional[str] = None,
    ) -> EnsembleDecision:
        """
        evaluate_strategies + aggregate를 한 번에 수행
        
        **편의 메서드**: 엔진에서 이 메서드 하나만 호출하면 됨
        
        Args:
            strategy_names: 평가할 전략 이름 리스트
            df: OHLCV + 지표 DataFrame
            regime: 현재 Regime
        
        Returns:
            EnsembleDecision: 최종 의사결정
        """
        decisions = self.evaluate_strategies(strategy_names, df, regime)
        return self.aggregate(decisions, regime)
    
    # =========================================================================
    # Private Methods
    # =========================================================================
    
    def _try_tier1(
        self,
        decisions: List[StrategyDecision],
        regime: Optional[str]
    ) -> Optional[EnsembleDecision]:
        """
        Tier 1: High-Confidence 시도
        
        Returns:
            EnsembleDecision 또는 None (조건 미달 시)
        """
        tier1_decisions = [d for d in decisions if d.score >= self.min_tier1_score]
        
        if not tier1_decisions:
            return None
        
        if len(tier1_decisions) == 1:
            # 단일 High-Confidence → 즉시 선택
            chosen = tier1_decisions[0]
            return EnsembleDecision(
                side=chosen.side,
                confidence=chosen.score,
                chosen_strategy=chosen.name,
                contributing_strategies=[chosen.name],
                tier='tier1',
                decisions=decisions,
                regime=regime,
                reason=f"High-confidence single pick ({chosen.name}, score={chosen.score:.3f})",
            )
        
        # 여러 High-Confidence → 충돌 검사
        long_decisions = [d for d in tier1_decisions if d.side == 'LONG']
        short_decisions = [d for d in tier1_decisions if d.side == 'SHORT']
        
        if long_decisions and short_decisions:
            # 충돌 발생 → 점수 차이 검사
            long_max = max(d.score for d in long_decisions)
            short_max = max(d.score for d in short_decisions)
            diff = abs(long_max - short_max)
            
            if diff >= self.tier1_conflict_diff:
                # 차이가 충분히 큼 → 높은 쪽 선택
                if long_max > short_max:
                    chosen = max(long_decisions, key=lambda x: x.score)
                else:
                    chosen = max(short_decisions, key=lambda x: x.score)
                
                return EnsembleDecision(
                    side=chosen.side,
                    confidence=chosen.score,
                    chosen_strategy=chosen.name,
                    contributing_strategies=[chosen.name],
                    tier='tier1',
                    decisions=decisions,
                    regime=regime,
                    reason=f"High-confidence conflict resolved ({chosen.name}, diff={diff:.3f})",
                )
            else:
                # 차이가 작음 → Conflict, NO TRADE
                return EnsembleDecision(
                    side=None,
                    confidence=0.0,
                    tier='skip',
                    decisions=decisions,
                    regime=regime,
                    reason=f"Tier1 conflict (diff={diff:.3f} < {self.tier1_conflict_diff})",
                )
        else:
            # 같은 방향만 존재 → 최고 점수 선택
            chosen = max(tier1_decisions, key=lambda x: x.score)
            return EnsembleDecision(
                side=chosen.side,
                confidence=chosen.score,
                chosen_strategy=chosen.name,
                contributing_strategies=[d.name for d in tier1_decisions],
                tier='tier1',
                decisions=decisions,
                regime=regime,
                reason=f"High-confidence unanimous ({len(tier1_decisions)} strategies)",
            )
    
    def _try_tier2(
        self,
        decisions: List[StrategyDecision],
        regime: Optional[str]
    ) -> Optional[EnsembleDecision]:
        """
        Tier 2: Consensus Vote 시도
        
        Returns:
            EnsembleDecision 또는 None (조건 미달 시)
        """
        tier2_decisions = [
            d for d in decisions
            if self.min_tier2_score <= d.score < self.min_tier1_score
        ]
        
        if len(tier2_decisions) < self.min_tier2_votes:
            return None
        
        long_votes = [d for d in tier2_decisions if d.side == 'LONG']
        short_votes = [d for d in tier2_decisions if d.side == 'SHORT']
        
        # 한 쪽이 최소 2개 이상 & 다른 쪽보다 명확히 많음
        if len(long_votes) >= self.min_tier2_votes and len(long_votes) > len(short_votes):
            avg_confidence = sum(d.score for d in long_votes) / len(long_votes)
            return EnsembleDecision(
                side='LONG',
                confidence=avg_confidence,
                contributing_strategies=[d.name for d in long_votes],
                tier='tier2',
                decisions=decisions,
                regime=regime,
                reason=f"Consensus vote (LONG: {len(long_votes)} vs SHORT: {len(short_votes)})",
            )
        elif len(short_votes) >= self.min_tier2_votes and len(short_votes) > len(long_votes):
            avg_confidence = sum(d.score for d in short_votes) / len(short_votes)
            return EnsembleDecision(
                side='SHORT',
                confidence=avg_confidence,
                contributing_strategies=[d.name for d in short_votes],
                tier='tier2',
                decisions=decisions,
                regime=regime,
                reason=f"Consensus vote (SHORT: {len(short_votes)} vs LONG: {len(long_votes)})",
            )
        else:
            # 동률 or 조건 미달
            return None
    
    def _get_default_config(self, strategy_name: str) -> Dict[str, Any]:
        """
        전략별 기본 Config 반환
        
        **현재**: 간단한 기본값 사용
        **미래**: Config 파일에서 로드하거나 더 정교한 기본값
        
        Args:
            strategy_name: 전략 이름
        
        Returns:
            dict: 기본 Config
        """
        # 간단한 기본값 (실제로는 전략에 맞게 조정 필요)
        return {
            'symbol': 'BTCUSDT',
            'timeframe': '1m',
            'risk_per_trade': 0.01,
            # 추가 필드는 전략에서 기본값 사용
        }


# Export
__all__ = [
    'StrategyDecision',
    'EnsembleDecision',
    'EnsembleAggregator',
]
