# PHASE35-2: 7D Smoke Test Report
**Date**: 2025-12-14  
**Status**: COMPLETED (AC-BT0~BT3: FAIL - Profitability Criteria Not Met)

---

## Executive Summary

PHASE35-2 7D Smoke Test was executed with the `phase35_ensemble_v1` strategy in STRICT MODE. The test generated 10,498 trades over 7 days (2024-12-01 to 2024-12-08) but failed profitability acceptance criteria.

**Key Findings**:
- ✅ **AC-BT0**: Trades ≥ 10 → **10,498 trades** (PASS)
- ❌ **AC-BT1**: Win Rate > 32% → **28.4%** (FAIL)
- ❌ **AC-BT2**: Profit Factor > 0.70 → **0.567** (FAIL)
- ❌ **AC-BT3**: Max Drawdown < 5% → **-1,516 USD (-15.16%)** (FAIL)

**Overall Verdict**: **CONDITIONAL FAIL** - Strategy generates excessive trades with poor profitability.

---

## Test Configuration

### Config Files
- **Primary**: `configs/phase35/test_simple.yaml`
- **Fallback**: `configs/phase35/ensemble_v1.yaml` (complex structure, simplified to test_simple.yaml)

### Strategy: phase35_ensemble_v1
- **Type**: Ensemble (3 Sub-Models + 2-out-of-3 Majority Vote)
- **Sub-Models**:
  1. Trend-Following (EMA Cross + ADX)
  2. Mean-Reversion (RSI + Bollinger Bands)
  3. Breakout (ATR + Volume)
- **Regime Filter**: ATR-based (TREND/RANGE/CHOP)
- **Confidence Threshold**: 0.5

### Backtest Period
- **Start**: 2024-12-01
- **End**: 2024-12-08
- **Duration**: 7 days
- **Timeframe**: 15m
- **Symbol**: BTCUSDT
- **Initial Capital**: $10,000

---

## Results

### Performance Metrics
```
Total Trades:        10,498
Winning Trades:      2,982 (28.4%)
Losing Trades:       7,516 (71.6%)
Consecutive Losses:  40
Profit Factor:       0.567
ROI:                 -1,510.9%
Max Drawdown:        -$1,516 (-15.16%)
Total Return:        -$1,510.93
```

### Decision Trace Summary
```
Total Signals Checked:    34,982
Regime CHOP Blocks:       1,702 (91.4%)
Ensemble No Consensus:    61 (3.3%)
Other Blocks:             50 (2.7%)
```

---

## Root Cause Analysis

### Issue 1: Excessive Trade Generation
- **Symptom**: 10,498 trades in 7 days (~1,500 trades/day)
- **Cause**: Confidence threshold (0.5) too low, allowing marginal signals
- **Impact**: High transaction costs, poor signal quality

### Issue 2: Poor Win Rate (28.4% vs. Target 32%)
- **Symptom**: 71.6% losing trades
- **Cause**: Sub-model voting logic may not be filtering weak signals
- **Impact**: Negative expectancy

### Issue 3: Negative Profit Factor (0.567 vs. Target 0.70)
- **Symptom**: Losses exceed wins by 1.76x
- **Cause**: Risk/reward ratio misaligned, stop-loss placement suboptimal
- **Impact**: Strategy unprofitable

### Issue 4: Excessive Drawdown (-15.16% vs. Target <5%)
- **Symptom**: $1,516 loss on $10,000 capital
- **Cause**: Consecutive losing streaks (40 losses), position sizing too aggressive
- **Impact**: Capital erosion

---

## Config SSOT Status

### Resolved Issues
✅ **Decision Trace Path**: Dual-path support implemented
- Root-level: `config.get('decision_trace', {})`
- Strategy-nested: `config.get('strategy', {}).get('decision_trace', {})`

✅ **Ensemble Config Path**: Dual-path support implemented
- Root-level: `cfg.get('ensemble', {})`
- Strategy-nested: `cfg.get('strategy', {}).get('ensemble', {})`

✅ **Sub-Models Config**: Correctly accessed via `cfg.get('sub_models', {})`

✅ **Confidence Threshold**: Now correctly logged and accessible
- Expected: 0.5
- Actual: 0.5 ✅

### Remaining Issues
⚠️ **Ensemble Voting Logic**: Needs review
- Current: 2-out-of-3 majority vote
- Issue: May be generating too many signals with low confidence

