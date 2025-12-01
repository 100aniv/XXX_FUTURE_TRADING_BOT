# PHASE23-3: Ensemble Orchestrator V2 - Design Document

**Date**: 2025-12-01  
**Status**: 🔄 IN PROGRESS  
**Phase**: PHASE23-3 – Ensemble Orchestrator V2  
**Purpose**: Implement Score V2-based ensemble decision logic with diversity constraints

---

## 1. Objective

### 1.1 Goals

**Primary Objectives**:
1. **Score V2 Integration**: Consume `S_LONG`, `S_SHORT`, `S_RISK`, `S_QUALITY` from strategies
2. **3-Tier Decision Logic**: High-Confidence / Consensus / Skip based on Score V2
3. **Dominant Strategy Prevention**: Limit any single strategy's contribution via `max_strategy_weight`
4. **Engine Integration**: Seamless integration with `engine.run_v2()` ensemble mode
5. **Validation**: Unit Tests + 1H PAPER smoke test

**Background**:
- PHASE23-2: All 5 strategies now return Score V2 fields (`S_LONG`, `S_SHORT`, `S_RISK`, `S_QUALITY`)
- PHASE19: Ensemble infrastructure exists but uses Factor-based single score
- Problem: Current `EnsembleAggregator` doesn't leverage Score V2 directional signals

**Key Requirements**:
- Must work with existing `BaseStrategy` interface
- Config-driven thresholds and weights
- No breaking changes to PHASE23-1 single-strategy mode

---

## 2. AS-IS Analysis

### 2.1 Current Architecture (PHASE19)

**Components**:
```
common/ensemble/
├── score_engine.py       # Factor → single score (0~1)
├── aggregator.py         # 3-Tier logic (tier1/tier2/skip)
└── factors.py            # 6 market factors calculation
```

**Data Flow**:
```
Strategy.compute_signal(df)
    ↓
Signal (direction, entry, sl, tp)
    ↓
compute_all_factors(df) → FactorDict
    ↓
ScoreEngine.compute_strategy_score(metadata, factors, regime)
    ↓
score = base_weight × regime_mult × Σ(factor_weights[i] × factors[i])
    ↓
EnsembleAggregator.aggregate(decisions)
    ↓
3-Tier logic → EnsembleDecision
```

**Key Classes**:

**ScoreEngine**:
- Input: `StrategyMetadata`, `FactorDict`, `regime`
- Output: `score` (0~1, single value)
- Logic: `Σ(factor_weight × factor_value) × base_weight × regime_multiplier`

**EnsembleAggregator**:
- Input: List[`StrategyDecision`]
- Output: `EnsembleDecision`
- Logic:
  - Tier 1: Any `score >= 0.8` → immediate execution
  - Tier 2: `2+ votes` with `0.5 <= score < 0.8` → consensus
  - Tier 3: Otherwise → skip

**StrategyDecision**:
```python
@dataclass
class StrategyDecision:
    name: str
    side: 'LONG' | 'SHORT' | None
    score: float                     # ⚠️ single score, no direction
    confidence: float
    raw_signal: Any
    metadata: StrategyMetadata
```

**EnsembleDecision**:
```python
@dataclass
class EnsembleDecision:
    side: 'LONG' | 'SHORT' | None
    confidence: float
    chosen_strategy: str | None
    contributing_strategies: List[str]
    tier: 'tier1' | 'tier2' | 'skip'
    decisions: List[StrategyDecision]
    regime: str | None
    reason: str
```

### 2.2 Limitations

**Problem 1: No Directional Scores**:
- Current `score` is direction-agnostic (0~1)
- Can't distinguish between "strong LONG" vs "strong SHORT"
- Tier logic relies on `side` field from raw signal, not score

**Problem 2: No Dominant Strategy Prevention**:
- If scalping has `score=0.9` and others have `score=0.2`, scalping dominates 100%
- No diversity constraint (`max_strategy_weight`)

**Problem 3: Score V2 Ignored**:
- Strategies return `S_LONG`, `S_SHORT`, `S_RISK`, `S_QUALITY` (PHASE23-2)
- But `EnsembleAggregator` doesn't consume these fields
- Factor-based score is still used

