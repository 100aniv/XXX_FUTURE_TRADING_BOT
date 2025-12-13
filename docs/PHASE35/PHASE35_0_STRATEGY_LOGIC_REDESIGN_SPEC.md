# PHASE35-0: Strategy Logic Redesign Specification

**Document Version**: 1.0  
**Created**: 2025-12-13  
**Status**: SPECIFICATION (Implementation Pending)

---

## Executive Summary

### Problem Statement
PHASE34 parameter sweep (18/18 configs, 3-month backtest) confirmed that **parameter tuning is ineffective** at improving trade quality:
- **WinRate variance**: 0.028% (near-zero, target: >0.1%)
- **PF variance**: 0.0008 (near-zero, target: >0.01)
- **Trades range**: 135-220 (parameter-dependent)

**Root Cause**: Parameters affect entry **frequency** (trades count) but not entry **quality** (WinRate/PF). The strategy signal logic is fundamentally flawed.

### Objective
Redesign strategy signal logic to achieve:
- **WinRate**: 38-42% (current: 28.4%, +9.6-13.6%p)
- **Profit Factor**: 1.15-1.25 (current: 0.57, +102-119%)
- **Expected Value**: Positive (+0.14 minimum)

### Approach
Replace parameter tuning with **signal logic redesign** based on:
1. Quantitative analysis of current failure modes
2. Industry-standard research methodologies
3. Triple-barrier labeling and meta-labeling framework
4. Walk-forward validation with multiple holdout periods

---

## Part 1: Root Cause Analysis (Gate-Level Diagnostics)

### 1.1 PHASE34 Gate Statistics Evidence

**Data Source**: `reports/backtest/phase34/sweep/gate_statistics_analysis.json`

**Key Findings** (9 representative configs, 2024-01-01 to 2024-04-01):

| Parameter | Range Tested | Effect on Trades | Effect on WinRate | Effect on PF |
|-----------|--------------|------------------|-------------------|--------------|
| **Confidence** | 0.20 → 0.30 | +135 (+1.3%) | +0.05%p | +0.001 |
| **Hysteresis** | 2 → 5 | +67 (+0.6%) | +0.02%p | +0.0004 |
| **MTF Weight** | 0.50 → 0.60 | +50 (+0.5%) | +0.02%p | +0.0001 |

**Variance Analysis**:
- WinRate std dev: 0.028% (effective threshold: >0.1%)
- PF std dev: 0.0008 (effective threshold: >0.01)
- **Conclusion**: Parameters control entry gate filtering (frequency) but do NOT affect signal quality.

### 1.2 Failure Mode Hypotheses

Based on 28.4% WinRate (random: 50%, target: 38%+), likely causes:

#### Hypothesis 1: Entry Timing (Late/Early)
- **Symptom**: Entering after momentum exhausted or before confirmation
- **Evidence Needed**: Entry price vs. peak/trough distance, slippage impact
- **Fix Direction**: Stricter confirmation filters, momentum decay detection

#### Hypothesis 2: False Breakouts (Noise Trades)
- **Symptom**: Breakout signals reverse quickly (fakeouts)
- **Evidence Needed**: Trade duration distribution, win/loss by hold time
- **Fix Direction**: Volume confirmation, ATR-based noise filters

#### Hypothesis 3: Regime Mismatch
- **Symptom**: Strategy enters trend signals in ranging markets (or vice versa)
- **Evidence Needed**: Win rate by regime type (trend-up/down/range/chop)
- **Fix Direction**: Regime-aware signal gating, different logic per regime

#### Hypothesis 4: Exit Strategy (Premature TP/Late SL)
- **Symptom**: Cutting winners short, letting losers run
- **Evidence Needed**: RR ratio distribution, PnL by exit reason
- **Fix Direction**: Dynamic TP levels, trailing stops, early loss-cutting

#### Hypothesis 5: Over-Diversification (14 OR Scenarios)
- **Symptom**: Too many low-quality entry paths dilute signal strength
- **Evidence Needed**: Win rate per scenario, scenario activation frequency
- **Fix Direction**: Prune weak scenarios, tighten AND conditions

---

## Part 2: Industry-Standard Research Framework

### 2.1 Meta-Labeling Approach (Advances in Financial ML)

**Reference**: López de Prado, Marcos. *Advances in Financial Machine Learning* (2018), Chapter 3.

**Core Concept**: Separate **signal generation** (primary model) from **position sizing** (meta-model).

