# PHASE36-0 Smoke SSOT Plan

## 변경 범위 (이번 턴 3가지만)

### 1. persist_trace Instrumentation SSOT
**파일**: `scripts/phase36/run_phase36_0_paper_validation_pack.py`
**함수**: `install_trace_instrumentation()`
**변경**:
- import 경로: `execution.engine.save_trade_to_db` 확정
- instrumentation 실패 시 raise (try/except 삼키기 금지)
- persist_trace 필드: `db_persist_called`, `db_insert_success`, `db_insert_fail`, `last_exception`

### 2. Report JSON SSOT (AC4)
**파일**: `scripts/phase36/run_phase36_0_paper_validation_pack.py`
**함수**: `main()`, `check_acceptance_criteria()`, `save_artifacts()`
**변경**:
- report JSON 생성 시점: AC 체크 **이전**으로 이동
- report JSON 경로: `reports/paper/paper_<run_id>.json`
- AC4 판정: `report_json_path.exists()` 사용
- AC JSON에 `report_json_path`, `report_files` 명시

### 3. D 표기 전면 제거
**파일**: 
- `docs/PHASE36/*.md` (모든 마크다운)
- `PHASE_ROADMAP.md`
- `scripts/phase36/*.py` (주석 포함)
**변경**:
- `PHASE36-0-D1/D2` → `PHASE36-0-AC2-4` 또는 `PHASE36-0`
- `D단계` → `단계` 또는 `작업`
- `-D[0-9]` → 제거

## 변경하지 않는 것
- `execution/engine.py` (DO-NOT-TOUCH 코어)
- 기존 config 파일
- 기존 테스트 파일 (contract 제외 가능)