---

## 3. TO-BE Design

### 3.1 Core Principles

1. **Score V2 as Primary Signal**: Use `S_LONG`, `S_SHORT` instead of Factor-based score
2. **Net Score Calculation**: `S_NET = S_LONG - S_SHORT` (directional signal strength)
3. **Weighted Aggregation**: `ensemble_net = Σ(weight[i] × S_NET[i])`
4. **Diversity Constraint**: Limit any strategy's contribution to ≤ `max_strategy_weight` (e.g., 60%)
5. **Risk/Quality Filters**: Use `S_RISK`, `S_QUALITY` to filter or adjust scores

### 3.2 Score V2 Structure (Review)

**From each strategy's `compute_signal()` output**:
```python
{
    'side': 'LONG' | 'SHORT' | None,
    'action': '진입' | None,
    'entry': float,
    'sl': float,
    'tp': float,
    'reason': List[str],
    
    # Score V2 fields (PHASE23-2):
    'S_LONG': float,   # LONG signal strength [0.0, 1.0]
    'S_SHORT': float,  # SHORT signal strength [0.0, 1.0]
    'S_RISK': float,   # Risk score [0.0, 1.0] (higher = riskier)
    'S_QUALITY': float # Signal quality [0.0, 1.0] (higher = more confident)
}
```

**Derived Fields**:
```python
S_NET = S_LONG - S_SHORT        # [-1.0, 1.0] directional strength
S_ABS = S_LONG + S_SHORT        # [0.0, 2.0] total signal strength
S_DIR = 'LONG' if S_NET > 0 else 'SHORT' if S_NET < 0 else None
```

### 3.3 ScoreEngine V2

**Goal**: Extract Score V2 components from strategy signals, optionally blend with Factor-based score.

**New Method**:
```python
def compute_strategy_score_v2(
    self,
    signal: Dict[str, Any],
    metadata: StrategyMetadata,
    factors: FactorDict | None = None,
    regime: str | None = None,
    mode: str = 'score_v2'  # 'score_v2' | 'factor' | 'hybrid'
) -> ScoreComponentsV2:
    """
    Score V2 계산
    
    Args:
        signal: Strategy의 compute_signal() 결과
        metadata: 전략 메타데이터
        factors: (Optional) Factor dict
        regime: 현재 Regime
        mode: 'score_v2' (Score V2만), 'factor' (Factor만), 'hybrid' (혼합)
    
    Returns:
        ScoreComponentsV2
    """
```

**ScoreComponentsV2 Dataclass**:
```python
@dataclass
class ScoreComponentsV2:
    S_LONG: float       # [0.0, 1.0]
    S_SHORT: float      # [0.0, 1.0]
    S_NET: float        # [-1.0, 1.0]
    S_ABS: float        # [0.0, 2.0]
    S_RISK: float       # [0.0, 1.0]
    S_QUALITY: float    # [0.0, 1.0]
    S_DIR: str | None   # 'LONG' | 'SHORT' | None
```

**Computation Logic** (`mode='score_v2'`):
1. Extract `S_LONG`, `S_SHORT`, `S_RISK`, `S_QUALITY` from signal
2. Calculate derived fields: `S_NET`, `S_ABS`, `S_DIR`
3. Apply regime multiplier to `S_NET` (optional)
4. Return `ScoreComponentsV2`

**Hybrid Mode** (`mode='hybrid'`):
- Blend Score V2 with Factor-based score
- Example: `S_NET = 0.7 × (S_LONG - S_SHORT) + 0.3 × factor_score`

### 3.4 EnsembleAggregator V2

**Goal**: Aggregate Score V2 components into ensemble decision with diversity constraints.

**New Method**:
```python
def aggregate_v2(
    self,
    decisions_v2: List[StrategyDecisionV2],
    config: Dict[str, Any],
    regime: str | None = None
) -> EnsembleDecisionV2:
    """
    Score V2 기반 3-Tier 통합
    
    Args:
        decisions_v2: List[StrategyDecisionV2]
        config: Ensemble config (thresholds, weights, caps)
        regime: 현재 Regime
    
    Returns:
        EnsembleDecisionV2
    """
```