**Triple-Barrier Method**:
```
Label = {
  1 (LONG): if price hits upper barrier (TP) before lower/time barrier
  -1 (SHORT): if price hits lower barrier (SL) before upper/time barrier
  0 (SKIP): if time barrier hits first (sideways)
}
```

**Benefits**:
1. Quantifies **signal quality** independent of market direction
2. Prevents overfitting to specific price paths
3. Enables objective evaluation of entry logic

**Application to PHASE35**:
- Re-label PHASE34 trades with triple-barrier outcomes
- Compute precision/recall for each of 14 OR scenarios
- Keep only scenarios with precision >45% and recall >10%

### 2.2 Walk-Forward Validation (WFV)

**Standard Approach** (Pardo, *The Evaluation and Optimization of Trading Strategies*, 2008):

```
Training Period: 2024-01-01 to 2024-02-29 (2 months)
   ↓
Optimize/Select logic
   ↓
OOS Test 1: 2024-03-01 to 2024-03-31 (1 month)
   ↓
Re-train: 2024-02-01 to 2024-03-31 (2 months)
   ↓
OOS Test 2: 2024-04-01 to 2024-04-30 (1 month)
```

**Acceptance Criteria**:
- OOS WinRate degradation < 5%p vs. training
- OOS PF degradation < 0.15 vs. training
- Both OOS periods must pass independently

### 2.3 Regime Detection (Academic Standard)

**Reference**: Ang, Andrew, and Geert Bekaert. "Regime switches in interest rates." *Journal of Business & Economic Statistics* 20.2 (2002): 163-182.

**Hidden Markov Model (HMM)** for regime classification:
- **States**: Trend-Up, Trend-Down, Range, High-Volatility
- **Observables**: Returns, ATR, EMA slope, Volume
- **Transition Matrix**: Probability of regime shift per period

**Simpler Alternative (MVP)**:
- **ATR Percentile**: >75% → High-Vol, <25% → Low-Vol
- **EMA Slope + ADX**: Trend strength classification
- **Regime Persistence**: Require 3+ candles for regime confirmation

**Strategy Application**:
- Different signal logic per regime
- Disable/reduce sizing in unfavorable regimes
- Track win rate by regime to identify strengths

---

## Part 3: Redesign Candidates

### Candidate A: Scenario Pruning + Regime Gating (Conservative)

**Approach**: Keep existing structure, remove weak paths, add regime filter.

**Changes**:
1. **Prune Scenarios**: Keep only top 6 of 14 based on triple-barrier precision
2. **Regime Gate**: Block entries if regime confidence <0.5 or mismatch (e.g., LONG in TREND_DOWN)
3. **Tighten AND Conditions**: Increase min_confidence from 0.20-0.30 → 0.40-0.50

**Expected Impact**:
- Trades: 80-100 → 50-70 (-30-40%)
- WinRate: 28.4% → 34-38% (+5.6-9.6%p)
- PF: 0.57 → 0.95-1.10 (+67-93%)

**Pros**: Minimal code changes, low risk  
**Cons**: May still underperform, conservative gains

---

### Candidate B: Momentum Decay + Volume Confirmation (Moderate)

**Approach**: Replace breakout logic with momentum strength + volume validation.

**New Entry Logic**:
```python
def generate_signal_v2(df, config):
    # 1. Momentum Strength (RSI + EMA alignment)
    momentum_long = (rsi > 50) and (close > ema_fast > ema_slow)
    momentum_short = (rsi < 50) and (close < ema_fast < ema_slow)
    
    # 2. Volume Confirmation (spike + sustained)
    volume_spike = volume > sma_volume_20 * 1.5
    volume_sustained = volume[-3:].mean() > sma_volume_20
    
    # 3. Regime Filter (HTF alignment)
    regime_aligned_long = htf_regime in ['TREND_UP'] and ltf_regime in ['TREND_UP', 'RANGE']
    regime_aligned_short = htf_regime in ['TREND_DOWN'] and ltf_regime in ['TREND_DOWN', 'RANGE']
    
    # 4. Entry Conditions
    long_signal = momentum_long and volume_spike and volume_sustained and regime_aligned_long
    short_signal = momentum_short and volume_spike and volume_sustained and regime_aligned_short
    
    return long_signal, short_signal
```

**Expected Impact**:
- Trades: 80-100 → 60-80 (-20-25%)
- WinRate: 28.4% → 36-40% (+7.6-11.6%p)
- PF: 0.57 → 1.05-1.20 (+84-111%)

