# PHASE29-6: AC3 Performance Analysis

**분석일**: 2025-12-11 15:02:50

---

## Executive Summary

- **총 분석**: 4개
- **AC3 PASS**: 0개
- **AC3 FAIL**: 4개

**AC3 기준**:
- Win Rate >= 45%
- Max Drawdown <= 15%

---

## 상세 결과

### 1. 1M Gate Baseline

**Config**: baseline (no guard)

| 지표 | 값 | AC3 |
|------|-----|-----|
| Trades | 140 | - |
| Win Rate | 27.9% | ❌ |
| Max DD | 23.2% | ❌ |
| PnL Total | -2245.21 USDT | - |
| Sharpe Ratio | -4.59 | - |
| Profit Factor | 0.53 | - |
| ROI | -22.5% | - |
| **AC3 판정** | **FAIL** | ❌ |

### 2. Top 1: r2_t2_rr1.0_cd0

**Config**: range=2, trend=2, RR=1.0, CD=0

| 지표 | 값 | AC3 |
|------|-----|-----|
| Trades | 500 | - |
| Win Rate | 30.4% | ❌ |
| Max DD | 64.6% | ❌ |
| PnL Total | -6353.10 USDT | - |
| Sharpe Ratio | -3.55 | - |
| Profit Factor | 0.60 | - |
| ROI | -63.5% | - |
| **AC3 판정** | **FAIL** | ❌ |

### 3. Top 2: r2_t2_rr1.0_cd1

**Config**: range=2, trend=2, RR=1.0, CD=1

| 지표 | 값 | AC3 |
|------|-----|-----|
| Trades | 500 | - |
| Win Rate | 30.4% | ❌ |
| Max DD | 64.6% | ❌ |
| PnL Total | -6353.10 USDT | - |
| Sharpe Ratio | -3.55 | - |
| Profit Factor | 0.60 | - |
| ROI | -63.5% | - |
| **AC3 판정** | **FAIL** | ❌ |

### 4. Top 3: r2_t3_rr1.0_cd0

**Config**: range=2, trend=3, RR=1.0, CD=0

| 지표 | 값 | AC3 |
|------|-----|-----|
| Trades | 500 | - |
| Win Rate | 30.4% | ❌ |
| Max DD | 64.6% | ❌ |
| PnL Total | -6353.10 USDT | - |
| Sharpe Ratio | -3.55 | - |
| Profit Factor | 0.60 | - |
| ROI | -63.5% | - |
| **AC3 판정** | **FAIL** | ❌ |

---

## PHASE29-4 AC3 최종 판정

❌ **FAIL** - AC3 기준을 충족하는 조합 없음

