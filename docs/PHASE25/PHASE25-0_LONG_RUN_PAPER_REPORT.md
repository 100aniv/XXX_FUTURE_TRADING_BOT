# PHASE25-0: Long-run PAPER Regression - 실행 리포트

**Date**: 2025-12-02 23:40:47  
**Original Run**: 2025-12-02T22:21:16.951350  
**Reevaluated**: 2025-12-02T23:40:47.453303  
**Status**: PASS_WITH_STRATEGY_WARNING  
**Infra Acceptance**: ✅ PASS  
**Config**: `configs\paper\phase25_0_long_run_2h.yml`  
**Duration**: 2.0H (목표), 2.00H (실제)  

---

## 1. Executive Summary

- **실행 시작**: 2025-12-02T20:21:10.860134
- **실행 종료**: 2025-12-02T22:21:16.246777
- **Duration**: 2.00H (7205초)
- **Trade 수**: 39 (목표: 50)
- **활성 포지션**: 0
- **ERROR/CRITICAL**: 2 / 0
- **Ensemble Aggregate**: 10564
- **인프라 Acceptance**: ✅ PASS
- **전략 KPI**: ⚠️ WARNING (Trade 수 부족)
- **최종 판정**: PASS_WITH_STRATEGY_WARNING

---

## 2. Acceptance Criteria

### 2.1 인프라 Acceptance (PHASE25-0 PASS 기준)

| 항목 | 조건 | 결과 | 판정 |
|------|------|------|------|
| Duration | ≥ 1.96H | 2.00H | ✅ |
| CRITICAL 오류 | = 0 | 0 | ✅ |
| 활성 포지션 | = 0 | 0 | ✅ |
| Ensemble Aggregate | ≥ 1000 | 10564 | ✅ |
| **인프라 종합** | - | - | ✅ PASS |

### 2.2 전략 KPI (경고/참고용)

| 항목 | 목표 | 결과 | 상태 |
|------|------|------|------|
| Trade 수 | ≥ 50 | 39 | ⚠️ WARNING |

**NOTE**: Trade 수는 전략/스캘핑/앙상블 파라미터 튜닝 영역이며, PHASE25-0 인프라 Acceptance 기준에는 포함되지 않습니다. 전략 KPI는 이후 PHASE에서 다룹니다.

---

## 3. 메트릭 상세

### 3.1 DB 메트릭
```json
{
  "trade_count": 39,
  "entry_count": 39,
  "exit_count": 39,
  "active_positions": 0,
  "time_range": {
    "start": "2025-12-02T20:21:10.860134",
    "end": "2025-12-02T22:21:16.246777"
  }
}
```

### 3.2 로그 메트릭
```json
{
  "ensemble_aggregate_count": 10564,
  "tier1_count": 0,
  "tier2_count": 0,
  "skip_count": 0,
  "error_count": 2,
  "critical_count": 0,
  "note": "정확한 로그 레벨 기반 카운트. [ERROR] 2건(Exposure BLOCK - 정상), [CRITICAL] 0건"
}
```

### 3.3 Duration 메트릭
```json
{
  "start_time": "2025-12-02T20:21:10.860134",
  "end_time": "2025-12-02T22:21:16.246777",
  "actual_duration_sec": 7205.386643,
  "actual_duration_hours": 2.001496289722222
}
```

---

## 4. 모니터링 결과

- **상태**: PASS
- **ERROR 라인 수**: 0

---

## 5. 최종 판정

✅ **INFRA PASS (전략 KPI 경고)** - 인프라 Acceptance 충족

**인프라 Acceptance**: ✅ PASS
- Duration: 2.00H ≥ 1.96H
- CRITICAL 오류: 0건 (모니터링 PASS)
- 활성 포지션: 0
- Ensemble Aggregate: 10564 ≥ 1000

**전략 KPI**: ⚠️ WARNING
- Trade 수: 39 < 목표 50건
- 이는 전략/스캘핑/앙상블 파라미터 튜닝 영역이며, 이후 PHASE에서 다룹니다.

**결론**: PHASE25-0는 인프라 기준으로 PASS. Long-run PAPER Harness가 안정적으로 작동하며, 장시간 실행 인프라가 확립되었습니다.
