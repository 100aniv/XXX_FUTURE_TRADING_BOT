#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE19-2 Score Engine 테스트
==============================
Factor Calculator & Score Engine 단위 테스트
"""
import pytest
import pandas as pd
import numpy as np
from common.ensemble import (
    compute_momentum_factor,
    compute_volatility_factor,
    compute_volume_factor,
    compute_trend_strength_factor,
    compute_overbought_oversold_factor,
    compute_breakout_probability_factor,
    compute_all_factors,
    ScoreEngine,
)
from common.registry import StrategyRegistry, StrategyMetadata


# ============================================================================
# TEST 1: Factor Calculator 기본 테스트
# ============================================================================

def test_factor_calculator_basic():
    """Factor 계산 함수들이 0~1 범위를 반환하는지 테스트"""
    print("\n" + "="*60)
    print("TEST 1: Factor Calculator 기본 테스트")
    print("="*60)
    
    # 더미 DataFrame 생성 (40개 row)
    np.random.seed(42)
    n = 40
    df = pd.DataFrame({
        'close': np.cumsum(np.random.randn(n)) + 100,
        'open': np.cumsum(np.random.randn(n)) + 100,
        'high': np.cumsum(np.random.randn(n)) + 101,
        'low': np.cumsum(np.random.randn(n)) + 99,
        'volume': np.random.randint(1000, 10000, n),
        'atr': np.random.uniform(1.0, 3.0, n),
        'ema_fast': np.cumsum(np.random.randn(n)) + 100,
        'ema_slow': np.cumsum(np.random.randn(n)) + 99,
        'rsi': np.random.uniform(20, 80, n),
        'vol_ma': np.random.randint(2000, 8000, n),
        'dc_upper': np.cumsum(np.random.randn(n)) + 102,
        'dc_lower': np.cumsum(np.random.randn(n)) + 98,
    })
    
    # 각 Factor 계산
    momentum = compute_momentum_factor(df)
    volatility = compute_volatility_factor(df)
    volume = compute_volume_factor(df)
    trend_strength = compute_trend_strength_factor(df)
    overbought_oversold = compute_overbought_oversold_factor(df)
    breakout_prob = compute_breakout_probability_factor(df)
    
    # 0~1 범위 검증
    assert 0.0 <= momentum <= 1.0, f"momentum out of range: {momentum}"
    assert 0.0 <= volatility <= 1.0, f"volatility out of range: {volatility}"
    assert 0.0 <= volume <= 1.0, f"volume out of range: {volume}"
    assert 0.0 <= trend_strength <= 1.0, f"trend_strength out of range: {trend_strength}"
    assert 0.0 <= overbought_oversold <= 1.0, f"overbought_oversold out of range: {overbought_oversold}"
    assert 0.0 <= breakout_prob <= 1.0, f"breakout_prob out of range: {breakout_prob}"
    
    print(f"✅ momentum: {momentum:.3f}")
    print(f"✅ volatility: {volatility:.3f}")
    print(f"✅ volume: {volume:.3f}")
    print(f"✅ trend_strength: {trend_strength:.3f}")
    print(f"✅ overbought_oversold: {overbought_oversold:.3f}")
    print(f"✅ breakout_probability: {breakout_prob:.3f}")
    print("\n✅ TEST 1 PASSED\n")


def test_compute_all_factors():
    """compute_all_factors()가 6개 Factor를 모두 반환하는지 테스트"""
    print("="*60)
    print("TEST 2: compute_all_factors() 통합 테스트")
    print("="*60)
    
    # 더미 DataFrame
    np.random.seed(42)
    n = 40
    df = pd.DataFrame({
        'close': np.cumsum(np.random.randn(n)) + 100,
        'open': np.cumsum(np.random.randn(n)) + 100,
        'high': np.cumsum(np.random.randn(n)) + 101,
        'low': np.cumsum(np.random.randn(n)) + 99,
        'volume': np.random.randint(1000, 10000, n),
        'atr': np.random.uniform(1.0, 3.0, n),
        'ema_fast': np.cumsum(np.random.randn(n)) + 100,
        'ema_slow': np.cumsum(np.random.randn(n)) + 99,
        'rsi': np.random.uniform(20, 80, n),
        'vol_ma': np.random.randint(2000, 8000, n),
        'dc_upper': np.cumsum(np.random.randn(n)) + 102,
        'dc_lower': np.cumsum(np.random.randn(n)) + 98,
    })
    
    factors = compute_all_factors(df)
    
    # 6개 key 존재 확인
    expected_keys = [
        "momentum",
        "volatility",
        "volume",
        "trend_strength",
        "overbought_oversold",
        "breakout_probability",
    ]
    
    for key in expected_keys:
        assert key in factors, f"Missing key: {key}"
        assert 0.0 <= factors[key] <= 1.0, f"{key} out of range: {factors[key]}"
        print(f"✅ {key}: {factors[key]:.3f}")
    
    print("\n✅ TEST 2 PASSED\n")


# ============================================================================
# TEST 3: ScoreEngine 테스트
# ============================================================================

def test_score_engine_basic():
    """ScoreEngine.compute_strategy_score() 기본 동작 테스트"""
    print("="*60)
    print("TEST 3: ScoreEngine 기본 동작")
    print("="*60)
    
    # 가짜 metadata 생성
    metadata = StrategyMetadata(
        strategy_name='test',
        strategy_type='test',
        optimal_regime='trending',
        worst_regime='ranging',
        base_weight=1.0,
        factor_weights={
            'momentum': 0.4,
            'trend_strength': 0.3,
            'volume': 0.2,
            'volatility': 0.1,
        }
    )
    
    # 가짜 factors (중립)
    factors = {
        'momentum': 0.5,
        'volatility': 0.5,
        'volume': 0.5,
        'trend_strength': 0.5,
        'overbought_oversold': 0.0,
        'breakout_probability': 0.0,
    }
    
    engine = ScoreEngine()
    
    # Regime = None (중립)
    score_neutral = engine.compute_strategy_score(metadata, factors, regime=None)
    print(f"✅ Score (regime=None): {score_neutral:.3f}")
    assert 0.0 <= score_neutral <= 1.0, f"Score out of range: {score_neutral}"
    
    # Optimal regime
    score_optimal = engine.compute_strategy_score(metadata, factors, regime='trending')
    print(f"✅ Score (optimal='trending'): {score_optimal:.3f}")
    assert score_optimal > score_neutral, "Optimal regime should boost score"
    
    # Worst regime
    score_worst = engine.compute_strategy_score(metadata, factors, regime='ranging')
    print(f"✅ Score (worst='ranging'): {score_worst:.3f}")
    assert score_worst < score_neutral, "Worst regime should reduce score"
    
    # 순서 확인
    assert score_optimal > score_neutral > score_worst, "Score order: optimal > neutral > worst"
    
    print("\n✅ TEST 3 PASSED\n")


def test_score_engine_factor_weights():
    """Factor weights가 점수에 올바르게 반영되는지 테스트"""
    print("="*60)
    print("TEST 4: ScoreEngine Factor Weight 반영")
    print("="*60)
    
    # momentum에 높은 가중치
    metadata_momentum = StrategyMetadata(
        strategy_name='test_momentum',
        strategy_type='test',
        base_weight=1.0,
        factor_weights={'momentum': 1.0}  # 100% momentum
    )
    
    # trend_strength에 높은 가중치
    metadata_trend = StrategyMetadata(
        strategy_name='test_trend',
        strategy_type='test',
        base_weight=1.0,
        factor_weights={'trend_strength': 1.0}  # 100% trend
    )
    
    # momentum 높음, trend_strength 낮음
    factors_momentum_high = {
        'momentum': 0.9,
        'trend_strength': 0.1,
        'volatility': 0.5,
        'volume': 0.5,
        'overbought_oversold': 0.5,
        'breakout_probability': 0.5,
    }
    
    engine = ScoreEngine()
    
    score_momentum = engine.compute_strategy_score(metadata_momentum, factors_momentum_high)
    score_trend = engine.compute_strategy_score(metadata_trend, factors_momentum_high)
    
    print(f"✅ Score (momentum-focused): {score_momentum:.3f}")
    print(f"✅ Score (trend-focused): {score_trend:.3f}")
    
    # momentum 가중치 전략이 더 높은 점수를 받아야 함
    assert score_momentum > score_trend, "Momentum-focused should score higher with high momentum factor"
    
    print("\n✅ TEST 4 PASSED\n")


# ============================================================================
# TEST 5: 실제 전략 metadata 테스트
# ============================================================================

def test_real_strategy_metadata():
    """실제 전략의 metadata가 올바르게 세팅되었는지 테스트"""
    print("="*60)
    print("TEST 5: 실제 전략 Metadata 검증")
    print("="*60)
    
    registry = StrategyRegistry()
    count = registry.scan()
    
    print(f"📊 등록된 전략: {count}개")
    assert count == 7, f"Expected 7 strategies, got {count}"
    
    # 각 전략의 metadata 검증
    for name in registry.list_strategies():
        metadata = registry.get_metadata(name)
        
        # PHASE19-2 필드 존재 확인
        assert metadata.optimal_regime is not None, f"{name}: optimal_regime is None"
        assert metadata.worst_regime is not None, f"{name}: worst_regime is None"
        assert metadata.base_weight > 0, f"{name}: base_weight <= 0"
        assert len(metadata.factor_weights) > 0, f"{name}: factor_weights is empty"
        
        # factor_weights 합계 확인 (0~1 범위, 일부 전략은 합이 1.0 아닐 수 있음)
        total_weight = sum(metadata.factor_weights.values())
        
        print(f"  ✅ {name}: optimal={metadata.optimal_regime}, worst={metadata.worst_regime}, "
              f"base_weight={metadata.base_weight}, factor_sum={total_weight:.2f}")
    
    print("\n✅ TEST 5 PASSED\n")


def test_real_strategy_score_calculation():
    """실제 전략으로 Score 계산 통합 테스트"""
    print("="*60)
    print("TEST 6: 실제 전략 Score 계산")
    print("="*60)
    
    registry = StrategyRegistry()
    registry.scan()
    
    # scalping 전략 가져오기
    scalping_meta = registry.get_metadata('scalping')
    
    # 가짜 factors (trending 시장 가정)
    factors_trending = {
        'momentum': 0.8,
        'trend_strength': 0.9,
        'volume': 0.7,
        'volatility': 0.6,
        'overbought_oversold': 0.2,
        'breakout_probability': 0.3,
    }
    
    engine = ScoreEngine()
    
    # Trending (optimal for scalping)
    score_trending = engine.compute_strategy_score(scalping_meta, factors_trending, regime='trending')
    print(f"✅ scalping Score (trending): {score_trending:.3f}")
    
    # Ranging (worst for scalping)
    score_ranging = engine.compute_strategy_score(scalping_meta, factors_trending, regime='ranging')
    print(f"✅ scalping Score (ranging): {score_ranging:.3f}")
    
    # Trending이 더 높아야 함
    assert score_trending > score_ranging, "Scalping should score higher in trending"
    
    # 0~1 범위
    assert 0.0 <= score_trending <= 1.0
    assert 0.0 <= score_ranging <= 1.0
    
    print("\n✅ TEST 6 PASSED\n")


# ============================================================================
# 메인 실행
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PHASE19-2 Score Engine 테스트 시작")
    print("="*60 + "\n")
    
    test_factor_calculator_basic()
    test_compute_all_factors()
    test_score_engine_basic()
    test_score_engine_factor_weights()
    test_real_strategy_metadata()
    test_real_strategy_score_calculation()
    
    print("\n" + "="*60)
    print("✅ 모든 테스트 PASSED (6/6)")
    print("="*60 + "\n")
