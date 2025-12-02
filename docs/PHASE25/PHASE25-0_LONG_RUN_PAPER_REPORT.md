# PHASE25-0: Long-run PAPER Regression - 실행 리포트

**Date**: 2025-12-02 17:24:04  
**Status**: ❌ FAIL  
**Config**: `configs\paper\phase25_0_long_run_2h.yml`  
**Duration**: 0.1H (목표), 0.00H (실제)  

---

## 1. Executive Summary

- **실행 시작**: 2025-12-02T17:23:58.024806
- **실행 종료**: 2025-12-02T17:24:03.309659
- **Duration**: 0.00H (5초)
- **Trade 수**: 0
- **활성 포지션**: 0
- **ERROR/CRITICAL**: 10257 / 63
- **최종 판정**: ❌ FAIL

---

## 2. Acceptance Criteria

| 항목 | 조건 | 결과 | 판정 |
|------|------|------|------|
| Duration | ≥ 0.10H | 0.00H | ❌ |
| ERROR/CRITICAL | = 0 | 10257 / 63 | ❌ |
| Trade 수 | ≥ 50 | 0 | ❌ |
| 활성 포지션 | = 0 | 0 | ✅ |
| Ensemble Aggregate | ≥ 1000 | 45669 | ✅ |

---

## 3. 메트릭 상세

### 3.1 DB 메트릭
```json
{
  "trade_count": 0,
  "entry_count": 0,
  "exit_count": 0,
  "active_positions": 0,
  "time_range": {
    "start": "2025-12-02T17:23:58.024806",
    "end": "2025-12-02T17:24:03.309659"
  }
}
```

### 3.2 로그 메트릭
```json
{
  "ensemble_aggregate_count": 45669,
  "tier1_count": 0,
  "tier2_count": 0,
  "skip_count": 0,
  "error_count": 10257,
  "critical_count": 63
}
```

### 3.3 Duration 메트릭
```json
{
  "start_time": "2025-12-02T17:23:58.024806",
  "end_time": "2025-12-02T17:24:03.309659",
  "actual_duration_sec": 5.284853,
  "actual_duration_hours": 0.0014680147222222223
}
```

---

## 4. 모니터링 결과

- **상태**: FAIL
- **ERROR 라인 수**: 1

### ERROR 라인 샘플:
```
2025-12-02 00:11:34,096 [WARNING] ⚠️ Redis 연결 실패 (1/3): Error 11001 connecting to ${REDIS_HOST}:6379. getaddrinfo failed. - 2초 후 재시도...
```

---

## 5. 최종 판정

❌ **FAIL** - 일부 Acceptance 조건 미충족

실패한 조건: duration_pass, error_pass, trade_pass

재실행 또는 코드 수정이 필요합니다.
