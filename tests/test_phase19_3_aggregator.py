#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE19-3 Ensemble Aggregator 테스트
====================================
Ensemble Signal Aggregator 단위 테스트
"""
import pytest
from dataclasses import dataclass
from unittest.mock import Mock, MagicMock
from typing import Optional

from common.ensemble import (
    StrategyDecision,
    EnsembleDecision,
    EnsembleAggregator,
    ScoreEngine,
)
from common.registry import StrategyMetadata


# ============================================================================
# Mock Setup
# ============================================================================

def create_mock_decision(name: str, side: str, score: float) -> StrategyDecision:
    """Mock StrategyDecision 생성"""
    metadata = StrategyMetadata(
        strategy_name=name,
        strategy_type='test',
        base_weight=1.0,
    )
    
    return StrategyDecision(
        name=name,
        side=side,
        score=score,
        confidence=score,
        raw_signal={'direction': side, 'entry': 100.0},
        metadata=metadata,
    )


# ============================================================================
# TEST 1: Tier 1 - 단일 High-Confidence 선택
# ============================================================================

def test_tier1_single_high_confidence():
    """Tier 1: 단일 High-Confidence 전략 선택"""
    print("\n" + "="*60)
    print("TEST 1: Tier 1 단일 High-Confidence 선택")
    print("="*60)
    
    # Mock registry & score_engine
    mock_registry = Mock()
    mock_score_engine = Mock()
    
    aggregator = EnsembleAggregator(mock_registry, mock_score_engine)
    
    # Decisions: LONG 0.85, SHORT 0.3
    decisions = [
        create_mock_decision('scalping', 'LONG', 0.85),
        create_mock_decision('reversion', 'SHORT', 0.3),
    ]
    
    # Aggregate
    result = aggregator.aggregate(decisions, regime=None)
    
    # 검증
    assert result.side == 'LONG', f"Expected LONG, got {result.side}"
    assert result.tier == 'tier1', f"Expected tier1, got {result.tier}"
    assert result.chosen_strategy == 'scalping', f"Expected scalping, got {result.chosen_strategy}"
    assert result.confidence >= 0.8, f"Confidence too low: {result.confidence}"
    
    print(f"✅ side: {result.side}")
    print(f"✅ tier: {result.tier}")
    print(f"✅ chosen_strategy: {result.chosen_strategy}")
    print(f"✅ confidence: {result.confidence:.3f}")
    print("\n✅ TEST 1 PASSED\n")


# ============================================================================
# TEST 2: Tier 1 - 충돌 (차이 큼) → 높은 쪽 선택
# ============================================================================

def test_tier1_conflict_large_diff():
    """Tier 1: 충돌 but 차이 >= 0.15 → 높은 쪽 선택"""
    print("="*60)
    print("TEST 2: Tier 1 충돌 (차이 큼)")
    print("="*60)
    
    mock_registry = Mock()
    mock_score_engine = Mock()
    
    aggregator = EnsembleAggregator(mock_registry, mock_score_engine)
    
    # Decisions: LONG 0.9, SHORT 0.7 (차이 0.2 >= 0.15)
    decisions = [
        create_mock_decision('scalping', 'LONG', 0.9),
        create_mock_decision('reversion', 'SHORT', 0.7),
    ]
    
    result = aggregator.aggregate(decisions, regime=None)
    
    # 검증: LONG 선택
    assert result.side == 'LONG', f"Expected LONG, got {result.side}"
    assert result.tier == 'tier1', f"Expected tier1, got {result.tier}"
    assert result.confidence >= 0.8, f"Confidence too low: {result.confidence}"
    
    print(f"✅ side: {result.side}")
    print(f"✅ confidence: {result.confidence:.3f}")
    print(f"✅ reason: {result.reason}")
    print("\n✅ TEST 2 PASSED\n")


# ============================================================================
# TEST 3: Tier 1 - 충돌 (차이 작음) → NO TRADE
# ============================================================================

def test_tier1_conflict_small_diff():
    """Tier 1: 충돌 but 차이 < 0.15 → NO TRADE"""
    print("="*60)
    print("TEST 3: Tier 1 충돌 (차이 작음) → NO TRADE")
    print("="*60)
    
    mock_registry = Mock()
    mock_score_engine = Mock()
    
    aggregator = EnsembleAggregator(mock_registry, mock_score_engine)
    
    # Decisions: LONG 0.87, SHORT 0.83 (차이 0.04 < 0.15, 둘 다 >= 0.8)
    decisions = [
        create_mock_decision('scalping', 'LONG', 0.87),
        create_mock_decision('reversion', 'SHORT', 0.83),
    ]
    
    result = aggregator.aggregate(decisions, regime=None)
    
    # 검증: NO TRADE
    assert result.side is None, f"Expected None, got {result.side}"
    assert result.tier == 'skip', f"Expected skip, got {result.tier}"
    assert result.confidence == 0.0, f"Expected 0.0, got {result.confidence}"
    
    print(f"✅ side: {result.side}")
    print(f"✅ tier: {result.tier}")
    print(f"✅ reason: {result.reason}")
    print("\n✅ TEST 3 PASSED\n")


# ============================================================================
# TEST 4: Tier 2 - Consensus (LONG 2 vs SHORT 1)
# ============================================================================

def test_tier2_consensus_long():
    """Tier 2: Consensus (LONG 2개 vs SHORT 1개) → LONG 선택"""
    print("="*60)
    print("TEST 4: Tier 2 Consensus (LONG 우세)")
    print("="*60)
    
    mock_registry = Mock()
    mock_score_engine = Mock()
    
    aggregator = EnsembleAggregator(mock_registry, mock_score_engine)
    
    # Decisions: LONG 0.7, LONG 0.65, SHORT 0.55
    decisions = [
        create_mock_decision('scalping', 'LONG', 0.7),
        create_mock_decision('trend', 'LONG', 0.65),
        create_mock_decision('reversion', 'SHORT', 0.55),
    ]
    
    result = aggregator.aggregate(decisions, regime=None)
    
    # 검증: LONG 선택
    assert result.side == 'LONG', f"Expected LONG, got {result.side}"
    assert result.tier == 'tier2', f"Expected tier2, got {result.tier}"
    assert 0.5 <= result.confidence <= 1.0, f"Confidence out of range: {result.confidence}"
    assert len(result.contributing_strategies) == 2, f"Expected 2 contributors, got {len(result.contributing_strategies)}"
    
    print(f"✅ side: {result.side}")
    print(f"✅ tier: {result.tier}")
    print(f"✅ confidence: {result.confidence:.3f}")
    print(f"✅ contributors: {result.contributing_strategies}")
    print("\n✅ TEST 4 PASSED\n")


# ============================================================================
# TEST 5: Tier 2 - Consensus 실패 (동률)
# ============================================================================

def test_tier2_consensus_tie():
    """Tier 2: Consensus 실패 (LONG 1 vs SHORT 1) → NO TRADE"""
    print("="*60)
    print("TEST 5: Tier 2 Consensus 실패 (동률)")
    print("="*60)
    
    mock_registry = Mock()
    mock_score_engine = Mock()
    
    aggregator = EnsembleAggregator(mock_registry, mock_score_engine)
    
    # Decisions: LONG 0.6, SHORT 0.6 (동률)
    decisions = [
        create_mock_decision('scalping', 'LONG', 0.6),
        create_mock_decision('reversion', 'SHORT', 0.6),
    ]
    
    result = aggregator.aggregate(decisions, regime=None)
    
    # 검증: NO TRADE
    assert result.side is None, f"Expected None, got {result.side}"
    assert result.tier == 'skip', f"Expected skip, got {result.tier}"
    
    print(f"✅ side: {result.side}")
    print(f"✅ tier: {result.tier}")
    print(f"✅ reason: {result.reason}")
    print("\n✅ TEST 5 PASSED\n")


# ============================================================================
# TEST 6: Empty Decisions → Skip
# ============================================================================

def test_empty_decisions():
    """빈 Decisions 리스트 → Skip"""
    print("="*60)
    print("TEST 6: Empty Decisions → Skip")
    print("="*60)
    
    mock_registry = Mock()
    mock_score_engine = Mock()
    
    aggregator = EnsembleAggregator(mock_registry, mock_score_engine)
    
    result = aggregator.aggregate([], regime=None)
    
    # 검증
    assert result.side is None
    assert result.tier == 'skip'
    assert result.reason == 'No signals'
    
    print(f"✅ side: {result.side}")
    print(f"✅ tier: {result.tier}")
    print(f"✅ reason: {result.reason}")
    print("\n✅ TEST 6 PASSED\n")


# ============================================================================
# TEST 7: Tier 1 Unanimous (여러 전략 같은 방향)
# ============================================================================

def test_tier1_unanimous():
    """Tier 1: 여러 전략이 모두 같은 방향 → 최고 점수 선택"""
    print("="*60)
    print("TEST 7: Tier 1 Unanimous (같은 방향)")
    print("="*60)
    
    mock_registry = Mock()
    mock_score_engine = Mock()
    
    aggregator = EnsembleAggregator(mock_registry, mock_score_engine)
    
    # Decisions: LONG 0.9, LONG 0.85, LONG 0.8
    decisions = [
        create_mock_decision('scalping', 'LONG', 0.9),
        create_mock_decision('trend', 'LONG', 0.85),
        create_mock_decision('breakout', 'LONG', 0.8),
    ]
    
    result = aggregator.aggregate(decisions, regime=None)
    
    # 검증
    assert result.side == 'LONG'
    assert result.tier == 'tier1'
    assert result.chosen_strategy == 'scalping'  # 최고 점수
    assert len(result.contributing_strategies) == 3
    
    print(f"✅ side: {result.side}")
    print(f"✅ chosen_strategy: {result.chosen_strategy}")
    print(f"✅ contributors: {len(result.contributing_strategies)}")
    print("\n✅ TEST 7 PASSED\n")


# ============================================================================
# 메인 실행
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PHASE19-3 Ensemble Aggregator 테스트 시작")
    print("="*60 + "\n")
    
    test_tier1_single_high_confidence()
    test_tier1_conflict_large_diff()
    test_tier1_conflict_small_diff()
    test_tier2_consensus_long()
    test_tier2_consensus_tie()
    test_empty_decisions()
    test_tier1_unanimous()
    
    print("\n" + "="*60)
    print("✅ 모든 테스트 PASSED (7/7)")
    print("="*60 + "\n")
