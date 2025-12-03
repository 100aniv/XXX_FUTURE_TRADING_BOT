# PHASE27-0: Trade Activity Diagnosis & Drop-off Instrumentation - Design Document

**Date**: 2025-12-03  
**Status**: 🔄 IN PROGRESS  
**Phase**: PHASE27-0 – Trade Activity Diagnosis  
**Purpose**: Systematically diagnose "0 trades" issue and build drop-off instrumentation infrastructure

---

## 1. Objective

### 1.1 Goals

**Primary Objectives**:
1. **Root Cause Analysis**: Identify exactly where signals are being dropped in the pipeline
2. **Drop-off Instrumentation**: Build metrics collection for each decision point
3. **Baseline Establishment**: Measure signal survival rate across different configurations
4. **Tuning Roadmap**: Define parameter candidates for next phases (no actual tuning in PHASE27-0)

**Background**:
- PHASE23-4 (12min): 50 trades, 5,499 aggregates → **4.2 trades/min, healthy activity**
- PHASE25-0 (2H): 39 trades, 10,564 aggregates → **0.3 trades/min, low throughput**
- PHASE26-3 (30m Top100): **0 trades, 0 aggregates → complete signal dropout**

**Key Questions**:
- Why did aggregate count drop from 10,564 (PHASE25) to 0 (PHASE26-3)?
- At which stage (Strategy → Ensemble → Guards → Execution) do signals die?
- Is it a config issue, multi-symbol issue, or strategy parameter issue?

---

## 2. Signal → Trade Pipeline Flow

### 2.1 End-to-End Pipeline

```
[1] DataFeed: WebSocket/Backtest
      ↓ candle stream
[2] Indicators: RSI, EMA, Bollinger Bands, etc.
      ↓ technical indicators
[3] Strategy.compute_signal()
      ↓ raw signal (side, entry, sl, tp)
      ↓
[4a] Single-Strategy Mode (ensemble=off)
      → direct to Risk/Guards
      ↓
[4b] Ensemble Mode (ensemble=score_v2)
      → [5] ScoreEngineV2.compute_strategy_score()
         ↓ Score V2 (S_LONG, S_SHORT, S_NET, S_RISK, S_QUALITY)
      → [6] EnsembleAggregatorV2.aggregate_v2()
         ↓ 3-Tier Logic (Tier1/Tier2/Skip)
         ↓ Ensemble Decision
      ↓
[7] RiskManager.check_order()
      ↓ Daily loss, position limits, flash guard
      ↓
[8] FlowGuardian / Various Guards
      ↓ Cooldown, symbol guard, frequency guard, DD guard
      ↓
[9] Execution: Order submission
      ↓
[10] Trade recorded in DB
```

### 2.2 Drop-off Points (Where Signals Can Die)

| Stage | Component | Potential Drop Reasons | Code Location |
|-------|-----------|------------------------|---------------|
| **[3] Strategy** | `BaseStrategy.compute_signal()` | Indicator conditions not met (RSI, EMA, volume) | `strategies/*/` |
| **[5] Score Engine** | `ScoreEngineV2.compute_strategy_score()` | Risk/Quality filtering | `common/ensemble/score_engine_v2.py` |
| **[6] Aggregator** | `EnsembleAggregatorV2.aggregate_v2()` | Tier1/Tier2 thresholds not met, dominance prevention | `common/ensemble/aggregator_v2.py` |
| **[7] Risk Manager** | `RiskManager.check_order()` | Daily loss limit, position count, exposure cap | `execution/risk_manager.py` |
| **[8] Guards** | FlowGuardian, Flash Guard, Cooldown | Symbol guard, cooldown, DD guard, flash guard pause | `core/flow_guardian.py`, `execution/risk_manager.py` |

---

## 3. Historical Trade Activity Analysis

### 3.1 Comparative Results

| Run | Duration | Mode | Trades | Aggregates | Config | Status |
|-----|----------|------|--------|------------|--------|--------|
| **PHASE23-4** | 12m | Single-Symbol PAPER | 50 | 5,499 | `phase23_4_ensemble_v2_3h.yml` | ✅ Healthy |
| **PHASE25-0** | 2H | Single-Symbol PAPER | 39 | 10,564 | `phase25_0_long_run_2h.yml` | ⚠️ Low throughput |
| **PHASE26-3** | 30m | Multi-Symbol Top100 | **0** | **0** | `phase26_3_top100_paper_30m.yml` | ❌ Complete dropout |