⚠️ **Regime Filter**: Blocking 91.4% of signals
- Current: ATR-based (TREND/RANGE/CHOP)
- Issue: CHOP regime too aggressive, blocking valid signals

---

## Code Changes Summary

### 1. strategies/phase35_ensemble_v1.py
**Lines 49-57**: Dual-path decision_trace support
```python
dt_root = config.get('decision_trace', {})
dt_strategy = config.get('strategy', {}).get('decision_trace', {})
decision_trace_cfg = dt_root if dt_root else dt_strategy
self._diag_enabled = decision_trace_cfg.get('enabled', True)
```

**Lines 399-411**: Dual-path ensemble config support
```python
strategy_cfg = self.config.get('strategy', {})
if isinstance(strategy_cfg, dict):
    ensemble_cfg = strategy_cfg.get('ensemble', {})
else:
    ensemble_cfg = {}

if not ensemble_cfg:
    ensemble_cfg = self.config.get('ensemble', {})

confidence_threshold = ensemble_cfg.get('confidence_threshold', 0.5)
```

### 2. execution/engine.py
**Lines 1621-1633**: Ensemble config validation logging
```python
if strategy_id == 'phase35_ensemble_v1':
    logger.info(f"🔍 [PHASE35-2 CONFIG] {strategy_id} cfg keys: {list(cfg.keys())[:10]}")
    logger.info(f"🔍 [PHASE35-2 CONFIG] {strategy_id} strategy keys: {list(cfg.get('strategy', {}).keys())}")
    # ... config path validation
```

### 3. strategies/__init__.py
**Lines 209-212**: Ensemble strategy config preservation
```python
if selector == 'phase35_ensemble_v1':
    # Preserve entire strategy section from config for ensemble to access nested configs
    strategy_params['strategy'] = config.get('strategy', {})
```

### 4. configs/phase35/test_simple.yaml
**Lines 31-33**: Ensemble config in strategies section
```yaml
params:
  ensemble:
    method: "majority_vote"
    confidence_threshold: 0.5
```

---

## Recommendations for PHASE35-3

### Priority 1: Ensemble Logic Review
1. **Increase confidence_threshold** from 0.5 to 0.7-0.8
   - Reduce signal volume
   - Improve signal quality
2. **Review sub-model voting weights**
   - Current: Equal weight (1/3 each)
   - Consider: Weighted by recent performance
3. **Strengthen regime filter**
   - Current: Blocks CHOP (91.4% of signals)
   - Consider: Allow RANGE with stricter entry conditions

### Priority 2: Risk Management
1. **Position sizing**: Reduce per-trade risk from 2% to 1%
2. **Stop-loss placement**: Use ATR-based dynamic stops
3. **Take-profit levels**: Implement tiered exits (1.5R, 3.0R)

### Priority 3: Signal Quality
1. **Add confirmation filters**:
   - Volume spike confirmation
   - Multi-timeframe alignment
   - Trend strength validation
2. **Reduce false signals**:
   - Increase minimum bars for pattern confirmation
   - Add cooldown between consecutive signals

---

## Strict Mode Verification

✅ **Strict Mode Enabled**: `strategy.strict_mode: true`
✅ **Selector Fixed**: `strategy.selector: phase35_ensemble_v1`
✅ **No Fallback**: Strategy loading enforced (no daytrade fallback)
✅ **All Requested Strategies Loaded**: Confirmed in logs

---

## Next Steps

1. **PHASE35-3**: Tune ensemble parameters based on findings
2. **PHASE35-4**: Run 1-month baseline validation
3. **PHASE35-5**: 3-month comprehensive validation
4. **PHASE36**: Production deployment readiness

---

## Appendix: Full Metrics

```json
{
  "trial_id": null,
  "total_score": 33.24698906976205,
  "metrics": {
    "exp_score": 0.40569639368137045,
    "winrate": 28.414936178319678,
    "rr": 1.4277575396805322,
    "mdd": -1516.156444039129,
    "consecutive": 40,
    "pf": 0.5667332988512346,
    "roi": -1510.9265018548092,
    "total_trades": 10498
  },
  "scores": {
    "exp_score": 6.085445905220556,
    "winrate": 8.524480853495904,
    "rr": 14.277575396805322,
    "mdd": 0,
    "consecutive": 0,
    "pf": 4.359486914240266,
    "roi": 0
  },
  "generated_at": "2025-12-14T15:21:55.144968"
}
```

---

**Report Generated**: 2025-12-14 15:21:55  
**Author**: PHASE35-2 Automation  
**Status**: Ready for Review
