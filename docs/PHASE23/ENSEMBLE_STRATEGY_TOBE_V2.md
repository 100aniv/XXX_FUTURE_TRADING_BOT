# Ensemble Strategy TO-BE V2

**Date**: 2025-11-29  
**Status**: 🔄 IN PROGRESS  
**Phase**: PHASE23-0 – Ensemble Strategy Design  
**Purpose**: Define 5-family ensemble strategy framework and scoring structure

---

## 1. Overview

### 1.1 Objective

**Purpose**:
- Define a **5-family ensemble framework** based on PHASE22-0 strategy reconstruction
- Establish **Ensemble Score V2 structure** for unified strategy scoring
- Design **config-driven ensemble control** for easy parameter tuning
- Prepare foundation for **PHASE24 ensemble integration and PHASE25 tuning**

**Background**:
- PHASE22-0: Defined 5 strategy families (HF Momentum, Volatility Breakout, Mean Reversion, Trend Following, Volume-Based)
- PHASE22-1: Implemented 4 new strategies (research/) + kept scalping_v3 (core/)
- PHASE22-2: 12H ensemble test produced 0 trades (threshold + config issues)
- PHASE22-4: Config propagation broken in runtime (architectural issue)
- PHASE23-0: TO-BE architecture established (single-engine-centric)

**Key Principles**:
1. **Complementarity**: Each family targets different market regimes
2. **Diversity**: Different timeframes, indicators, and signal types
3. **Scalability**: Easy to add/remove strategies within families
4. **Tunability**: All weights, thresholds, and params in config

---

## 2. Five Strategy Families

### 2.1 Family 1: High-Frequency Momentum

**Representative Strategy**: `scalping_v3` (core/)

**Characteristics**:
- **Timeframe**: 3m
- **Frequency**: ACTIVE (high-frequency signals)
- **Signal Type**: Momentum (RSI + EMA + Volume)
- **Market Regime**: Trending (short bursts)
- **Status**: ✅ IMPLEMENTED & VALIDATED (PHASE21)

**Signal Logic**:
- **Entry Long**: RSI oversold + EMA cross up + Volume spike
- **Entry Short**: RSI overbought + EMA cross down + Volume spike
- **Exit**: TP/SL or opposite signal

**Key Parameters**:
```yaml
scalping:
  params:
    timeframe: 3m
    rsi_oversold: 45          # Default: 30 (relaxed in PHASE22-3)
    rsi_overbought: 55        # Default: 70 (relaxed in PHASE22-3)
    ema_fast: 9
    ema_slow: 21
    volume_mult: 1.5
    momentum_enabled: false   # Higher-low / lower-high pattern
    volume_required: false    # Volume confirmation required
```

**Metadata** (PHASE23-2 migration target):
```python
StrategyMetadata(
    strategy_name='scalping',
    strategy_type='momentum',
    supported_symbols=['BTCUSDT'],
    supported_timeframes=['3m', '5m'],
    version='v3.0',
    optimal_regime='trending_short',
    worst_regime='low_volatility',
    base_weight=1.0,
    factor_weights={
        'momentum': 0.4,
        'volume': 0.3,
        'trend_strength': 0.3,
    }
)
```

**Role in Ensemble**:
- **Primary**: Capture short-term momentum bursts
- **Complementary**: Provides high-frequency signals when other strategies are idle
- **Risk**: Can overtrade in choppy markets (needs cooldown)

---

### 2.2 Family 2: Volatility Breakout

**Representative Strategy**: `volatility_breakout_v2` (research/)

**Characteristics**:
- **Timeframe**: 15m
- **Frequency**: LOW_FREQ (low-frequency signals)
- **Signal Type**: Volatility breakout (ATR + Bollinger Bands)
- **Market Regime**: Volatile / breakout
- **Status**: ✅ IMPLEMENTED (PHASE22-1), ⏳ NOT RUNTIME-VALIDATED