**Pros**: Addresses timing and false breakouts, proven indicators  
**Cons**: Requires indicator validation, medium risk

---

### Candidate C: Multi-Model Ensemble (Aggressive)

**Approach**: Train 3 independent models, require 2/3 agreement for entry.

**Models**:
1. **Trend Model**: EMA + ADX + Supertrend
2. **Mean-Reversion Model**: RSI + Bollinger Bands + Volume
3. **Breakout Model**: Support/Resistance + Volume + ATR

**Ensemble Logic**:
```python
def ensemble_signal(df, config):
    trend_signal = trend_model.predict(df)
    reversion_signal = reversion_model.predict(df)
    breakout_signal = breakout_model.predict(df)
    
    # Require 2/3 agreement
    long_votes = sum([trend_signal == 1, reversion_signal == 1, breakout_signal == 1])
    short_votes = sum([trend_signal == -1, reversion_signal == -1, breakout_signal == -1])
    
    if long_votes >= 2:
        return 'LONG'
    elif short_votes >= 2:
        return 'SHORT'
    else:
        return 'NEUTRAL'
```

**Expected Impact**:
- Trades: 80-100 → 40-60 (-40-50%)
- WinRate: 28.4% → 40-45% (+11.6-16.6%p)
- PF: 0.57 → 1.20-1.40 (+111-146%)

**Pros**: Highest quality potential, diversified signals  
**Cons**: Complex implementation, requires 3 model validations, high risk

---

## Part 4: Validation & Testing Plan

### 4.1 Phase Sequence (Stepwise Gating)

```
PHASE35-1: Candidate Implementation (1 week)
   ↓
PHASE35-2: 7-Day Smoke Test (All 3 candidates)
   ├─ Target: WinRate >32%, PF >0.70, Trades >10
   ├─ Pass: Proceed to 1-month
   └─ Fail: Debug or drop candidate
   ↓
PHASE35-3: 1-Month Baseline (Pass-only candidates)
   ├─ Target: WinRate >35%, PF >0.90, Trades >30
   ├─ Pass: Proceed to 3-month
   └─ Fail: Iterate or drop
   ↓
PHASE35-4: 3-Month Validation (Top 1-2 candidates)
   ├─ Target: WinRate >38%, PF >1.10, Trades >80
   ├─ Pass: Proceed to PAPER
   └─ Fail: Return to design
   ↓
PHASE35-5: PAPER Trading (20m → 1h → 3h → 12h)
   ├─ Target: Similar metrics to backtest, no crashes
   ├─ Pass: Production ready
   └─ Fail: Debug infra or logic
```

### 4.2 Acceptance Criteria (Per Phase)

| Phase | Duration | Min Trades | Min WinRate | Min PF | Max Drawdown | Decision |
|-------|----------|------------|-------------|--------|--------------|----------|
| 35-1 | N/A | N/A | N/A | N/A | N/A | Implementation |
| 35-2 | 7 days | 10 | 32% | 0.70 | <5% | Smoke Pass/Fail |
| 35-3 | 1 month | 30 | 35% | 0.90 | <8% | Baseline Pass/Fail |
| 35-4 | 3 months | 80 | 38% | 1.10 | <12% | Validation Pass/Fail |
| 35-5 | 20m-12h | 5-40 | 35%+ | 0.90+ | <10% | PAPER Pass/Fail |

### 4.3 Contingency Plan

**If all candidates fail 3-month validation**:
1. **Diagnose** via gate statistics (re-run PHASE34-style analysis)
2. **Hypothesis Revision**: Update failure mode list based on new data
3. **Candidate D/E**: Design 1-2 new approaches based on diagnostics
4. **Re-enter** at PHASE35-2 (smoke test)

**Maximum Iterations**: 3 rounds before escalating to ensemble refactor or external research consultation.

---

## Part 5: Implementation Guidelines

### 5.1 Code Structure (DO-NOT-TOUCH Compliance)

**New Files** (Preferred):
- `strategies/btc15m_core_v3.py` (Candidate A/B/C implementations)
- `strategies/utils/triple_barrier.py` (Meta-labeling helper)
- `strategies/utils/regime_hmm.py` (HMM regime detector, optional)

**Modified Files** (Minimal, Doc-Required):
- `strategies/btc15m_core_v2.py` (ONLY if refactoring in-place, not recommended)

**Do NOT Touch**:
- `execution/engine.py`
- `execution/portfolio_manager.py`
- `execution/risk_manager.py`

