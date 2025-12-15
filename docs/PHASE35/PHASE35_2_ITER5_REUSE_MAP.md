# PHASE35-2 ITER5: 재사용 가능 컴포넌트 맵

**작성일**: 2025-12-15  
**목적**: ITER5 작업 전 기존 인프라 스캔 및 오염 지점 식별

---

## 1. 기존 러너 인프라

### 1.1 메인 러너
**파일**: `scripts/phase35/run_7d_ssot.py` (ITER4 버전)

**현재 구조**:
```python
# Run ID 생성
run_id = f"phase35_2_iter4_run{run_number}_{timestamp}"

# 결과 파일 경로
summary_path = "artifacts/phase35/iter4/iter4_run{N}_summary.json"
effective_config = "artifacts/phase35/iter4/effective_config_run{N}.yaml"

# 리포트 파일 찾기 (⚠️ 오염 지점)
report_files = [
    f for f in (project_root / "reports" / "backtest").glob("*.json")
    if f.stat().st_mtime > backtest_start_time  # 10분 이내 필터
]
latest_report = report_files[-1] if report_files else None
```

**문제점**:
- ✅ 시간 기반 필터링으로 개선됨 (ITER4)
- ❌ 여전히 "글롭"으로 찾아서 오염 가능성 존재
- ❌ 리포트 생성 실패 시 기본값 0 처리 (땜빵)

### 1.2 기타 러너들
- `run_7d_smoke_test.py`: 구버전 (사용 중단)
- `run_7d_smoke_test_v2.py`: V2 버전
- `run_iter2_7d_fast.py`: ITER2 전용
- `run_iter3_simple.py`: ITER3 전용
- `run_fast_gate.py`: Fast Gate 테스트
- `run_tests_fast_gate.py`: Fast Gate 테스트 (중복?)

**재사용 권장**: `run_fast_gate.py` (Fast Gate 실행용)

---

## 2. 리포트 생성 인프라

### 2.1 메인 모듈
**파일**: `analytics/report_generator.py`

**주요 함수**:
```python
def generate_backtest_report(
    trial_id: str = None,
    table_name: str = "trades",
    schema: str = "trading",
    output_file: str = None,
    sinks: List[str] = None,
    output_dir: str = "reports"
) -> Dict[str, Any]
```

**출력**:
- JSON: `{output_file}.json` 또는 `reports/backtest/backtest_{timestamp}.json`
- HTML: `{output_file}.html` (sinks에 "html" 포함 시)
- 로그: TUNING_VIBLE 점수 출력

**현재 동작**:
1. PostgreSQL에서 trades 조회
2. TUNING_VIBLE 100점 계산
3. JSON/HTML 저장
4. result 딕셔너리 반환

### 2.2 엔진에서 호출
**파일**: `execution/engine.py:2676-2769`

```python
from analytics.report_generator import generate_backtest_report

# HTML 모드
if html_enabled:
    result = generate_backtest_report(
        trial_id=None,
        output_file=str(output_path),
        sinks=["log", "html", "json"]
    )

# JSON만 모드
else:
    result = generate_backtest_report(
        trial_id=None,
        output_file=str(output_path),
        sinks=["log", "json"]
    )

if result.get("status") == "success":
    logger.info("📊 백테스트 리포트 생성 완료")
else:
    logger.warning("⚠️ 백테스트 리포트 생성 실패")
```

**⚠️ 오염 지점 발견**:
- 엔진은 `output_path`를 지정하지만, 러너는 **이 경로를 모름**
- 러너는 `reports/backtest/*.json`을 glob으로 찾음
- **구조적 오염 가능성**: 다른 실행의 리포트를 잘못 읽을 수 있음

---

## 3. Symbol Unbound 버그 추적

### 3.1 엔진에서 symbol 사용
**파일**: `execution/engine.py`

**발견된 symbol 사용처**:
1. **Line 147-148**: 하위 호환 처리
   ```python
   if not symbols:
       symbol = config.get('symbol', 'BTCUSDT')
       symbols = [symbol]
   ```

2. **Line 501-502**: 하위 호환 처리 (symbols가 None일 때)
   ```python
   if symbols is None:
       symbol = config.get("symbol", "BTCUSDT")
       symbols = [symbol]
   ```

3. **Line 1101**: Candle에 symbol 키 없을 때 fallback
   ```python
   candle_symbol = config.get("symbol", "UNKNOWN")
   ```

### 3.2 리포트 생성기에서 symbol 사용
**파일**: `analytics/report_generator.py`

**검색 결과**: symbol 변수 직접 사용 없음 (DB에서 조회만)

### 3.3 근본 원인 추정
**ITER4 로그에서 발견**:
```
⚠️ 백테스트 리포트 생성 실패: cannot access local variable 'symbol' where it is not associated with a value
```

**추정 시나리오**:
1. 엔진에서 리포트 생성 호출 시점
2. 어딘가에서 `symbol` 변수를 참조하려 했으나 정의되지 않음
3. 가능성 1: 엔진 내부 로컬 변수 스코프 문제
4. 가능성 2: 리포트 생성기 또는 HTML 템플릿에서 symbol 참조