**Signal Logic**:
- **Entry Long**: Price breaks above upper BB + ATR expansion + Volume > avg
- **Entry Short**: Price breaks below lower BB + ATR expansion + Volume > avg
- **Exit**: TP/SL or volatility contraction

**Key Parameters**:
```yaml
volatility_breakout_v2:
  params:
    timeframe: 15m
    atr_period: 14
    atr_mult: 2.0             # Breakout threshold (ATR multiplier)
    bb_period: 20
    bb_std: 2.0
    volume_mult: 1.2          # Volume confirmation
    min_volatility: 0.02      # Minimum ATR% to consider signal
```

**Metadata**:
```python
StrategyMetadata(
    strategy_name='volatility_breakout_v2',
    strategy_type='breakout',
    supported_symbols=['BTCUSDT'],
    supported_timeframes=['15m', '1h'],
    version='v2.0',
    optimal_regime='volatile_breakout',
    worst_regime='low_volatility',
    base_weight=0.8,
    factor_weights={
        'volatility': 0.5,
        'breakout_probability': 0.3,
        'volume': 0.2,
    }
)
```

**Role in Ensemble**:
- **Primary**: Capture high-volatility breakout moves
- **Complementary**: Active when scalping/reversion are less effective (volatile regimes)
- **Risk**: False breakouts in ranging markets

---

### 2.3 Family 3: Mean Reversion

**Representative Strategy**: `mean_reversion_v2` (research/)

**Characteristics**:
- **Timeframe**: 5m
- **Frequency**: LOW_FREQ
- **Signal Type**: Mean reversion (Bollinger Bands + RSI)
- **Market Regime**: Ranging / sideways
- **Status**: ✅ IMPLEMENTED (PHASE22-1), ⏳ NOT RUNTIME-VALIDATED

**Signal Logic**:
- **Entry Long**: Price touches lower BB + RSI oversold + Distance from mean > threshold
- **Entry Short**: Price touches upper BB + RSI overbought + Distance from mean > threshold
- **Exit**: Price returns to middle BB or TP/SL

**Key Parameters**:
```yaml
mean_reversion_v2:
  params:
    timeframe: 5m
    bb_period: 20
    bb_std: 2.0
    rsi_period: 14
    rsi_oversold: 30
    rsi_overbought: 70
    mean_distance_mult: 1.5   # How far from mean to trigger (BB width multiplier)
    exit_mean_pct: 0.5        # Exit when 50% back to mean
```

**Metadata**:
```python
StrategyMetadata(
    strategy_name='mean_reversion_v2',
    strategy_type='reversion',
    supported_symbols=['BTCUSDT'],
    supported_timeframes=['5m', '15m'],
    version='v2.0',
    optimal_regime='ranging',
    worst_regime='strong_trend',
    base_weight=0.8,
    factor_weights={
        'overbought_oversold': 0.4,
        'volatility': 0.3,
        'trend_strength': -0.3,  # Negative: better when trend is weak
    }
)
```

**Role in Ensemble**:
- **Primary**: Profit from mean reversion in ranging markets
- **Complementary**: Active when trend strategies are weak
- **Risk**: Losses in strong trends (needs regime filter)

---

### 2.4 Family 4: Trend Following

**Representative Strategy**: `trend_follow_v2` (research/)

**Characteristics**:
- **Timeframe**: 1h
- **Frequency**: LOW_FREQ
- **Signal Type**: Trend following (EMA + ADX)
- **Market Regime**: Strong trend
- **Status**: ✅ IMPLEMENTED (PHASE22-1), ⏳ NOT RUNTIME-VALIDATED

**Signal Logic**:
- **Entry Long**: EMA cross up + ADX > threshold + Price > EMA
- **Entry Short**: EMA cross down + ADX > threshold + Price < EMA
- **Exit**: EMA cross opposite or ADX drops below threshold