### 5.2 Testing Requirements

**Unit Tests** (`tests/test_strategies/test_btc15m_core_v3.py`):
- Test signal generation logic independently
- Test regime detection accuracy (if using HMM)
- Test triple-barrier labeling correctness

**Integration Tests** (`tests/integration/test_phase35_backtest.py`):
- Smoke test (7-day) automated
- Baseline test (1-month) automated
- Validation test (3-month) manual review

**Regression Gate**:
- All existing tests must pass (no breaks)
- New tests must pass 100%

---

## Part 6: Success Metrics & Exit Criteria

### 6.1 Primary Metrics (Must-Pass)

1. **WinRate**: ≥38% (3-month backtest)
2. **Profit Factor**: ≥1.10 (3-month backtest)
3. **Expected Value**: >0 (positive expectancy)
4. **Max Drawdown**: <12% (equity-based)

### 6.2 Secondary Metrics (Nice-to-Have)

5. **Sharpe Ratio**: >0.5 (3-month)
6. **Calmar Ratio**: >0.8 (3-month)
7. **Trade Duration**: 30-120 minutes median (avoid overnight)
8. **Regime Coverage**: ≥60% uptime (not over-filtered)

### 6.3 Exit Criteria (Abandon PHASE35)

**Fail Conditions**:
- 3 full iteration cycles (35-2 through 35-4) without passing 3-month validation
- WinRate improvement <3%p after 2 iterations
- PF improvement <0.15 after 2 iterations

**Action**: Escalate to **PHASE36** (Alternative Approach):
- Consider ML-based signal generation (XGBoost, LSTM)
- Consider arbitrage or market-making strategies
- Consider external alpha signals (order flow, funding rate)

---

## Part 7: Risk Assessment

### 7.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Overfitting to 2024 data | High | High | Walk-forward, multiple OOS periods |
| Candidate A too conservative | Medium | Low | Have B/C as alternatives |
| Candidate C too complex | Medium | Medium | Implement B first, C optional |
| HMM regime detection unstable | Low | Medium | Use simpler ATR-based fallback |

### 7.2 Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| PAPER divergence from backtest | Medium | High | 20m → 1h → 3h gradual ramp |
| Infrastructure bugs (engine/risk) | Low | High | DO-NOT-TOUCH policy, extensive unit tests |
| Data quality issues (MTF) | Low | Medium | Verify MTF injection in logs |

---

## Part 8: Timeline Estimate

**Conservative Estimate** (Assuming 1 iteration):

| Phase | Duration | Notes |
|-------|----------|-------|
| PHASE35-1 | 2-3 days | Implementation (A+B, C optional) |
| PHASE35-2 | 1 day | 7-day smoke tests (parallel) |
| PHASE35-3 | 1-2 days | 1-month baseline (sequential) |
| PHASE35-4 | 1-2 days | 3-month validation (top 1-2) |
| PHASE35-5 | 1-2 days | PAPER 20m→12h ramp |
| **Total** | **6-10 days** | Single iteration, no major issues |

**Worst Case** (3 iterations + debugging): 3-4 weeks

---

## Part 9: Appendix

### 9.1 References

1. López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
   - Chapter 3: Labeling (Triple-Barrier Method)
   - Chapter 7: Cross-Validation in Finance

2. Pardo, R. (2008). *The Evaluation and Optimization of Trading Strategies* (2nd ed.). Wiley.
   - Chapter 6: Walk-Forward Analysis

3. Ang, A., & Bekaert, G. (2002). "Regime switches in interest rates." *Journal of Business & Economic Statistics*, 20(2), 163-182.

4. Aronson, D. (2006). *Evidence-Based Technical Analysis*. Wiley.
   - Chapter 9: Data-Mining Bias and Overfitting

### 9.2 Related Documents

- `docs/PHASE34/PHASE34_4_SWEEP_REPORT.md` (Parameter tuning results)
- `docs/PHASE34/PHASE34_3_EXECUTION_STATUS.md` (Final execution status)
- `reports/backtest/phase34/sweep/gate_statistics_analysis.json` (Quantitative evidence)
- `strategies/btc15m_core_v2.py` (Current failing strategy)

---

**Document Status**: ✅ APPROVED FOR IMPLEMENTATION  
**Next Action**: Proceed to PHASE35-1 (Candidate Implementation)  
**Owner**: Strategy Development Team  
**Review Date**: 2025-12-20 (After 35-2 smoke tests)
