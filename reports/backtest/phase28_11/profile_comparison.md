# PHASE28-11: Profile Comparison Report

**Generated**: 2025-12-08T18:53:36.975333
**Phase**: PHASE28-11
**Objective**: Guard Optimization V1 - Profile Comparison

---

## 📊 Profile Summary

| Profile | Signal True | Guard Blocks | Orders | Conversion Rate | Status |
|---------|-------------|--------------|--------|-----------------|--------|
| **A: BASELINE** | 6,194 | 6,179 (99.8%) | 15 | **0.24%** | 🔴 LOW |
| **B: COOLDOWN_RELAXED** | 6,194 | 6,179 (99.8%) | 15 | **0.24%** | 🔴 LOW |
| **C: PORTFOLIO_RELAXED** | 6,194 | 6,179 (99.8%) | 15 | **0.24%** | 🔴 LOW |
| **D: MIXED_RELAXED** | 6,194 | 6,186 (99.9%) | 8 | **0.13%** | 🔴 LOW |

---

## 🔍 Detailed Analysis

### A: BASELINE

**Key Metrics**:
- Signal True: **6,194**
- Guard Blocks: **6,179** (99.8%)
- Orders Submitted: **15**
- Conversion Rate: **0.24%**

**Top Blocking Factors**:

| Rank | Reason | Count | % of Signals |
|------|--------|-------|--------------|
| 🥇 | `GUARD_PORTFOLIO_CAN_OPEN` | 6,179 | 99.76% |

---

### B: COOLDOWN_RELAXED

**Key Metrics**:
- Signal True: **6,194**
- Guard Blocks: **6,179** (99.8%)
- Orders Submitted: **15**
- Conversion Rate: **0.24%**

**Top Blocking Factors**:

| Rank | Reason | Count | % of Signals |
|------|--------|-------|--------------|
| 🥇 | `GUARD_PORTFOLIO_CAN_OPEN` | 6,179 | 99.76% |

---

### C: PORTFOLIO_RELAXED

**Key Metrics**:
- Signal True: **6,194**
- Guard Blocks: **6,179** (99.8%)
- Orders Submitted: **15**
- Conversion Rate: **0.24%**

**Top Blocking Factors**:

| Rank | Reason | Count | % of Signals |
|------|--------|-------|--------------|
| 🥇 | `GUARD_PORTFOLIO_CAN_OPEN` | 6,179 | 99.76% |

---

### D: MIXED_RELAXED

**Key Metrics**:
- Signal True: **6,194**
- Guard Blocks: **6,186** (99.9%)
- Orders Submitted: **8**
- Conversion Rate: **0.13%**

**Top Blocking Factors**:

| Rank | Reason | Count | % of Signals |
|------|--------|-------|--------------|
| 🥇 | `GUARD_PORTFOLIO_CAN_OPEN` | 5,981 | 96.56% |
| 🥈 | `FILTER_VOLUME_SPIKE` | 205 | 3.31% |

---

## 💡 Recommendations

### ⚠️ Profile D (MIXED_RELAXED) - Below Target

- **Conversion Rate**: 0.13% (Target: 3~5%)
- **Status**: Further optimization required.

### Comparison: B (Cooldown) vs C (Portfolio)

- **Profile B Conversion**: 0.24%
- **Profile C Conversion**: 0.24%

**Insight**: Both cooldown and portfolio relaxation have **similar impact**.

## 🚀 Next Steps

1. **PHASE28-12**: Fine-tune parameters based on Profile D (if target achieved)
2. **PHASE28-13**: Multi-Period Validation (Bull/Bear/Range)
3. **PHASE29**: Paper Trading validation (30 days)

---

## 📝 Notes

- This report compares **4 Guard Optimization profiles** (PHASE28-11).
- All backtests use the **same 3-month period** (2024-10-01 ~ 2024-12-31).
- Strategy: `btc5m_baseline_v2` (PHASE28-6/7 design).
- Symbol: BTCUSDT (5m timeframe).
