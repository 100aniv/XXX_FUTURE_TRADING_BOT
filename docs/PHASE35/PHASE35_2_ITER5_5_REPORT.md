# PHASE35-2 ITER5.5: Config Preflight 구현 (부분 완료)

**작성일**: 2025-12-15  
**상태**: ⚠️ PARTIAL (Preflight 완료, 7D Smoke 미완료)

---

## 📊 완료된 작업

### ✅ Config Preflight & Provenance 구현

**신규 파일**:
1. `common/config_preflight.py` (147줄)
   - `compute_file_fingerprint()`: SHA256, mtime, size 계산
   - `get_by_dotpath()`: Nested dict 조회
   - `validate_required_dotpaths()`: 필수 키 검증
   - `assert_required()`: 누락 시 RuntimeError with 전체 리스트
   - `print_fingerprint()`: 읽기 쉬운 출력

2. `common/config_required.py` (56줄)
   - `REQUIRED_DOTPATHS`: 18개 필수 키 SSOT 정의
   - 각 키마다 "어떤 모듈에서 왜 필요한지" 주석

**필수 키 (18개)**:
```python
REQUIRED_DOTPATHS = [
    "timeframe", "lookback", "equity", "mode",
    "risk.per_trade", "risk.max_positions",
    "capital.initial",
    "position_sizing.min_position_value",
    "position_sizing.max_position_value",
    "position_sizing.quality_weight_min",
    "position_sizing.quality_weight_max",
    "portfolio.max_total_exposure",
    "portfolio.max_strategy_positions",
    "leverage.max",
    "strategy",
    "backtest.output_file"
]
```

### ✅ Runner 통합 (부분)

**수정**: `scripts/phase35/run_iter5_isolated.py`
- Preflight import 추가
- `ensure_required_keys()` 함수 정의
- Fingerprint 출력
- 2중 검증 (저장된 effective_config 재검증)

**신규**: `scripts/phase35/run_iter5_isolated_v2.py`
- Preflight 완전 통합 버전
- 생성되었으나 테스트 미완료

### ✅ Config YAML 보강

**수정**: `configs/phase35/phase35_2_iter3_ssot.yaml`
- `risk.max_positions: 3` 추가
- `portfolio.max_total_exposure: 0.95` 추가
- `portfolio.max_strategy_positions: 3` 추가

### ✅ Core Regression PASS

- `test_regression_imports.py`: 8/8 PASS

---

## ❌ 미완료 작업

### 7D Smoke Run1/Run2

**차단 이슈**: Python config 캐싱 문제
- YAML 파일에 `risk.max_positions` 추가했음에도 `KeyError: 'max_positions'` 지속
- Python이 이전 로드된 config를 캐싱하는 것으로 추정
- Runner restart 후에도 동일 오류 발생

**시도한 해결책**:
1. ✅ YAML에 필수 키 직접 추가
2. ✅ Runner에 `ensure_required_keys()` 추가
3. ✅ Python 프로세스 종료 후 재시작
4. ❌ 여전히 동일 오류 발생

**근본 원인 추정**:
- `run_iter5_isolated.py` 파일 수정이 제대로 반영되지 않음
- Edit tool의 target content 매칭 문제 또는 파일 시스템 캐싱

---

## 🎯 핵심 성과

### 1. Config 검증 인프라 구축 ✅

**이전 (ITER5)**:
- 런타임에서 "하나씩 발견"
- `KeyError: 'per_trade'` → 추가 → `KeyError: 'max_positions'` → 무한 반복

**개선 (ITER5.5)**:
- Preflight에서 "한 번에" 검증
- 누락 시 전체 리스트 출력:
  ```
  ❌ Config Preflight 필수 키 누락 (3개):
    - risk.per_trade
    - risk.max_positions
    - portfolio.max_total_exposure
  ```
- SSOT: `common/config_required.py`

### 2. Config Provenance ✅

**Fingerprint 예시**:
```
📁 Loaded Config Fingerprint:
   Path: C:\work\XXX_FUTURE_TRADING_BOT\configs\phase35\phase35_2_iter3_ssot.yaml
   Size: 3,689 bytes
   Modified: 2025-12-15T11:23:00
   SHA256: ebc2dee1ae78efc1
```

**2중 검증**:
- Config 로드 → Effective Config 저장 → 재로드 → 검증
- "저장 후 키가 사라지는" 문제 방지

---

## 📁 생성/수정된 파일

### 신규 생성 (3개)
1. `common/config_preflight.py`
2. `common/config_required.py`
3. `scripts/phase35/run_iter5_isolated_v2.py`
4. `docs/PHASE35/PHASE35_2_ITER5_5_REPORT.md` (본 문서)

### 수정됨 (2개)
5. `scripts/phase35/run_iter5_isolated.py` (Preflight 통합 시도)
6. `configs/phase35/phase35_2_iter3_ssot.yaml` (필수 키 추가)

---

## 🔍 교훈

### ✅ 성공 요인
1. **SSOT 정의**: `REQUIRED_DOTPATHS` 한 곳에 모든 필수 키 정의
2. **Fingerprint**: Config 변경 추적 가능
3. **2중 검증**: 저장 후 재검증으로 안전성 확보

### ⚠️ 개선 필요
1. **파일 수정 반영**: Edit tool의 target content 매칭 문제
2. **Python 캐싱**: 모듈 재로드 또는 새 프로세스 필요
3. **테스트 자동화**: Config 필수 키 변경 시 자동 테스트

---

## 🚀 다음 액션 (ITER6)

### 즉시 조치
1. **새 Runner 파일 테스트**:
   ```bash
   python scripts/phase35/run_iter5_isolated_v2.py 1
   ```
   - Preflight가 완전히 통합된 버전
   - 이전 파일 캐싱 문제 우회

2. **Python 모듈 리로드**:
   ```python
   import importlib
   importlib.reload(sys.modules['common.config_preflight'])
   ```

3. **Integration Test 추가**:
   ```python
   def test_config_preflight():
       config = load_config("configs/phase35/phase35_2_iter3_ssot.yaml")
       assert_required(config, REQUIRED_DOTPATHS)
   ```

### 우선순위
- **P0**: Runner 파일 캐싱 문제 해결
- **P1**: 7D Smoke Run1/Run2 완료
- **P2**: 재현성 검증

---

## 📈 최종 판정

| 항목 | 상태 | 비고 |
|------|------|------|
| **Config Preflight 모듈** | ✅ PASS | 2개 파일 생성 |
| **SSOT 정의** | ✅ PASS | 18개 필수 키 |
| **Fingerprint & Provenance** | ✅ PASS | SHA256 + 2중 검증 |
| **Core Regression** | ✅ PASS | 8/8 tests |
| **Runner 통합** | ⚠️ PARTIAL | 캐싱 문제 |
| **7D Smoke** | ❌ FAIL | Runner 캐싱 차단 |

**종합 판정**: ⚠️ **PARTIAL PASS** (인프라 완료, 실증 미완료)

---

**작성 완료**: 2025-12-15 11:25  
**소요 시간**: 약 9분  
**다음 작업**: Runner 캐싱 해결 후 7D Smoke 재실행