**StrategyDecisionV2**:
```python
@dataclass
class StrategyDecisionV2:
    name: str
    score_v2: ScoreComponentsV2
    raw_signal: Dict[str, Any]
    metadata: StrategyMetadata
    weight: float = 1.0  # 전략 가중치 (config에서 설정)
```

**EnsembleDecisionV2**:
```python
@dataclass
class EnsembleDecisionV2:
    side: 'LONG' | 'SHORT' | None
    action: '진입' | 'EXIT' | 'HOLD'
    entry: float | None
    sl: float | None
    tp: float | None
    reason: List[str]
    
    # Ensemble meta
    strategy_votes: Dict[str, float]  # {strategy_name: net_score}
    dominant_strategies: List[str]     # strategies with >max_weight contribution
    tier: 'tier1' | 'tier2' | 'skip'
    confidence: float
    
    # Aggregated scores
    agg_S_LONG: float
    agg_S_SHORT: float
    agg_S_NET: float
    agg_S_RISK: float
    agg_S_QUALITY: float
    
    # Original
    decisions: List[StrategyDecisionV2]
    regime: str | None
```

**3-Tier Logic V2**:

**Tier 1: High-Confidence** (any `abs(S_NET) >= high_conf_threshold`):
```python
high_conf_threshold = config.get('ensemble.high_conf_threshold', 0.7)

# Check for high-confidence signals
high_conf_decisions = [d for d in decisions_v2 if abs(d.score_v2.S_NET) >= high_conf_threshold]

if high_conf_decisions:
    # Select best signal (highest abs(S_NET))
    best = max(high_conf_decisions, key=lambda x: abs(x.score_v2.S_NET))
    
    # Check dominant strategy cap
    if _check_dominance(best, high_conf_decisions, max_strategy_weight):
        return Ensemble_DECISION(side=best.score_v2.S_DIR, tier='tier1', ...)
    else:
        # Skip due to dominance
        return EnsembleDecision(side=None, tier='skip', reason='dominance violation')
```

**Tier 2: Consensus** (`2+ strategies`, weighted average `>= consensus_threshold`):
```python
consensus_threshold = config.get('ensemble.consensus_threshold', 0.4)
min_strategies = config.get('ensemble.min_strategies', 2)

# Calculate weighted average
total_weight = sum(d.weight for d in decisions_v2)
weighted_net = sum(d.weight × d.score_v2.S_NET for d in decisions_v2) / total_weight

if abs(weighted_net) >= consensus_threshold:
    # Check strategy diversity
    if _count_agreeing_strategies(decisions_v2, direction) >= min_strategies:
        # Check dominance
        if not _has_dominant_strategy(decisions_v2, max_strategy_weight):
            return EnsembleDecision(
                side='LONG' if weighted_net > 0 else 'SHORT',
                tier='tier2',
                ...
            )
```

**Tier 3: Skip** (otherwise):
```python
return EnsembleDecision(side=None, tier='skip', reason='no consensus')
```

**Dominant Strategy Prevention**:
```python
def _check_dominance(
    decisions_v2: List[StrategyDecisionV2],
    max_strategy_weight: float = 0.6
) -> Tuple[bool, List[str]]:
    """
    Check if any strategy dominates (contribution > max_strategy_weight)
    
    Returns:
        (is_valid, dominant_strategies)
    """
    total_abs_net = sum(abs(d.score_v2.S_NET × d.weight) for d in decisions_v2)
    
    dominant = []
    for d in decisions_v2:
        contribution = abs(d.score_v2.S_NET × d.weight) / total_abs_net
        if contribution > max_strategy_weight:
            dominant.append(d.name)
    
    return (len(dominant) == 0, dominant)
```

### 3.5 Config Structure