**Key Parameters**:
```yaml
trend_follow_v2:
  params:
    timeframe: 1h
    ema_fast: 12
    ema_slow: 26
    adx_period: 14
    adx_threshold: 25         # Minimum ADX to consider trend strong
    trailing_stop_mult: 2.0   # ATR multiplier for trailing stop
```

**Metadata**:
```python
StrategyMetadata(
    strategy_name='trend_follow_v2',
    strategy_type='trend',
    supported_symbols=['BTCUSDT'],
    supported_timeframes=['1h', '4h'],
    version='v2.0',
    optimal_regime='strong_trend',
    worst_regime='ranging',
    base_weight=1.0,
    factor_weights={
        'trend_strength': 0.6,
        'momentum': 0.3,
        'volatility': 0.1,
    }
)
```

**Role in Ensemble**:
- **Primary**: Capture long-term trend moves
- **Complementary**: Provides stability in strong trends
- **Risk**: Whipsaws in choppy markets (needs ADX filter)

---

### 2.5 Family 5: Volume-Based

**Representative Strategy**: `volume_based_v2` (research/)

**Characteristics**:
- **Timeframe**: 5m
- **Frequency**: LOW_FREQ
- **Signal Type**: Volume spike + price action
- **Market Regime**: High volume events (news, breakouts)
- **Status**: ✅ IMPLEMENTED (PHASE22-1), ⏳ NOT RUNTIME-VALIDATED

**Signal Logic**:
- **Entry Long**: Volume spike (>2x avg) + Price closes near high + Bullish candle
- **Entry Short**: Volume spike (>2x avg) + Price closes near low + Bearish candle
- **Exit**: Volume drops below avg or TP/SL

**Key Parameters**:
```yaml
volume_based_v2:
  params:
    timeframe: 5m
    volume_mult: 2.0          # Volume spike threshold (relative to avg)
    candle_body_ratio: 0.6    # Min candle body / total range
    close_position_ratio: 0.8 # Close near high/low for long/short
    follow_through_bars: 2    # Wait N bars for follow-through
```

**Metadata**:
```python
StrategyMetadata(
    strategy_name='volume_based_v2',
    strategy_type='volume',
    supported_symbols=['BTCUSDT'],
    supported_timeframes=['5m', '15m'],
    version='v2.0',
    optimal_regime='high_volume_event',
    worst_regime='low_volume',
    base_weight=0.7,
    factor_weights={
        'volume': 0.6,
        'momentum': 0.3,
        'breakout_probability': 0.1,
    }
)
```

**Role in Ensemble**:
- **Primary**: Capture volume-driven moves (news events, large orders)
- **Complementary**: Provides alpha during unusual volume events
- **Risk**: False signals from volume spikes without follow-through

---

## 3. Ensemble Score V2 Structure

### 3.1 Strategy-Level Output

**Goal**: Each strategy outputs a **standardized signal dict** for ensemble aggregation.

**Signal Dict Structure** (TO-BE):
```python
{
    'side': 'LONG' | 'SHORT' | None,
    'action': '진입' | None,
    'entry': float,
    'sl': float,
    'tp': float,
    'lev': int,
    'reason': List[str],
    
    # Ensemble Score Components (PHASE24 addition):
    'S_LONG': float,   # Long signal strength [0.0, 1.0]
    'S_SHORT': float,  # Short signal strength [0.0, 1.0]
    'S_RISK': float,   # Risk score [0.0, 1.0] (lower = safer)
    'S_QUALITY': float # Signal quality [0.0, 1.0] (higher = more confident)
}
```

**Score Calculation** (Strategy-level):
- **S_LONG**: Aggregated long indicators (RSI, EMA, Volume, etc.)
  - Example (scalping): `S_LONG = 0.3 * (RSI < oversold) + 0.3 * (EMA cross) + 0.4 * (Volume spike)`
