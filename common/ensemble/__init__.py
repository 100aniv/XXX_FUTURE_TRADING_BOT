#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ensemble System
===============
PHASE19-2: Factor Calculator & Score Engine
PHASE19-3: Ensemble Signal Aggregator
PHASE23-3: Score V2-based Ensemble Orchestrator

앙상블 트레이딩을 위한 팩터 계산, 전략 점수화 및 신호 통합 모듈
"""
from .factors import (
    FactorDict,
    compute_momentum_factor,
    compute_volatility_factor,
    compute_volume_factor,
    compute_trend_strength_factor,
    compute_overbought_oversold_factor,
    compute_breakout_probability_factor,
    compute_all_factors,
)
from .score_engine import ScoreEngine
from .aggregator import (
    StrategyDecision,
    EnsembleDecision,
    EnsembleAggregator,
)

# PHASE23-3: V2 Components
from .score_engine_v2 import (
    ScoreComponentsV2,
    ScoreEngineV2,
    ScoreMode,
)
from .aggregator_v2 import (
    StrategyDecisionV2,
    EnsembleDecisionV2,
    EnsembleAggregatorV2,
)

__all__ = [
    # Factors
    "FactorDict",
    "compute_momentum_factor",
    "compute_volatility_factor",
    "compute_volume_factor",
    "compute_trend_strength_factor",
    "compute_overbought_oversold_factor",
    "compute_breakout_probability_factor",
    "compute_all_factors",
    # V1 (PHASE19)
    "ScoreEngine",
    "StrategyDecision",
    "EnsembleDecision",
    "EnsembleAggregator",
    # V2 (PHASE23-3)
    "ScoreComponentsV2",
    "ScoreEngineV2",
    "ScoreMode",
    "StrategyDecisionV2",
    "EnsembleDecisionV2",
    "EnsembleAggregatorV2",
]