**Config Example** (`configs/ensemble/ensemble_v2.yml`):
```yaml
ensemble:
  enabled: true
  mode: 'score_v2'  # 'score_v2' | 'factor' | 'hybrid'
  
  # Thresholds
  high_conf_threshold: 0.7      # Tier 1 threshold (abs(S_NET))
  consensus_threshold: 0.4      # Tier 2 threshold (weighted avg)
  min_strategies: 2             # Tier 2 minimum agreeing strategies
  
  # Diversity Constraints
  max_strategy_weight: 0.6      # Max contribution from single strategy (60%)
  
  # Risk/Quality Filters
  max_risk: 0.8                 # Skip if agg_S_RISK > 0.8
  min_quality: 0.3              # Skip if agg_S_QUALITY < 0.3
  
  # Strategy Weights
  strategy_weights:
    scalping: 1.0
    volatility_breakout_v2: 1.0
    mean_reversion_v2: 1.0
    trend_follow_v2: 1.0
    volume_based_v2: 1.0
```

---

## 4. Implementation Plan

### 4.1 File Changes

**New Files**:
- `common/ensemble/score_engine_v2.py`: ScoreEngine V2 implementation
- `common/ensemble/aggregator_v2.py`: EnsembleAggregator V2 implementation
- `tests/test_phase23_3_ensemble_orchestrator_v2.py`: Unit tests

**Modified Files**:
- `execution/engine.py`: Integrate V2 orchestrator in ensemble mode
- `common/ensemble/__init__.py`: Export V2 classes

### 4.2 Implementation Steps

1. **ScoreEngine V2** (`score_engine_v2.py`):
   - Define `ScoreComponentsV2` dataclass
   - Implement `compute_strategy_score_v2()` method
   - Handle `mode='score_v2'` (primary)

2. **EnsembleAggregator V2** (`aggregator_v2.py`):
   - Define `StrategyDecisionV2`, `EnsembleDecisionV2` dataclasses
   - Implement `aggregate_v2()` with 3-Tier logic V2
   - Implement `_check_dominance()` helper
   - Implement weighted aggregation logic

3. **Engine Integration** (`execution/engine.py`):
   - Add `_run_ensemble_v2()` helper in `run_v2()`
   - Load ensemble config from `config.get('ensemble', {})`
   - Call `EnsembleAggregatorV2.aggregate_v2()` when `ensemble.mode == 'score_v2'`
   - Convert `EnsembleDecisionV2` → signal dict for execution

4. **Unit Tests** (`test_phase23_3_ensemble_orchestrator_v2.py`):
   - Test Tier 1 (high-confidence LONG/SHORT)
   - Test Tier 2 (consensus)
   - Test Tier 3 (skip)
   - Test dominance prevention
   - Test risk/quality filtering

5. **PAPER Smoke Test** (1H):
   - Create `configs/paper/phase23_3_ensemble_v2_smoke.yml`
   - Run with `scripts/run_v2.py` for 1H
   - Verify ensemble decisions logged
   - Verify no crashes/errors

---

## 5. Success Criteria

**Code Quality**:
- [ ] `ScoreEngine V2` extracts Score V2 components from signals
- [ ] `EnsembleAggregator V2` implements 3-Tier logic with Score V2
- [ ] Dominant strategy prevention works (max_strategy_weight cap)
- [ ] Risk/Quality filtering implemented

**Testing**:
- [ ] Unit Tests: ≥10 test cases, all PASS
- [ ] PAPER Smoke Test: 1H run, 0 errors, ensemble decisions logged

**Documentation**:
- [ ] Design doc (this file) complete
- [ ] Implementation doc (`PHASE23-3_ENSEMBLE_ORCHESTRATOR_V2.md`) created
- [ ] PHASE_ROADMAP.md updated (23-3: COMPLETE)

**Integration**:
- [ ] `engine.run_v2()` uses V2 orchestrator in ensemble mode
- [ ] Single-strategy mode unaffected (PHASE23-1 compatibility)
- [ ] Config-driven (no hardcoded thresholds)

---

**Status**: 🟡 Design Complete, Implementation Pending  
**Next**: Implement `ScoreEngine V2` + `EnsembleAggregator V2`
