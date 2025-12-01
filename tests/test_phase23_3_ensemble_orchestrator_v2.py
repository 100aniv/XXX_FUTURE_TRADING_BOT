#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE23-3: Ensemble Orchestrator V2 Unit Tests
===============================================
Score V2 기반 앙상블 의사결정 테스트

**테스트 범위**:
1. ScoreEngineV2: Score V2 필드 추출 및 계산
2. EnsembleAggregatorV2: 3-Tier 의사결정 (High-Confidence / Consensus / Skip)
3. 지배 전략 방지 (Dominance constraint)
4. Risk/Quality 필터링
"""
import pytest
import pandas as pd
from common.ensemble.score_engine_v2 import ScoreEngineV2, ScoreComponentsV2
from common.ensemble.aggregator_v2 import (
    EnsembleAggregatorV2,
    StrategyDecisionV2,
    EnsembleDecisionV2
)
from common.registry.strategy_metadata import StrategyMetadata


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_metadata():
    """샘플 전략 메타데이터"""
    return StrategyMetadata(
        strategy_name='test_strategy',
        strategy_type='momentum',
        supported_symbols=['BTCUSDT'],
        supported_timeframes=['5m'],
        version='v1.0',
        optimal_regime='trending',
        worst_regime='choppy',
        base_weight=1.0,
        factor_weights={
            'momentum': 0.3,
            'volume': 0.3,
            'trend_strength': 0.4
        }
    )


@pytest.fixture
def score_engine_v2():
    """ScoreEngineV2 인스턴스"""
    return ScoreEngineV2()


@pytest.fixture
def ensemble_config():
    """Ensemble config"""
    return {
        'ensemble': {
            'enabled': True,
            'mode': 'score_v2',
            'high_conf_threshold': 0.7,
            'consensus_threshold': 0.4,
            'min_strategies': 2,
            'max_strategy_weight': 0.6,
            'max_risk': 0.8,
            'min_quality': 0.3,
            'strategy_weights': {
                'strategy_a': 1.0,
                'strategy_b': 1.0,
                'strategy_c': 1.0
            }
        }
    }


@pytest.fixture
def aggregator_v2(score_engine_v2, ensemble_config):
    """EnsembleAggregatorV2 인스턴스"""
    return EnsembleAggregatorV2(
        score_engine=score_engine_v2,
        config=ensemble_config
    )


# =============================================================================
# ScoreEngineV2 Tests
# =============================================================================

def test_score_engine_v2_extracts_score_v2_fields(score_engine_v2, sample_metadata):
    """
    ScoreEngineV2가 signal에서 Score V2 필드를 올바르게 추출하는지 테스트
    """
    signal = {
        'side': 'LONG',
        'entry': 50000,
        'sl': 49000,
        'tp': 51000,
        'S_LONG': 0.8,
        'S_SHORT': 0.2,
        'S_RISK': 0.3,
        'S_QUALITY': 0.9
    }
    
    score_v2 = score_engine_v2.compute_strategy_score_v2(
        signal=signal,
        metadata=sample_metadata,
        mode='score_v2'
    )
    
    assert isinstance(score_v2, ScoreComponentsV2)
    assert score_v2.S_LONG == 0.8
    assert score_v2.S_SHORT == 0.2
    assert score_v2.S_RISK == 0.3
    assert score_v2.S_QUALITY == 0.9
    assert score_v2.S_NET == pytest.approx(0.6, abs=0.01)  # 0.8 - 0.2
    assert score_v2.S_ABS == pytest.approx(1.0, abs=0.01)  # 0.8 + 0.2
    assert score_v2.S_DIR == 'LONG'


def test_score_components_v2_direction_determination():
    """
    ScoreComponentsV2가 S_NET 기반으로 방향을 올바르게 결정하는지 테스트
    """
    # LONG
    score_long = ScoreComponentsV2(
        S_LONG=0.8, S_SHORT=0.2,
        S_NET=0.0, S_ABS=0.0, S_RISK=0.5, S_QUALITY=0.5, S_DIR=None
    )
    assert score_long.S_DIR == 'LONG'
    
    # SHORT
    score_short = ScoreComponentsV2(
        S_LONG=0.2, S_SHORT=0.8,
        S_NET=0.0, S_ABS=0.0, S_RISK=0.5, S_QUALITY=0.5, S_DIR=None
    )
    assert score_short.S_DIR == 'SHORT'
    
    # None (neutral)
    score_neutral = ScoreComponentsV2(
        S_LONG=0.3, S_SHORT=0.3,
        S_NET=0.0, S_ABS=0.0, S_RISK=0.5, S_QUALITY=0.5, S_DIR=None
    )
    assert score_neutral.S_DIR is None


def test_score_engine_v2_clamps_values(score_engine_v2, sample_metadata):
    """
    ScoreEngineV2가 범위를 벗어난 값을 올바르게 클램핑하는지 테스트
    """
    signal = {
        'side': 'LONG',
        'S_LONG': 1.5,  # > 1.0
        'S_SHORT': -0.2,  # < 0.0
        'S_RISK': 2.0,  # > 1.0
        'S_QUALITY': -0.5  # < 0.0
    }
    
    score_v2 = score_engine_v2.compute_strategy_score_v2(
        signal=signal,
        metadata=sample_metadata,
        mode='score_v2'
    )
    
    assert 0.0 <= score_v2.S_LONG <= 1.0
    assert 0.0 <= score_v2.S_SHORT <= 1.0
    assert 0.0 <= score_v2.S_RISK <= 1.0
    assert 0.0 <= score_v2.S_QUALITY <= 1.0


# =============================================================================
# EnsembleAggregatorV2 Tests - Tier 1 (High-Confidence)
# =============================================================================

def test_tier1_high_confidence_long(aggregator_v2, sample_metadata):
    """
    Tier 1: 강한 LONG 신호 (S_NET >= high_conf_threshold) → LONG 진입
    """
    # Strategy A: 강한 LONG (S_NET = 0.8)
    score_v2_a = ScoreComponentsV2(
        S_LONG=0.9, S_SHORT=0.1,
        S_NET=0.0, S_ABS=0.0, S_RISK=0.3, S_QUALITY=0.8, S_DIR=None
    )
    decision_a = StrategyDecisionV2(
        name='strategy_a',
        score_v2=score_v2_a,
        raw_signal={'side': 'LONG', 'entry': 50000, 'sl': 49000, 'tp': 51000},
        metadata=sample_metadata,
        weight=1.0
    )
    
    decisions_v2 = [decision_a]
    
    ensemble_decision = aggregator_v2.aggregate_v2(decisions_v2, regime=None)
    
    assert ensemble_decision.side == 'LONG'
    assert ensemble_decision.tier == 'tier1'
    assert ensemble_decision.confidence >= 0.7
    assert ensemble_decision.entry == 50000


def test_tier1_high_confidence_short(aggregator_v2, sample_metadata):
    """
    Tier 1: 강한 SHORT 신호 (S_NET <= -high_conf_threshold) → SHORT 진입
    """
    # Strategy A: 강한 SHORT (S_NET = -0.75)
    score_v2_a = ScoreComponentsV2(
        S_LONG=0.1, S_SHORT=0.85,
        S_NET=0.0, S_ABS=0.0, S_RISK=0.3, S_QUALITY=0.8, S_DIR=None
    )
    decision_a = StrategyDecisionV2(
        name='strategy_a',
        score_v2=score_v2_a,
        raw_signal={'side': 'SHORT', 'entry': 50000, 'sl': 51000, 'tp': 49000},
        metadata=sample_metadata,
        weight=1.0
    )
    
    decisions_v2 = [decision_a]
    
    ensemble_decision = aggregator_v2.aggregate_v2(decisions_v2, regime=None)
    
    assert ensemble_decision.side == 'SHORT'
    assert ensemble_decision.tier == 'tier1'
    assert ensemble_decision.confidence >= 0.7


# =============================================================================
# EnsembleAggregatorV2 Tests - Tier 2 (Consensus)
# =============================================================================

def test_tier2_consensus_long(aggregator_v2, sample_metadata):
    """
    Tier 2: 2개 이상 전략이 LONG 방향 지지 (weighted avg >= consensus_threshold)
    
    **주의**: Dominance를 피하기 위해 두 전략의 S_NET을 비슷하게 설정
    """
    # Strategy A: 중간 LONG (S_NET = 0.48)
    score_v2_a = ScoreComponentsV2(
        S_LONG=0.68, S_SHORT=0.2,
        S_NET=0.0, S_ABS=0.0, S_RISK=0.3, S_QUALITY=0.7, S_DIR=None
    )
    decision_a = StrategyDecisionV2(
        name='strategy_a',
        score_v2=score_v2_a,
        raw_signal={'side': 'LONG', 'entry': 50000, 'sl': 49000, 'tp': 51000},
        metadata=sample_metadata,
        weight=1.0
    )
    
    # Strategy B: 중간 LONG (S_NET = 0.36)
    score_v2_b = ScoreComponentsV2(
        S_LONG=0.58, S_SHORT=0.22,
        S_NET=0.0, S_ABS=0.0, S_RISK=0.4, S_QUALITY=0.6, S_DIR=None
    )
    decision_b = StrategyDecisionV2(
        name='strategy_b',
        score_v2=score_v2_b,
        raw_signal={'side': 'LONG', 'entry': 50000, 'sl': 49000, 'tp': 51000},
        metadata=sample_metadata,
        weight=1.0
    )
    
    decisions_v2 = [decision_a, decision_b]
    
    ensemble_decision = aggregator_v2.aggregate_v2(decisions_v2, regime=None)
    
    assert ensemble_decision.side == 'LONG'
    assert ensemble_decision.tier == 'tier2'
    assert ensemble_decision.agg_S_NET >= 0.4  # consensus threshold


def test_tier2_consensus_short(aggregator_v2, sample_metadata):
    """
    Tier 2: 2개 이상 전략이 SHORT 방향 지지
    """
    # Strategy A: 중간 SHORT (S_NET = -0.5)
    score_v2_a = ScoreComponentsV2(
        S_LONG=0.2, S_SHORT=0.7,
        S_NET=0.0, S_ABS=0.0, S_RISK=0.3, S_QUALITY=0.7, S_DIR=None
    )
    decision_a = StrategyDecisionV2(
        name='strategy_a',
        score_v2=score_v2_a,
        raw_signal={'side': 'SHORT', 'entry': 50000, 'sl': 51000, 'tp': 49000},
        metadata=sample_metadata,
        weight=1.0
    )
    
    # Strategy B: 약한 SHORT (S_NET = -0.35)
    score_v2_b = ScoreComponentsV2(
        S_LONG=0.25, S_SHORT=0.6,
        S_NET=0.0, S_ABS=0.0, S_RISK=0.4, S_QUALITY=0.6, S_DIR=None
    )
    decision_b = StrategyDecisionV2(
        name='strategy_b',
        score_v2=score_v2_b,
        raw_signal={'side': 'SHORT', 'entry': 50000, 'sl': 51000, 'tp': 49000},
        metadata=sample_metadata,
        weight=1.0
    )
    
    decisions_v2 = [decision_a, decision_b]
    
    ensemble_decision = aggregator_v2.aggregate_v2(decisions_v2, regime=None)
    
    assert ensemble_decision.side == 'SHORT'
    assert ensemble_decision.tier == 'tier2'


# =============================================================================
# EnsembleAggregatorV2 Tests - Tier 3 (Skip)
# =============================================================================

def test_tier3_skip_low_scores(aggregator_v2, sample_metadata):
    """
    Tier 3: 모든 전략의 점수가 낮음 → Skip
    """
    # Strategy A: 약한 신호 (S_NET = 0.2)
    score_v2_a = ScoreComponentsV2(
        S_LONG=0.4, S_SHORT=0.2,
        S_NET=0.0, S_ABS=0.0, S_RISK=0.5, S_QUALITY=0.5, S_DIR=None
    )
    decision_a = StrategyDecisionV2(
        name='strategy_a',
        score_v2=score_v2_a,
        raw_signal={'side': 'LONG', 'entry': 50000, 'sl': 49000, 'tp': 51000},
        metadata=sample_metadata,
        weight=1.0
    )
    
    # Strategy B: 약한 신호 (S_NET = 0.15)
    score_v2_b = ScoreComponentsV2(
        S_LONG=0.35, S_SHORT=0.2,
        S_NET=0.0, S_ABS=0.0, S_RISK=0.5, S_QUALITY=0.5, S_DIR=None
    )
    decision_b = StrategyDecisionV2(
        name='strategy_b',
        score_v2=score_v2_b,
        raw_signal={'side': 'LONG', 'entry': 50000, 'sl': 49000, 'tp': 51000},
        metadata=sample_metadata,
        weight=1.0
    )
    
    decisions_v2 = [decision_a, decision_b]
    
    ensemble_decision = aggregator_v2.aggregate_v2(decisions_v2, regime=None)
    
    assert ensemble_decision.side is None
    assert ensemble_decision.tier == 'skip'


def test_tier3_skip_no_signals(aggregator_v2):
    """
    Tier 3: 신호 없음 → Skip
    """
    decisions_v2 = []
    
    ensemble_decision = aggregator_v2.aggregate_v2(decisions_v2, regime=None)
    
    assert ensemble_decision.side is None
    assert ensemble_decision.tier == 'skip'
    assert 'no_signals' in ensemble_decision.reason[0]


# =============================================================================
# Dominance Prevention Tests
# =============================================================================

def test_dominance_prevention_tier1(aggregator_v2, sample_metadata):
    """
    지배 전략 방지: Tier1에서 한 전략의 기여도가 max_strategy_weight 초과 시 Skip
    """
    # Strategy A: 매우 강한 LONG (S_NET = 0.9, 지배적)
    score_v2_a = ScoreComponentsV2(
        S_LONG=0.95, S_SHORT=0.05,
        S_NET=0.0, S_ABS=0.0, S_RISK=0.2, S_QUALITY=0.9, S_DIR=None
    )
    decision_a = StrategyDecisionV2(
        name='strategy_a',
        score_v2=score_v2_a,
        raw_signal={'side': 'LONG', 'entry': 50000, 'sl': 49000, 'tp': 51000},
        metadata=sample_metadata,
        weight=1.0
    )
    
    # Strategy B: 매우 약한 LONG (S_NET = 0.05)
    score_v2_b = ScoreComponentsV2(
        S_LONG=0.1, S_SHORT=0.05,
        S_NET=0.0, S_ABS=0.0, S_RISK=0.5, S_QUALITY=0.3, S_DIR=None
    )
    decision_b = StrategyDecisionV2(
        name='strategy_b',
        score_v2=score_v2_b,
        raw_signal={'side': 'LONG', 'entry': 50000, 'sl': 49000, 'tp': 51000},
        metadata=sample_metadata,
        weight=1.0
    )
    
    decisions_v2 = [decision_a, decision_b]
    
    ensemble_decision = aggregator_v2.aggregate_v2(decisions_v2, regime=None)
    
    # Dominance violation → Skip
    assert ensemble_decision.side is None
    assert ensemble_decision.tier == 'skip'
    assert 'dominance' in ensemble_decision.reason[0].lower()


# =============================================================================
# Risk/Quality Filter Tests
# =============================================================================

def test_skip_high_risk(aggregator_v2, sample_metadata):
    """
    Risk 필터: agg_S_RISK > max_risk → Skip
    """
    # Strategy A: 강한 LONG이지만 high risk (S_RISK = 0.9)
    score_v2_a = ScoreComponentsV2(
        S_LONG=0.9, S_SHORT=0.1,
        S_NET=0.0, S_ABS=0.0, S_RISK=0.9, S_QUALITY=0.8, S_DIR=None  # ⚠️ High risk
    )
    decision_a = StrategyDecisionV2(
        name='strategy_a',
        score_v2=score_v2_a,
        raw_signal={'side': 'LONG', 'entry': 50000, 'sl': 49000, 'tp': 51000},
        metadata=sample_metadata,
        weight=1.0
    )
    
    decisions_v2 = [decision_a]
    
    ensemble_decision = aggregator_v2.aggregate_v2(decisions_v2, regime=None)
    
    assert ensemble_decision.side is None
    assert ensemble_decision.tier == 'skip'
    assert 'high_risk' in ensemble_decision.reason[0].lower()


def test_skip_low_quality(aggregator_v2, sample_metadata):
    """
    Quality 필터: agg_S_QUALITY < min_quality → Skip
    """
    # Strategy A: 강한 LONG이지만 low quality (S_QUALITY = 0.2)
    score_v2_a = ScoreComponentsV2(
        S_LONG=0.9, S_SHORT=0.1,
        S_NET=0.0, S_ABS=0.0, S_RISK=0.3, S_QUALITY=0.2, S_DIR=None  # ⚠️ Low quality
    )
    decision_a = StrategyDecisionV2(
        name='strategy_a',
        score_v2=score_v2_a,
        raw_signal={'side': 'LONG', 'entry': 50000, 'sl': 49000, 'tp': 51000},
        metadata=sample_metadata,
        weight=1.0
    )
    
    decisions_v2 = [decision_a]
    
    ensemble_decision = aggregator_v2.aggregate_v2(decisions_v2, regime=None)
    
    assert ensemble_decision.side is None
    assert ensemble_decision.tier == 'skip'
    assert 'low_quality' in ensemble_decision.reason[0].lower()


# =============================================================================
# Summary
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