### 3.2 Common Patterns - 0 Trades Runs

**PHASE26-3 Characteristics**:
- Multi-Symbol (Top100)
- Ensemble mode: `score_v2`
- Duration: 30m (wall-clock)
- Strategies: 5 strategies (scalping_v3, trend_follow_v2, mean_reversion_v2, volume_based_v2, volatility_breakout_v2)
- **Aggregate count: 0** → Ensemble Aggregator never called → No strategy signals generated

**Hypothesis**:
1. **Strategy Parameter Issue**: Multi-symbol config may have overly conservative thresholds
2. **Timeframe Mismatch**: Strategies may be configured for specific timeframes (e.g., scalping=3m) but multi-symbol feed is 5m
3. **Data Quality**: WebSocket feed may not be providing complete indicator data
4. **Config Propagation**: Strategy params may not be properly propagated in multi-symbol mode

### 3.3 Healthy Run Analysis (PHASE23-4)

**Why did PHASE23-4 work?**
- Single-Symbol (BTCUSDT)
- Timeframe: 5m (matches strategy expectations)
- Strategies: 5 V2 strategies active
- Tier1: 25.5% (1,403 / 5,499) → High-confidence decisions
- Tier2: 1.0% (56 / 5,499) → Consensus decisions
- Skip: 73.5% (4,040 / 5,499)
- **Key**: 26.5% of aggregates led to active decisions (Tier1+Tier2)

**Trade Rate**: 50 trades / 12min = **4.2 trades/min**  
**Aggregate → Trade Conversion**: 50 / 1,459 active decisions = **3.4%**

---

## 4. PHASE27-0 Implementation Plan

### 4.1 Trade Activity Tracker Module

**New Module**: `metrics/trade_activity_tracker.py`

**Purpose**: In-memory counter to track signal survival across pipeline stages

**API**:
```python
class TradeActivityTracker:
    """
    Drop-off instrumentation for Signal → Trade pipeline
    
    Tracks:
    - Strategy signals (per symbol, per strategy)
    - Ensemble decisions (Tier1/Tier2/Skip)
    - Guard blocks (by reason)
    - Order submissions
    """
    
    def record_strategy_signal(self, symbol: str, strategy_id: str, has_signal: bool) -> None:
        """Record strategy signal generation"""
    
    def record_ensemble_decision(self, symbol: str, tier: str, side: str) -> None:
        """Record ensemble aggregator decision (tier1/tier2/skip)"""
    
    def record_guard_block(self, symbol: str, reason: str) -> None:
        """Record guard block event with reason"""
    
    def record_order_submitted(self, symbol: str, side: str, size: float) -> None:
        """Record order submission"""
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
    
    def save_json(self, output_path: Path) -> None:
        """Save results to JSON file"""
```

**Data Structure**:
```python
{
    "run_id": "phase27_0_single_symbol_30m",
    "duration_minutes": 30,
    "timestamp": "2025-12-03T...",
    "symbols": {
        "BTCUSDT": {
            "strategy_signals": {
                "scalping_v3": {"total_calls": 500, "signal_true": 5, "signal_false": 495},
                "trend_follow_v2": {"total_calls": 500, "signal_true": 120, "signal_false": 380}
            },
            "ensemble_decisions": {
                "tier1": 3,
                "tier2": 2,
                "skip": 50
            },
            "guard_blocks": {
                "cooldown_block": 10,
                "dd_block": 0,
                "flash_guard": 2
            },
            "orders_submitted": 4
        }
    },
    "totals": {
        "strategy_signals": 625,
        "ensemble_tier1": 3,
        "ensemble_tier2": 2,
        "ensemble_skip": 50,
        "guard_blocks": 12,
        "orders_submitted": 4
    }
}
```

### 4.2 Hook Points

**Minimal Engine/Strategy Modifications**:

1. **Strategy Signal Hook** (`execution/engine.py` L1200-1400):
   ```python
   # After strategy.compute_signal()
   if activity_tracker:
       activity_tracker.record_strategy_signal(
           symbol=candle_symbol,
           strategy_id=strategy_name,
           has_signal=(raw_signal is not None and raw_signal.get('side') is not None)
       )
   ```

