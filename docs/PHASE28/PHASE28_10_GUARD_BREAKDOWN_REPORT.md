# PHASE28-10: Guard & Filter Breakdown Report

**Generated**: 2025-12-08 12:39:14

---

## 📊 Summary

- **Run ID**: `20251208_122050_shmi`
- **Timestamp**: `2025-12-08T12:20:53.067080` → `2025-12-08T12:32:20.182175`
- **Signal True**: 6,194
- **Guard Blocks Total**: 6,169
- **Orders Submitted**: 25
- **Conversion Rate**: **0.40%**

---

## 🚫 Guard Rejection Breakdown

| Rank | Reason | Count | % of Signals | Cumulative | Cumulative % |
|------|--------|-------|--------------|------------|--------------|
| 1 | `FILTER_COOLDOWN_ACTIVE` | 3,263 | 52.68% | 3,263 | 52.68% |
| 2 | `GUARD_PORTFOLIO_CAN_OPEN` | 2,284 | 36.87% | 5,547 | 89.55% |
| 3 | `FILTER_VOLUME_SPIKE` | 622 | 10.04% | 6,169 | 99.60% |

---

## 🔍 Top 3 Blocking Factors

### 🥇 #1: `FILTER_COOLDOWN_ACTIVE`

- **Count**: 3,263 (52.68% of signals)
- **Description**: Signal was blocked due to active cooldown period after recent signal.

### 🥈 #2: `GUARD_PORTFOLIO_CAN_OPEN`

- **Count**: 2,284 (36.87% of signals)
- **Description**: Signal was blocked by PortfolioManager (max_positions, exposure, or budget cap).

### 🥉 #3: `FILTER_VOLUME_SPIKE`

- **Count**: 622 (10.04% of signals)
- **Description**: Signal was blocked due to abnormal volume spike detection.

---

## 💡 Recommendations

### 1. Cooldown Optimization

- The cooldown filter is the **#1 blocking factor**.
- **Action**: Review and relax cooldown parameters in `signals/signal_generator.py`.
- **Config Key**: `cooldown_minutes` (currently applied per signal side).

### 2. Portfolio Guard Refinement

- `GUARD_PORTFOLIO_CAN_OPEN` is blocking a significant portion of signals.
- **Action**: Analyze `PortfolioManager.can_open_position()` logic.
- **Possible causes**: max_positions, exposure limits, budget cap.

### 3. Volume Spike Filter Review

- Volume spike filter is blocking signals during high volatility.
- **Action**: Consider adjusting `vol_spike_mult` or disabling in trending markets.

---

## 📝 Notes

- This report is purely **diagnostic**. No strategy logic or guard parameters were changed in PHASE28-10.
- Use this analysis as input for PHASE28-11 (Guard Optimization).
