# PHASE36-0: AC2-4 검증 완료 보고서

## Executive Summary

**목표**: PHASE36-0 Smoke 20m AC2-4 검증 (persist_trace, DB insert, report JSON 생성)  
**결과**: ✅ **ALL PASS** - AC1-5 전체 통과  
**기간**: 2025-12-21 16:24 ~ 17:02 (실행 20분)  
**상태**: PHASE36-0-D1 완료

---

## 문제 정의

### 초기 상태 (15:05 실행)
```
AC1 (trades > 0): 7 trades → ✅ PASS
AC2 (DB persist 100%): 0/7 → ❌ FAIL
AC3 (persist_trace): 0 calls → ❌ FAIL
AC4 (report JSON): 0 files → ❌ FAIL
AC5 (run complete): PASS → ✅ PASS
```

**근본 원인**: persist_trace 계측 미설치 → save_trade_to_db import 경로 오류

---

## Root Cause Analysis

### 버그 1: save_trade_to_db import 경로 오류
**위치**: `scripts/phase36/run_phase36_0_paper_validation_pack.py:99`  
**증상**: `from database.postgres import save_trade_to_db` → ImportError (함수 없음)  
**실제 위치**: `execution.engine.save_trade_to_db` (L2921)  
**영향**: persist_trace 계측 설치 실패 → db_persist_called=0, db_insert_success=0

```python
# Before (L99-104)
from database.postgres import save_trade_to_db  # ❌ 존재하지 않음
_original_save_trade_to_db = save_trade_to_db
import database.postgres
database.postgres.save_trade_to_db = instrumented_save_trade_to_db

# After (L99-106)
from execution.engine import save_trade_to_db  # ✅ 정확한 경로
_original_save_trade_to_db = save_trade_to_db
import execution.engine
execution.engine.save_trade_to_db = instrumented_save_trade_to_db
```

### 버그 2: report JSON 생성 로직 누락
**위치**: Paper 모드 runner  
**증상**: Backtest는 engine에서 자동 생성하지만, Paper는 runner에서 명시적 생성 필요  
**영향**: AC4 (report JSON 생성) FAIL

**수정**: `save_artifacts()`에 report JSON 생성 로직 추가 (L461-486)
```python
report_dir = PROJECT_ROOT / "reports" / "paper"
report_dir.mkdir(parents=True, exist_ok=True)

report_json_path = report_dir / f"paper_{config.get('run_id', timestamp)}.json"
report_json_data = {
    "run_id": config.get("run_id"),
    "mode": "paper",
    ...
}
with open(report_json_path, "w", encoding="utf-8") as f:
    json.dump(report_json_data, f, indent=2, ensure_ascii=False)
```

### 버그 3: AC 체크 순서 문제
**위치**: `scripts/phase36/run_phase36_0_paper_validation_pack.py:568-572`  
**증상**: AC 체크 → Artifacts 저장 순서로 인해 AC4가 report_files=[] 판정  
**수정**: Artifacts 저장 → AC 체크 순서로 변경 + report_json_path 인자 전달

```python
# Before
ac_results = check_acceptance_criteria(...)  # AC4: report_files=[]
trace_path, results_path = save_artifacts(..., ac_results)

# After
trace_path, results_path, report_json_path = save_artifacts(..., {})  # 먼저 저장
ac_results = check_acceptance_criteria(..., report_json_path=report_json_path)  # 경로 전달
```

---

## Solution Implementation

### 수정 파일 (5개)

1. **scripts/phase36/run_phase36_0_paper_validation_pack.py**
   - L99-106: persist_trace import 경로 수정 (database.postgres → execution.engine)
   - L346: check_acceptance_criteria() 시그니처에 report_json_path 인자 추가
   - L367-376: AC4 체크 로직 개선 (report_json_path 우선 체크)
   - L461-486: report JSON 생성 로직 추가
   - L488: save_artifacts() return 값에 report_json_path 추가
   - L568-572: Artifacts 저장 → AC 체크 순서 변경

2. **requirements-dev.txt**
   - L10: `pytest-timeout>=2.1.0` 추가 (HANG 방지)

3. **pytest.ini**
   - L7: `--timeout=180 --timeout-method=thread` 추가

---

## Validation Results

### Run 최종 (16:41-17:02)
**Run ID**: `20251221_164154_mpu5`  
**Duration**: 0.34h (20.2분)  
**Candles**: 6,004개  
**Trades**: 8건 (진입 8, 청산 8)  
**Strategy Calls**: 6,004회 (성공률 100%)

### AC 검증 결과

```
AC1 (trades > 0): 8 trades → ✅ PASS
AC2 (DB persist 100%): 8/8 → ✅ PASS
AC3 (persist_trace): 8 calls → ✅ PASS
AC4 (report JSON): paper_20251221_164154_mpu5.json → ✅ PASS
AC5 (run complete): PASS → ✅ PASS

✅ ALL PASS
```

### Artifacts 생성 확인

1. **Trace JSON**: `artifacts/phase36/phase36_0/runs/phase36_0_L4_SMOKE_smoke_20251221_170206_trace.json`
   ```json
   {
     "persist_trace": {
       "db_persist_called": 8,
       "db_insert_success": 8
     },
     "db_evidence": {
       "total_trades": 8,
       "trial_trades": 8
     }
   }
   ```

2. **Results JSON**: `artifacts/phase36/phase36_0/results/phase36_0_L4_SMOKE_smoke.json`

3. **Report JSON**: `reports/paper/paper_20251221_164154_mpu5.json`
   ```json
   {
     "run_id": "20251221_164154_mpu5",
     "mode": "paper",
     "stage": "smoke",
     "trades": 8,
     "db_persist_success": 8
   }
   ```

### Contract Tests

**pytest**: 24/24 PASS (0.13s)
- `pytest-timeout` 설정 적용 (180s, thread method)
- 모든 계약 테스트 통과

---

## 재발 방지

### 1. Import 경로 명확화
- ❌ `database.postgres.save_trade_to_db` (존재하지 않음)
- ✅ `execution.engine.save_trade_to_db` (L2921, 실제 위치)

### 2. Paper 모드 Report JSON 생성 강제
- Backtest: engine에서 자동 생성
- Paper: runner에서 명시적 생성 필요 (save_artifacts에 포함)

### 3. AC 체크 순서 표준화
- **원칙**: Artifacts 생성 → AC 체크 (생성된 파일 경로 전달)
- **이유**: AC 체크 시점에 모든 artifacts가 존재해야 정확한 판정 가능

### 4. pytest-timeout 표준화
- **설정**: 180s, thread method
- **적용**: pytest.ini addopts
- **효과**: HANG 방지 + 자동 중단

---

## 최종 판정

**상태**: ✅ **COMPLETE**  
**AC 결과**: 5/5 PASS  
**증거**:
- Trace: `artifacts/phase36/phase36_0/runs/phase36_0_L4_SMOKE_smoke_20251221_170206_trace.json`
- Report: `reports/paper/paper_20251221_164154_mpu5.json`
- DB trades: 8건 (mode='paper', trial_id='20251221_164154_mpu5')

---

## 다음 단계

1. ✅ Git commit/push (변경 파일 5개)
2. Compare URL 생성 (BASE: e29786c → HEAD)
3. PHASE_ROADMAP.md 업데이트 (PHASE36-0 완료 반영)
