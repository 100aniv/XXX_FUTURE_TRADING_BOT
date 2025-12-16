# PHASE35-3 ITER13: IS vs OOS Comparison

**Date**: 2025-12-16  
**Note**: Summary values corrected using `backtest_report.json` metrics (runner bug workaround)

---

## Window Definitions

| Split | Date Range | Days | Label |
|-------|------------|------|-------|
| **IS (In-Sample)** | 2024-11-01 ~ 2024-11-30 | 30 | Nov 2024 (Election Month) |
| **OOS (Out-of-Sample)** | 2024-12-01 ~ 2024-12-14 | 14 | Dec 2024 (First Half) |

---

## KPI Comparison

| Metric | IS | OOS | Delta | Delta % | Status |
|--------|----|----|-------|---------|--------|
| **Trades** | 10,498 | 4,917 | -5,581 | -53.2% | ✅ Both >0 |
| **Win Rate (%)** | 28.41 | 28.80 | +0.39 | +1.4% | ✅ Stable |
| **Profit Factor** | 0.567 | 0.575 | +0.008 | +1.4% | ✅ Slight improvement |
| **Max Drawdown ($)** | -1,516.16 | -1,343.70 | +172.46 | -11.4% | ✅ Better (less drawdown) |
| **PnL ($)** | -1,510.93 | -1,338.82 | +172.11 | -11.4% | ⚠️ Both negative |
| **ROI (%)** | -15.11 | -13.39 | +1.72 | -11.4% | ⚠️ Both negative |
| **Risk/Reward Ratio** | 1.428 | 1.450 | +0.022 | +1.5% | ✅ Stable |
| **Consecutive Losses** | 40 | 50 | +10 | +25.0% | ⚠️ Worse |

---

## Analysis

### ✅ Strengths

1. **Trade Generation**: Both windows generate **thousands of trades**
   - IS: 10,498 trades (30 days)
   - OOS: 4,917 trades (14 days)
   - Trade density consistent: ~350 trades/day

2. **Win Rate Stability**: 28.41% → 28.80% (+0.39pp)
   - Minimal degradation
   - OOS slightly better than IS

3. **Profit Factor Consistency**: 0.567 → 0.575 (+1.4%)
   - No significant edge erosion

4. **Drawdown Improvement**: -1,516 → -1,344 ($172 less)
   - Better risk control in OOS

### ⚠️ Concerns

1. **Negative PnL**: Both IS and OOS are **net negative**
   - Strategy is currently **losing money**
   - PF < 1.0 indicates losses > wins

2. **High Trade Frequency**: ~350 trades/day = very high churn
   - Likely scalping/mean reversion over-trading
   - Transaction costs could be killing profitability

3. **Consecutive Losses**: 40 → 50
   - Longer losing streaks in OOS
   - Risk of psychological/capital stress

### 🔍 Root Cause Hypothesis

**Strategy is signal-rich but edge-poor**:
- Generates many signals (ensemble voting works)
- But individual trades have **negative expectancy**
- Likely issues:
  1. **Over-trading**: Cooldown too short (3 bars = 45min)
  2. **Poor entries**: Confidence threshold too low (0.70)
  3. **TP/SL imbalance**: Risk/Reward ~1.4 but WinRate only 28%
  4. **Regime mismatch**: May be trading in unfavorable market conditions

---

## Recommendation

### Short-term: Accept ITER13 as **PARTIAL PASS**

**Why**:
- ✅ EC1: Window found (Nov + Dec)
- ✅ EC2: 1M baseline executed (IS)
- ✅ EC3: OOS validated
- ✅ EC4: trades>0 confirmed
- ✅ Stability: KPIs consistent IS→OOS
- ⚠️ Profitability: Negative PnL (but not ITER13 scope)

**Verdict**: ITER13 **infrastructure validation = PASS**, strategy profitability = separate issue

### Long-term: PHASE35-4 - Strategy Tuning

Next phase should address:
1. **Trade Frequency Reduction**:
   - Increase cooldown: 3 bars → 8-12 bars (2-3 hours)
   - Raise confidence threshold: 0.70 → 0.75-0.80

2. **Entry Quality Filter**:
   - Add volume confirmation
   - Strengthen regime filter (avoid CHOP)

3. **Risk Management**:
   - Widen stops or tighten TPs
   - Target RR >2.0 with WR >30%

4. **Transaction Cost Modeling**:
   - Add realistic fees/slippage
   - May reveal true profitability

---

## Conclusion

**ITER13 Status**: ✅ **PASS** (Infrastructure + Validation)

**Evidence**:
- Window scan successful (trades>0)
- IS baseline: 10,498 trades
- OOS validation: 4,917 trades
- KPI stability: WinRate ±0.4pp, PF ±1.4%
- Reproducibility: Git commit, config hash tracked

**Next**: Proceed to ITER14 (12h Paper Test) or PHASE35-4 (Strategy Tuning)

---

**Generated**: 2025-12-16 21:42:00  
**Commit**: a6e6d5c69a1c5efdcb22f4c22ff3dcd9bb8b1571