- **S_SHORT**: Aggregated short indicators
- **S_RISK**: Based on volatility, position size, market conditions
  - Example: `S_RISK = 1.0 - min(1.0, current_ATR / historical_avg_ATR)`
- **S_QUALITY**: Confidence in signal (number of confirming indicators)
  - Example: `S_QUALITY = (num_confirming_indicators / total_indicators)`

**Implementation Note**:
- PHASE23-2: Add score calculation to each strategy's `compute_signal()` method
- PHASE24: Use scores for ensemble aggregation

### 3.2 Ensemble-Level Decision Logic

**Goal**: Combine individual strategy scores into a unified trading decision.

**3-Tier Decision Framework**:

```
┌──────────────────────────────────────────────────────────────┐
│                      Tier 1: High-Confidence                 │
│  - ANY strategy score > tier1_threshold (e.g., 0.8)          │
│  - Action: Execute immediately (high conviction)             │
│  - Example: Scalping S_LONG=0.9 → GO LONG                    │
└──────────────────────────────────────────────────────────────┘
                              ↓ (if no Tier1)
┌──────────────────────────────────────────────────────────────┐
│                      Tier 2: Consensus                       │
│  - Multiple strategies (≥2) agree on direction               │
│  - Weighted average score > tier2_threshold (e.g., 0.5)      │
│  - Action: Execute if consensus strong enough                │
│  - Example: Breakout S_LONG=0.6 + Reversion S_LONG=0.5      │
│            → Weighted avg = 0.55 → GO LONG                   │
└──────────────────────────────────────────────────────────────┘
                              ↓ (if no Tier2)
┌──────────────────────────────────────────────────────────────┐
│                      Tier 3: Skip                            │
│  - No strong individual signal, no consensus                 │
│  - Action: No trade                                          │
└──────────────────────────────────────────────────────────────┘
```

**Weighted Average Calculation**:
```python
# For LONG direction:
weighted_long = sum(strategy_weight[i] * S_LONG[i] for i in strategies) / sum(strategy_weight)

# For SHORT direction:
weighted_short = sum(strategy_weight[i] * S_SHORT[i] for i in strategies) / sum(strategy_weight)

# Net signal:
net_signal = weighted_long - weighted_short

# Decision:
if max(S_LONG) > tier1_threshold:
    decision = 'LONG' (Tier1)
elif net_signal > tier2_threshold and count(S_LONG > 0.3) >= 2:
    decision = 'LONG' (Tier2)
else:
    decision = None (Tier3)
```

**Risk Aggregation**:
```python
# Ensemble risk score (average of individual risks):
ensemble_risk = sum(strategy_weight[i] * S_RISK[i]) / sum(strategy_weight)

# Risk-adjusted position size:
position_size = base_position_size * (1.0 - ensemble_risk)
```

**Quality Filtering**:
```python
# Only consider strategies with quality > min_quality_threshold:
valid_strategies = [s for s in strategies if s['S_QUALITY'] > min_quality_threshold]

# If no valid strategies:
if not valid_strategies:
    decision = None
```

### 3.3 Config Structure (Ensemble Control)