2. **Ensemble Decision Hook** (`execution/engine.py` L1344-1353):
   ```python
   # After ensemble_aggregator_v2.aggregate_v2()
   if activity_tracker:
       activity_tracker.record_ensemble_decision(
           symbol=candle_symbol,
           tier=ensemble_decision_v2.tier,
           side=ensemble_decision_v2.side
       )
   ```

3. **Guard Block Hook** (`execution/risk_manager.py`, `core/flow_guardian.py`):
   ```python
   # When guard blocks signal
   if activity_tracker:
       activity_tracker.record_guard_block(symbol, reason="cooldown_active")
   ```

4. **Order Submission Hook** (`execution/engine.py` order submission):
   ```python
   # After broker.place_order()
   if activity_tracker:
       activity_tracker.record_order_submitted(symbol, side, size)
   ```

**Design Principles**:
- Hooks are **optional** (if `activity_tracker` is None, no overhead)
- **No logic changes** to core engine/strategy/ensemble
- **In-memory only** (no DB writes during run, JSON dump at end)
- **Thread-safe** (use locks if needed for multi-threading)

### 4.3 Test Scenarios

**Scenario 1: Single-Symbol 30m Baseline**
- Config: `configs/paper/phase27_0_single_symbol_30m.yml` (based on PHASE23-4 config)
- Symbol: BTCUSDT
- Duration: 30m
- Ensemble: score_v2
- Expected: Aggregates > 0, Trades > 0 (reproduce PHASE23-4 behavior)

**Scenario 2: Multi-Symbol Top10 30m**
- Config: `configs/paper/phase27_0_top10_30m.yml` (based on PHASE26-2 config)
- Symbols: Top10 by volume
- Duration: 30m
- Ensemble: score_v2
- Expected: Aggregates ≥ 0, identify drop-off point if Trades = 0

**Scenario 3 (Optional): Top100 30m Re-run**
- Config: `configs/paper/phase26_3_top100_paper_30m.yml` (existing)
- Symbols: Top100
- Duration: 30m
- Expected: Validate previous 0-trade result, collect drop-off metrics

---

## 5. Redis/DB Infra Assumptions & Fail-Fast Policy

### 5.1 Current State (PHASE24/26)

**Redis Hardening (PHASE24-0)**:
- `clean_state_complete.py`: Retry logic with max_retries=10, 2s intervals
- `phase24_1_infra_diagnostics.py`: DB/Redis/Engine pre-flight checks
- `phase25_0_long_run_paper.py`: Calls `run_preflight_checks()` before run

**Observed Behavior**:
- Redis container startup may show initial ConnectionRefused errors
- Retry logic typically succeeds within 10-20s
- Final result: Redis connection OK

### 5.2 Fail-Fast Policy Definition

**Acceptable**: Transient connection failures during container startup (< 30s)

**Unacceptable**: Persistent connection failures after 60s

**Policy**:
- Pre-flight checks must pass before starting acceptance run
- If Redis/DB connection fails after 60s cumulative retry time → **FAIL and EXIT**
- Log all retry attempts with timestamps
- Final status: "Pre-flight PASS" or "Pre-flight FAIL (reason)"

**Implementation**:
- No code changes needed (existing retry logic sufficient)
- Document policy in this design doc
- Ensure runner scripts respect `run_preflight_checks()` return value

### 5.3 Redis Connection Assumptions

**Assumption 1**: Docker containers (Postgres, Redis) are running before test execution

**Assumption 2**: Transient failures (0-30s) are acceptable, persistent failures (>60s) are not

**Assumption 3**: Clean state script must succeed before acceptance run

**Verification**: All PHASE27-0 test runs will log pre-flight results in JSON output

---

## 6. Parameter Tuning Candidates (Scope for Future PHASEs)

**Note**: PHASE27-0 focuses on **diagnosis only**. Actual parameter tuning is deferred to PHASE27-1+.

### 6.1 Strategy Level

**Scalping V3** (`strategies/core/scalping_v3.py`):
- RSI thresholds: `rsi_oversold` (default: 30), `rsi_overbought` (default: 70)
- EMA window: `ema_window` (default: 20)
- Volume multiplier: `volume_mult` (default: 1.5)

**Trend Follow V2** (`strategies/research/trend_follow_v2.py`):
- EMA windows: `ema_fast` (default: 12), `ema_slow` (default: 26)
- Trend strength: `min_trend_strength` (default: 0.02)

