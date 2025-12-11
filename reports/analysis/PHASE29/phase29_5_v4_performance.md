# PHASE29-5: V4 Performance Metrics Analysis

**생성 시각**: 2025-12-11 12:58:47

---

## 1. Executive Summary

- **총 조합 수**: 24개 (1M Gate 포함 시 25개)
- **AC3 통과**: 0개 (Win Rate >= 45% & Max DD <= 15%)
- **AC3 실패**: 24개

## 2. 1M Gate Baseline Performance

⚠️ 1M Gate 결과 없음

## 3. Top 5 Tuning Combinations

**정렬 기준**: AC3 통과 > Sharpe Ratio > PnL Total > Max DD (낮을수록)

| Rank | Run ID | Range | Trend | min_rr | CD | Trades | Win Rate | Max DD | PnL | Sharpe | AC3 |
|------|--------|-------|-------|--------|----|---------|-----------|---------|----- |--------|-----|
| 1 | `20251211_023512_ymh6...` | - | - | - | - | 500 | 30.4% | 64.6% | -6353.1 | -3.55 | ❌ |
| 2 | `20251211_023919_qayu...` | - | - | - | - | 500 | 30.4% | 64.6% | -6353.1 | -3.55 | ❌ |
| 3 | `20251211_024328_8ko4...` | - | - | - | - | 500 | 30.4% | 64.6% | -6353.1 | -3.55 | ❌ |
| 4 | `20251211_024728_0ux0...` | - | - | - | - | 500 | 30.4% | 64.6% | -6353.1 | -3.55 | ❌ |
| 5 | `20251211_025112_gb2y...` | - | - | - | - | 500 | 30.4% | 64.6% | -6353.1 | -3.55 | ❌ |

## 4. AC3 Pass/Fail Distribution

- ✅ **PASS**: 0개
- ❌ **FAIL**: 24개

## 5. Performance Metrics Summary (All Combinations)

- **평균 Win Rate**: 30.40%
- **평균 Max DD**: 64.56%
- **평균 PnL**: -6353.10 USDT

## 6. Next Steps

1. **AC3 통과 조합** → PHASE30 앙상블 통합 후보
2. **상위 3-5개 조합** → Paper Trading 검증
3. **AC3 실패 조합** → 파라미터 재조정 또는 제외