**Config YAML** (TO-BE):
```yaml
ensemble:
  mode: 'OFF' | 'ON' | 'DEBUG'      # Ensemble enable/disable
  
  # 3-Tier Thresholds
  tier1_threshold: 0.8              # High-confidence threshold
  tier2_threshold: 0.5              # Consensus threshold
  min_consensus_count: 2            # Min strategies agreeing for Tier2
  min_quality_threshold: 0.3        # Min quality to consider signal
  
  # Strategy Weights
  strategy_weights:
    scalping: 1.0                   # Base weight for each strategy
    volatility_breakout_v2: 0.8
    mean_reversion_v2: 0.8
    trend_follow_v2: 1.0
    volume_based_v2: 0.7
  
  # Regime Multipliers (PHASE24+)
  regime_multipliers:
    trending_short:
      scalping: 1.2                 # Boost scalping in short trends
      mean_reversion_v2: 0.7        # Reduce reversion in trends
    ranging:
      mean_reversion_v2: 1.3        # Boost reversion in ranging
      trend_follow_v2: 0.5          # Reduce trend following in ranging
    volatile_breakout:
      volatility_breakout_v2: 1.5   # Boost breakout in volatile regimes
  
  # Risk Settings
  max_ensemble_risk: 0.7            # Max allowed ensemble risk score
  risk_adjusted_sizing: true        # Enable risk-adjusted position sizing
  
  # Conflict Resolution
  long_short_conflict_action: 'SKIP' | 'NET_SIGNAL' | 'QUALITY_WINS'
  # SKIP: Don't trade if LONG and SHORT scores both high
  # NET_SIGNAL: Trade based on net_signal (LONG - SHORT)
  # QUALITY_WINS: Trade direction with higher quality score

strategies:
  scalping:
    enabled: true
    params:
      # ... (as defined in section 2.1)
  
  volatility_breakout_v2:
    enabled: true
    params:
      # ... (as defined in section 2.2)
  
  # ... (other strategies)
```

---

## 4. Strategy Complementarity Matrix

### 4.1 Regime-Based Complementarity

**Goal**: Ensure each regime has at least 2 active strategies.

| Market Regime | Primary Strategies | Secondary Strategies | Expected Behavior |
|---------------|-------------------|---------------------|-------------------|
| **Strong Trend Up** | trend_follow_v2 (1.0x)<br>scalping (0.8x) | volatility_breakout_v2 (0.6x) | Trend captures main move, scalping catches pullbacks |
| **Strong Trend Down** | trend_follow_v2 (1.0x)<br>scalping (0.8x) | volatility_breakout_v2 (0.6x) | Same as above |
| **Ranging / Sideways** | mean_reversion_v2 (1.3x)<br>volume_based_v2 (1.0x) | scalping (0.7x) | Reversion profits from oscillations, volume catches breakouts |
| **Volatile Breakout** | volatility_breakout_v2 (1.5x)<br>volume_based_v2 (1.2x) | scalping (0.9x) | Breakout captures move, volume confirms, scalping follows |
| **Low Volatility** | scalping (0.5x)<br>mean_reversion_v2 (0.8x) | None (all reduced) | Minimal trading, wait for volatility to return |

**Multipliers** are applied to base_weight via `regime_multipliers` in config.

### 4.2 Timeframe Diversification

**Goal**: Avoid all strategies operating on same timeframe (reduces correlation).

| Strategy | Timeframe | Frequency | Role |
|----------|-----------|-----------|------|
| scalping | 3m | ACTIVE | High-frequency signals |
| mean_reversion_v2 | 5m | LOW_FREQ | Short-term reversion |
| volume_based_v2 | 5m | LOW_FREQ | Event-driven |
| volatility_breakout_v2 | 15m | LOW_FREQ | Medium-term breakout |
| trend_follow_v2 | 1h | LOW_FREQ | Long-term trend |

**Result**: Strategies operate on different timescales, reducing signal correlation and improving ensemble diversity.

### 4.3 Indicator Diversification

**Goal**: Each strategy uses different indicator combinations to avoid redundancy.

| Strategy | Primary Indicators | Secondary Indicators |
|----------|-------------------|---------------------|
| scalping | RSI, EMA | Volume, Momentum |
| volatility_breakout_v2 | ATR, Bollinger Bands | Volume |
| mean_reversion_v2 | Bollinger Bands, RSI | Distance from mean |
| trend_follow_v2 | EMA, ADX | Trailing stop |
| volume_based_v2 | Volume, Candle pattern | Price position |

**Result**: Low indicator overlap ensures strategies provide independent signals.

---

## 5. Strategy Parameter Ranges (Initial)

### 5.1 Conservative Defaults (PHASE23-3)