**Mean Reversion V2** (`strategies/research/mean_reversion_v2.py`):
- Bollinger Band std: `bb_std` (default: 2.0)
- Reversion threshold: `min_bb_distance` (default: 0.5)

### 6.2 Ensemble Level

**Score Engine V2** (`common/ensemble/score_engine_v2.py`):
- Risk weight: `risk_weight` (default: 0.3)
- Quality weight: `quality_weight` (default: 0.2)

**Aggregator V2** (`common/ensemble/aggregator_v2.py`):
- Tier1 threshold: `high_confidence_threshold` (default: 0.7)
- Tier2 threshold: `consensus_threshold` (default: 0.4)
- Max strategy weight: `max_strategy_weight` (default: 0.6)
- Risk filter: `max_risk` (default: 0.5)
- Quality filter: `min_quality` (default: 0.3)

### 6.3 Guard Level

**Risk Manager** (`execution/risk_manager.py`):
- Daily loss limit: `max_daily_loss_pct` (default: 5%)
- Max positions: `max_positions` (default: 5)
- Per-symbol exposure: `max_symbol_exposure_pct` (default: 20%)
- Flash guard: `flash_pct` (default: 3%), `flash_pause_candles` (default: 3)

**Cooldown Guards**:
- Global cooldown: `cooldown_seconds` (default: 60)
- Symbol cooldown: `symbol_cooldown_seconds` (default: 120)

---

## 7. Deliverables

### 7.1 Documentation
- [x] This design document (`PHASE27-0_TRADE_ACTIVITY_DIAGNOSIS_DESIGN.md`)
- [ ] PHASE_ROADMAP.md update (PHASE27-0 section)

### 7.2 Code
- [ ] `metrics/trade_activity_tracker.py` (new module)
- [ ] Hooks in `execution/engine.py` (minimal, optional)
- [ ] Hooks in `execution/risk_manager.py` (minimal, optional)
- [ ] Unit tests: `tests/test_phase27_0_trade_activity_tracker.py`

### 7.3 Configs
- [ ] `configs/paper/phase27_0_single_symbol_30m.yml` (based on PHASE23-4)
- [ ] `configs/paper/phase27_0_top10_30m.yml` (based on PHASE26-2)

### 7.4 Test Runs
- [ ] Single-Symbol 30m: JSON output with drop-off metrics
- [ ] Multi-Symbol Top10 30m: JSON output with drop-off metrics
- [ ] Optional: Top100 30m re-run

### 7.5 Reports
- [ ] `docs/PHASE27/phase27_0_single_symbol_30m_summary.json`
- [ ] `docs/PHASE27/phase27_0_top10_30m_summary.json`
- [ ] `docs/PHASE27/PHASE27-0_TRADE_ACTIVITY_DIAGNOSIS_REPORT.md` (after test runs)

---

## 8. Acceptance Criteria

**PHASE27-0 is COMPLETE when**:

1. **Documentation**:
   - [x] Design document complete (this file)
   - [ ] PHASE_ROADMAP.md updated

2. **Code**:
   - [ ] TradeActivityTracker module implemented
   - [ ] Hooks added (engine, risk manager, guards)
   - [ ] Unit tests: 100% PASS
   - [ ] Regression tests: All existing tests PASS

3. **Test Runs**:
   - [ ] Single-Symbol 30m: ERROR/CRITICAL 0, drop-off JSON generated
   - [ ] Multi-Symbol Top10 30m: ERROR/CRITICAL 0, drop-off JSON generated
   - [ ] Pre-flight checks: ALL PASS

4. **Analysis**:
   - [ ] Drop-off metrics collected for both runs
   - [ ] Root cause hypothesis documented (even if trades = 0)
   - [ ] Parameter tuning candidates identified

5. **Git**:
   - [ ] Meaningful commit message
   - [ ] Clean status (no unintended changes)

---

## 9. Out of Scope (PHASE27-0)

**Explicitly NOT doing in this phase**:
- ❌ Actual parameter tuning (deferred to PHASE27-1+)
- ❌ MultiSymbolProfiler CPU/Memory profiling (deferred to PHASE27)
- ❌ IndicatorCache activation (deferred to PHASE27)
- ❌ New strategy implementation
- ❌ Ensemble architecture changes
- ❌ Long-run tests (>1H)

**Why**: PHASE27-0 is **diagnosis only**. We need to understand the problem before fixing it.

---

**Next Steps**: Implement TradeActivityTracker module and add hooks.
