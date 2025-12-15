# PHASE35-2 ITER1: 재사용 맵 & 신규 파일 목록

**생성일**: 2025-12-14  
**목적**: 오버리팩토링 방지 + 기존 모듈 최대 재사용

---

## 1) 재사용 모듈/스크립트

### 전략 로더
- **파일**: `strategies/__init__.py`
- **함수**: `load_strategies()`, `get_all_strategies()`
- **용도**: phase35_ensemble_v1 로드 + strict mode 검증
- **변경**: Strict mode 보강 (enabled인데 params 비어있음 → FAIL)

### 엔진
- **파일**: `execution/engine.py`
- **함수**: `run_v2()`
- **용도**: 백테스트 실행 (mode='backtest')
- **변경**: 최소 (로깅만 기존 유지)

### 기존 7D Smoke 러너
- **파일**: `scripts/phase35/run_7d_smoke_test.py`
- **용도**: 7D 백테스트 실행 (Run1/Run2)
- **변경**: Config 경로만 phase35_2_smoke_ssot.yaml로 변경

### 기존 Config 파일 (참조용)
- `configs/phase35/ensemble_v1.yaml` - 참조용 (복잡한 구조)
- `configs/phase35/test_simple.yaml` - 참조용 (간단한 구조)
- `configs/base.yml` - 기본 설정 (deep merge 베이스)

---

## 2) 신규 생성 파일 (이번 턴)

### 설정 파일
- **`configs/phase35/phase35_2_smoke_ssot.yaml`**
  - 목적: PHASE35-2 ITER1 SSOT (Single Source of Truth)
  - 기반: test_simple.yaml + 최소 튜닝 파라미터
  - 튜닝값:
    - ensemble.confidence_threshold: 0.75 (↑ 신호 품질)
    - ensemble.min_votes: 2 (2/3 합의)
    - ensemble.cooldown_bars: 2 (15m 기준 30분 쿨다운)
    - risk.per_trade: 0.005 (2% → 0.5%)
    - risk.max_leverage: 1 (3 → 1)
    - risk.max_position_size: 0.05 (0.1 → 0.05)
    - risk.cooldown_seconds: 1800 (300 → 1800)

- **`configs/phase35/phase35_3_1m_baseline.yaml`**
  - 목적: PHASE35-3 1M Baseline (조건부, PHASE35-2 PASS 시만 생성)
  - 기반: phase35_2_smoke_ssot.yaml (기간만 1M로 변경)
  - 값: 동일 유지 (불필요 변경 금지)

### 스크립트
- **`scripts/phase35/check_infra.py`**
  - 목적: Docker/DB/Redis 상태 확인
  - 기능: 포트 핑 + 간단 쿼리 + 상태 리포트

- **`scripts/phase35/run_7d_ssot.py`**
  - 목적: PHASE35-2 ITER1 7D Smoke 실행 (Run1/Run2)
  - 기반: run_7d_smoke_test.py 복사 + config 경로 고정
  - 기능: 
    - Run1 실행 + 결과 저장
    - Run2 실행 + 재현성 검증
    - 메트릭 비교 + 허용오차 판정

- **`scripts/phase35/run_tests_fast_gate.py`**
  - 목적: Fast Gate 테스트 자동 실행
  - 기능: 기존 18/18 SSOT로 pytest 실행 + 결과 판정

- **`scripts/phase35/run_tests_core_regression.py`**
  - 목적: Core Regression 테스트 자동 실행
  - 기능: 기존 12/12 SSOT로 pytest 실행 + 결과 판정

- **`scripts/phase35/fix_roadmap_encoding.py`**
  - 목적: PHASE_ROADMAP.md 인코딩 문제 해결
  - 기능: UTF-8 변환 + diff 확인

### 문서
- **`docs/PHASE35/PHASE35_2_ITER1_REPORT.md`**
  - 목적: PHASE35-2 ITER1 최종 보고서
  - 내용:
    - 변경 요약 (무엇을 왜 바꿨는지)
    - Run1/Run2 메트릭 표
    - DecisionTrace Top blockers (상위 10개)
    - AC 판정표 (각 항목 PASS/FAIL)
    - 재현성 판정 (허용오차 포함)

- **`docs/PHASE35/PHASE35_3_1M_BASELINE_REPORT.md`** (조건부)
  - 목적: PHASE35-3 1M Baseline 보고서
  - 생성: PHASE35-2 PASS 시만 생성

---

## 3) 변경 파일 (최소)

### 전략 코드
- **`strategies/phase35_ensemble_v1.py`**
  - 변경: _get_cfg() helper 추가 + 이중 경로 지원 강화
  - 범위: 설정 읽기 경로만 (로직 변경 금지)
  - 로깅: 실제 적용값 1회 INFO 로깅

### 전략 로더
- **`strategies/__init__.py`**
  - 변경: Strict mode 보강 (enabled인데 params 비어있음 → FAIL)
  - 범위: 검증 로직만 (기존 로드 로직 유지)

### 엔진
- **`execution/engine.py`**
  - 변경: 최소 (기존 로깅 유지)
  - 범위: 필요 시 ensemble config 검증 로깅만

---

## 4) 파일 구조 요약

```
configs/phase35/
├── phase35_2_smoke_ssot.yaml       ✨ NEW (SSOT)
├── phase35_3_1m_baseline.yaml      ✨ NEW (조건부)
├── ensemble_v1.yaml                (참조용)
├── test_simple.yaml                (참조용)
└── ensemble_v1_full.yaml           (참조용)

scripts/phase35/
├── check_infra.py                  ✨ NEW
├── run_7d_ssot.py                  ✨ NEW
├── run_tests_fast_gate.py          ✨ NEW
├── run_tests_core_regression.py    ✨ NEW
├── fix_roadmap_encoding.py         ✨ NEW
├── run_7d_smoke_test.py            (재사용, config 경로만 변경)
└── check_strategy_import.py        (기존)

docs/PHASE35/
├── PHASE35_2_ITER1_REPORT.md       ✨ NEW
├── PHASE35_3_1M_BASELINE_REPORT.md ✨ NEW (조건부)
├── PHASE35_2_SMOKE_REPORT.md       (기존)
└── PHASE35_2_ITER1_REUSE_MAP.md    (이 파일)

strategies/
├── __init__.py                     (변경: strict mode 보강)
└── phase35_ensemble_v1.py          (변경: _get_cfg() helper + 이중 경로)

execution/
└── engine.py                       (변경: 최소)
```

---

## 5) 변경 범위 정리

| 파일 | 변경 유형 | 범위 | 목적 |
|------|---------|------|------|
| phase35_ensemble_v1.py | 코드 추가 | _get_cfg() helper + 로깅 | 설정 경로 표준화 |
| __init__.py | 검증 강화 | Strict mode 보강 | Silent skip 방지 |
| engine.py | 로깅 | 최소 | 기존 유지 |
| phase35_2_smoke_ssot.yaml | 신규 | 전체 | SSOT 고정 |
| phase35_3_1m_baseline.yaml | 신규 | 전체 | 조건부 생성 |
| 스크립트 5개 | 신규 | 전체 | 자동화 |
| 문서 2개 | 신규 | 전체 | 보고서 |

---

**최종 목표**: 
- ✅ 오버리팩토링 0
- ✅ 기존 모듈 최대 재사용
- ✅ 신규 파일 명확한 목적
- ✅ 변경 범위 최소 (설정 경로 + 검증만)