**Goal**: Start with conservative params to ensure strategies produce signals but don't overtrade.

```yaml
# Family 1: HF Momentum
scalping:
  params:
    rsi_oversold: 40        # Relaxed from 30
    rsi_overbought: 60      # Relaxed from 70
    ema_fast: 9
    ema_slow: 21
    volume_mult: 1.5
    momentum_enabled: false
    volume_required: false

# Family 2: Volatility Breakout
volatility_breakout_v2:
  params:
    atr_mult: 2.0           # Conservative (wider breakout)
    bb_std: 2.0
    volume_mult: 1.2
    min_volatility: 0.02

# Family 3: Mean Reversion
mean_reversion_v2:
  params:
    bb_std: 2.0
    rsi_oversold: 25        # Tighter than scalping
    rsi_overbought: 75
    mean_distance_mult: 1.5

# Family 4: Trend Following
trend_follow_v2:
  params:
    adx_threshold: 25       # Moderate trend strength required
    ema_fast: 12
    ema_slow: 26

# Family 5: Volume-Based
volume_based_v2:
  params:
    volume_mult: 2.5        # High volume spike required
    candle_body_ratio: 0.6
    close_position_ratio: 0.8
```

### 5.2 Tuning Ranges (PHASE25)

**Goal**: Define parameter search space for automated tuning.

| Strategy | Parameter | Min | Max | Default | Step |
|----------|-----------|-----|-----|---------|------|
| **scalping** | rsi_oversold | 25 | 50 | 40 | 5 |
| | rsi_overbought | 50 | 75 | 60 | 5 |
| | volume_mult | 1.0 | 2.5 | 1.5 | 0.25 |
| **volatility_breakout_v2** | atr_mult | 1.5 | 3.0 | 2.0 | 0.25 |
| | bb_std | 1.5 | 2.5 | 2.0 | 0.25 |
| **mean_reversion_v2** | bb_std | 1.5 | 3.0 | 2.0 | 0.25 |
| | mean_distance_mult | 1.0 | 2.5 | 1.5 | 0.25 |
| **trend_follow_v2** | adx_threshold | 20 | 35 | 25 | 5 |
| **volume_based_v2** | volume_mult | 2.0 | 4.0 | 2.5 | 0.5 |

**Tuning Method** (PHASE25):
1. Random Search (100 runs): Explore parameter space
2. Bayesian Optimization (30 runs): Refine promising regions
3. Local Grid Search (10 runs): Fine-tune best candidates

---

## 6. Acceptance Criteria

### 6.1 Individual Strategy Criteria (PHASE23-3)

**For Each Strategy**:
- [ ] 3H backtest produces >0 trades (not dead)
- [ ] Win rate >30% (not random)
- [ ] Max drawdown <20% (risk-controlled)
- [ ] Signal frequency appropriate for timeframe:
  - scalping (3m): >10 signals/hour
  - mean_reversion_v2 (5m): 3-10 signals/hour
  - volume_based_v2 (5m): 1-5 signals/hour
  - volatility_breakout_v2 (15m): 1-3 signals/hour
  - trend_follow_v2 (1h): 0.5-2 signals/hour

### 6.2 Ensemble Criteria (PHASE23-4)

**For Ensemble (3H Test)**:
- [ ] At least 3/5 strategies produce >0 trades
- [ ] No single strategy dominates (>60% of trades)
- [ ] Tier1/Tier2/Tier3 distribution reasonable:
  - Tier1: 10-30% (high-confidence signals)
  - Tier2: 40-60% (consensus signals)
  - Tier3: 20-40% (skipped, no clear signal)
- [ ] Ensemble win rate >35% (better than individual avg)
- [ ] Max drawdown <15% (risk aggregation works)

### 6.3 Config Propagation Criteria (PHASE23-1)