**조치 필요**:
- 엔진 코드 전체 스캔하여 symbol 변수의 모든 사용처 확인
- 리포트 생성 실패 시 예외 스택 트레이스 로깅 추가
- 안전한 기본값 설정 (config.get('symbol', 'UNKNOWN'))

---

## 4. 테스트 인프라

### 4.1 Fast Gate
**파일**: `scripts/phase35/run_fast_gate.py`

**기능**:
- Core imports 검증
- Config 로드 검증
- Strategy 초기화 검증

**재사용**: ✅ 그대로 사용 가능

### 4.2 Core Regression
**파일**: `tests/test_regression_imports.py`

**현재 상태**: 확인 필요 (ITER4에서 outdated 판정)

**조치 필요**:
- 테스트 실행 후 FAIL 원인 파악
- Outdated 테스트는 현재 코드에 맞게 수정 (삭제 금지)

---

## 5. 데이터 흐름 및 오염 경로 분석

### 5.1 현재 흐름 (ITER4)
```
[Runner] run_7d_ssot.py
    ↓
[Engine] run_v2()
    ↓
[Report] generate_backtest_report()
    ↓ output_file 지정
[File] reports/backtest/backtest_{timestamp}.json
    ↑ (글롭으로 찾음, 시간 필터)
[Runner] latest_report 읽기
    ↓
[Summary] artifacts/phase35/iter4/iter4_run{N}_summary.json
```

### 5.2 오염 가능 경로
1. **경로 1**: 리포트 생성 실패 → 이전 리포트 남아있음 → 러너가 오래된 파일 읽음
2. **경로 2**: 동시 실행 → 타임스탬프 겹침 → 잘못된 파일 읽음
3. **경로 3**: 수동 실행 잔여물 → reports/backtest에 다른 테스트 결과 존재

### 5.3 ITER5 개선 방향
**목표**: 구조적으로 오염 불가능한 격리 구조

```
[Run ID] phase35_2_iter5_run1_20251215_102530
    ↓
[Output Dir] artifacts/phase35/iter5/{run_id}/
    ├── effective_config.yaml
    ├── summary.json
    ├── report.json
    ├── report.html (optional)
    └── logs/
        └── engine.log
```

**핵심 변경**:
1. 리포트 경로를 runner가 엔진에 **명시적으로 전달**
2. 글롭 탐색 **완전 제거**
3. 리포트 생성 실패 시 runner **즉시 FAIL** (exit code != 0)
4. 모든 파일이 run_id 폴더에 격리

---

## 6. ITER5 재사용 컴포넌트 요약

| 컴포넌트 | 파일 | 재사용 | 수정 필요 |
|---------|------|--------|----------|
| 리포트 생성기 | `analytics/report_generator.py` | ✅ | ⚠️ symbol 버그 수정 |
| 엔진 | `execution/engine.py` | ✅ | ⚠️ symbol 스코프 확인 |
| 러너 기반 | `scripts/phase35/run_7d_ssot.py` | 🔄 | ⚠️ 격리 구조로 리팩터링 |
| Fast Gate | `scripts/phase35/run_fast_gate.py` | ✅ | ❌ 수정 불필요 |
| Core Regression | `tests/test_regression_imports.py` | ✅ | ⚠️ Outdated 수정 |
| Config 로더 | `run_7d_ssot.py:load_config()` | ✅ | ❌ 수정 불필요 |
| Deep Merge | `run_7d_ssot.py:deep_merge()` | ✅ | ❌ 수정 불필요 |

---

## 7. ITER5 우선순위 작업

### P0 (필수)
1. ✅ **symbol 버그 근본 수정**: 엔진/리포트 생성기에서 symbol 정의 보장
2. ✅ **러너 격리 구조**: run_id 기반 폴더, 글롭 제거, 명시적 경로 전달
3. ✅ **리포트 실패 FAIL**: 기본값 0 처리 제거, 실패 시 즉시 종료

### P1 (중요)
4. ✅ **Core Regression 수정**: Outdated 테스트를 현재 코드에 맞게 업데이트
5. ✅ **논리 일관성 assert**: blocked_ratio==1.0 ⇒ trades==0 검증

### P2 (권장)
6. ✅ **DecisionTrace Top Reasons**: Summary에 차단 사유 top-k 포함
7. ✅ **Data Hash**: 데이터 파일 해시 검증 (재현성 보장)

---

## 8. 체크리스트

- [x] Git status clean 확인 (Modified 4개 발견, ITER5 시작 전 정리 필요)
- [x] 오염 지점 pinpoint 완료 (글롭 탐색 + 리포트 경로 불일치)
- [x] 재사용 가능 컴포넌트 식별 완료
- [x] symbol 버그 근본 원인 추정 완료
- [ ] **다음**: Modified 파일 정리 후 STEP 1 진행

---

**작성 완료**: 2025-12-15 10:30
