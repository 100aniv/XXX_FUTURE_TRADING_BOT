# PHASE28-8-1: Extended Baseline Deep Dive Report

**Date**: 2025-12-08 08:36:54  
**Period**: 2024-08-01 ~ 2024-10-31 (3개월, 92일)  
**Strategy**: btc5m_baseline_v2  
**Mode**: Baseline Parameters (No Tuning)

---

## 📊 Executive Summary

### 전체 성능 메트릭

| Metric | Value | Target (PHASE28-6) | Status |
|--------|-------|---------------------|--------|
| **Trial ID** | phase28_8_btc5m_baseline_v2_3m_v2 | - | - |
| **Trade Count** | 10 | ≥ 60 (20/month × 3) | ❌ |
| **Win Rate** | 30.0% | ≥ 40% | ❌ |
| **Sharpe Ratio** | -0.3323 | ≥ 0.0 | ❌ |
| **Total PnL** | $-152.62 | Positive | ❌ |
| **Total Return** | -0.31% | Positive | ❌ |
| **Max Drawdown** | 0.4% | ≤ 20% | ✅ |
| **Final Equity** | $49847.38 | > $50,000 | ❌ |
| **Profit Factor** | 0.493 | ≥ 1.5 | ❌ |

### Trade Breakdown

| Side | Count | % |
|------|-------|---|
| **LONG** | 4 | 40.0% |
| **SHORT** | 6 | 60.0% |

### Win/Loss Breakdown

| Type | Count | Avg PnL |
|------|-------|---------|
| **Wins** | 3 | $49.52 |
| **Losses** | 7 | $-43.02 |

---

## 🔍 Signal → Order → Trade Funnel Analysis

### Funnel Metrics

| Stage | Count | Conversion Rate |
|-------|-------|-----------------|
| **Signals Generated** | 8576 | 100% |
| **Orders Submitted** | 10 | 0.12% |
| **Trades Executed** | 10 | - |

**핵심 발견**:
- Signal → Order 전환율: **0.12%**
- ⚠️ 극도로 낮은 전환율 (대부분 Guard/Portfolio에서 차단)

### Regime Distribution

| Regime | Count | % |
|--------|-------|---|
| **Trend** | 0 | 0.0% |
| **Range** | 2828 | 100.0% |

**핵심 발견**:
- ⚠️ Regime Trend가 거의 감지되지 않음 (Bull/Bear 구간 포함)
- Range 편향이 심각함

### Signal Breakdown

| Direction | Count | % |
|-----------|-------|---|
| **LONG** | 4084 | 47.6% |
| **SHORT** | 4492 | 52.4% |


---

## 📈 Daily Performance

| Date | Trades | Wins | Win Rate | Daily PnL |
|------|--------|------|----------|----------|
| 2025-12-08 | 10 | 3 | 30.0% | $-152.62 |

---

## 🎯 핵심 문제 포인트

### 1. Trade Count 극도로 부족
- **관찰**: 3개월(10건) vs 목표(60건)
- **원인**: Signal → Order 전환율 0.12%
- **영향**: 목표 대비 83.3% 부족

### 2. Regime Detection 오작동
- **관찰**: Trend Regime 0건 vs Range 2828건
- **원인**: ADX/DI threshold 너무 높거나 로직 오류
- **영향**: Dynamic Threshold가 제대로 작동 안함

### 3. 성능 메트릭
- **Win Rate**: 30.0% (목표: 40%)
- **Sharpe Ratio**: -0.3323 (목표: ≥ 0)
- **Profit Factor**: 0.493 (목표: ≥ 1.5)

---

## 💡 권장 조치

### 긴급 (PHASE28-8-2)
1. **Regime Detection 디버깅**
   - ADX threshold 0건 → 500+ 목표
   - DI+/DI- 분리 조건 재검토
   
2. **Guard/Portfolio 완화**
   - Signal 8576개 → Order 10건 전환율 개선
   - Budget Cap/Cooldown 조정

3. **Dynamic Threshold 재조정**
   - RSI percentile 범위 확대
   - BB multiplier 하향

### 중기 (PHASE29)
- 전략 패밀리 재평가 (Mean Reversion vs Trend Following)
- 파라미터 공간 재설계
- Light Random Search로 생존 가능성 재확인

---

**Last Updated**: 2025-12-08 08:36:54