**For Config Integration**:
- [ ] Strategy params reach strategy correctly (no empty dicts)
- [ ] Logs show: `Strategy scalping loaded with params: {rsi_oversold: 40, ...}`
- [ ] Strategy uses config params (not hardcoded defaults)
- [ ] 30min paper test: At least 5 trades with correct thresholds

---

## 7. Implementation Timeline

### 7.1 PHASE23-0 (Current)
- ✅ Document 5-family ensemble framework
- ✅ Define Ensemble Score V2 structure
- ✅ Specify config structure for ensemble control

### 7.2 PHASE23-1 (Script + Engine Refactor)
- Duration: 2-4 hours
- Focus: Fix config propagation (absorb PHASE22-4 issue)
- Deliverable: 30min paper test with correct params

### 7.3 PHASE23-2 (Strategy Interface Unification)
- Duration: 3-5 hours
- Focus: Migrate scalping_v3 to BaseStrategy, add score calculation
- Deliverable: All 5 strategies use unified interface

### 7.4 PHASE23-3 (Individual Strategy Validation)
- Duration: 4-6 hours
- Focus: 3H backtest for each strategy, rough param tuning
- Deliverable: 5/5 strategies produce >0 trades

### 7.5 PHASE23-4 (Ensemble Integration Test)
- Duration: 2-3 hours
- Focus: 3H ensemble paper test, verify multi-strategy participation
- Deliverable: Ensemble test report, criteria validation

---

## 8. Risk & Mitigation

### 8.1 Strategy Risks

| Risk | Mitigation |
|------|------------|
| **Strategy produces 0 trades** | Individual validation (PHASE23-3) before ensemble |
| **Strategy overproduces signals** | Cooldown, FlowGuardian, conservative params |
| **Strategies conflict (LONG + SHORT)** | Conflict resolution in config (long_short_conflict_action) |
| **Low strategy diversity** | Indicator diversification matrix, timeframe spread |

### 8.2 Ensemble Risks

| Risk | Mitigation |
|------|------------|
| **One strategy dominates** | Weight tuning, regime multipliers |
| **No consensus ever reached** | Lower tier2_threshold, reduce min_consensus_count |
| **High ensemble risk** | max_ensemble_risk limit, risk-adjusted sizing |
| **Conflicting regimes** | Regime detection + dynamic weights (PHASE24) |

---

## 9. Future Enhancements (Post-PHASE23)

### 9.1 PHASE24: Ensemble V2 Integration
- Implement Ensemble Score V2 calculation in each strategy
- Integrate ScoreEngine + EnsembleAggregator in engine loop
- 3H ensemble paper test with full scoring

### 9.2 PHASE25: Tuning Cluster
- Automated parameter search for each strategy
- Ensemble weight optimization
- Backtest validation of tuned params

### 9.3 PHASE26: Multi-Symbol
- Extend ensemble to Top10/20/50 symbols
- Per-symbol regime detection
- Symbol-specific strategy weights

### 9.4 PHASE28+: Monitoring & UI
- Real-time strategy score visualization
- Ensemble decision breakdown (Tier1/2/3 stats)
- Strategy participation charts

---

## 10. Conclusion

**Summary**:
- **5 Families Defined**: HF Momentum, Volatility Breakout, Mean Reversion, Trend Following, Volume-Based
- **Complementarity Ensured**: Regime-based, timeframe-based, indicator-based diversification
- **Ensemble Score V2**: Standardized signal structure (S_LONG, S_SHORT, S_RISK, S_QUALITY)
- **Config-Driven Control**: All weights, thresholds, and params in YAML

**Next Steps**:
1. Complete PHASE23-0 documentation ✅
2. Proceed to PHASE23-1: Fix config propagation
3. Validate with 30min paper test (correct params)
4. Continue to PHASE23-2: Unify strategy interface

---

**Document Status**: 🟢 COMPLETE  
**Review Date**: 2025-11-29  
**Author**: Cascade AI (PHASE23-0)  
**Approved By**: [Pending User Review]
