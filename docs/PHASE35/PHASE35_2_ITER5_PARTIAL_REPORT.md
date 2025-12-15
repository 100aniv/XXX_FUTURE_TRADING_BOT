# PHASE35-2 ITER5: 실험 인프라 신뢰성 복구 (부분 완료)

**작성일**: 2025-12-15  
**상태**: ⚠️ PARTIAL COMPLETE (Config 문제로 7D Smoke 미완료)

---

## 📊 완료된 작업

### ✅ STEP 0: 루트 스캔 + 재사용 맵
**파일**: `docs/PHASE35/PHASE35_2_ITER5_REUSE_MAP.md`

**성과**:
- 기존 인프라 완전 분석
- 오염 지점 식별 완료 (리포트 글롭 탐색)
- symbol 버그 근본 원인 추정 완료
- 재사용 가능 컴포넌트 맵 작성

### ✅ STEP 1: 환경/도커 재기동
**성과**:
- Python 3.14.0 venv 정상
- Docker Compose: PostgreSQL (port 5433) + Redis (port 6379) 정상 기동
- DB/Redis 연결 테스트 통과

### ✅ STEP 2+3: 리포트 생성 강화 + Runner 격리 구조
**파일**: `execution/engine.py`, `scripts/phase35/run_iter5_isolated.py`

**주요 변경**:
1. **엔진 리포트 생성 실패 강화**:
   - 예외 발생 시 상세 스택 트레이스 로깅
   - `RuntimeError` 재발생으로 치명적 오류 처리
   
2. **Runner 완전 격리 구조**:
   ```python
   # Run ID 기반 격리
   run_id = f"phase35_2_iter5_run{run_number}_{timestamp}"
   run_dir = artifacts/phase35/iter5/{run_id}/
   
   # 리포트 경로 명시적 지정 (글롭 제거)
   report_path = run_dir / "backtest_report.json"
   config["backtest"]["output_file"] = str(report_path)
   
   # Effective Config 저장
   effective_config_path = run_dir / "effective_config.yaml"
   ```

3. **구조적 오염 방지**:
   - 모든 파일이 run_id 폴더에 격리
   - 이전 실행 결과 참조 불가능
   - 명시적 경로 전달 (글롭 탐색 제거)

### ✅ STEP 4: Fast Gate + Core Regression PASS
**결과**:
- **Fast Gate**: ✅ PASS (Import, Config 로드, 전략 초기화 모두 성공)
- **Core Regression**: ✅ PASS (8개 테스트 전부 통과)

---

## ❌ 미완료 작업

### STEP 5: 7D Smoke Run1/Run2 실행
**차단 이유**: Config 필수 키 누락 문제

**발견된 누락 키**:
1. `lookback`, `equity` ✅ 해결
2. `mode` ✅ 해결
3. `risk.per_trade` ✅ 해결
4. `capital.initial` ✅ 해결
5. `position_sizing.min_position_value` ❌ 지속 실패
6. `position_sizing.max_position_value` ❌ 지속 실패
7. `leverage.max` ✅ 해결

**문제점**:
- YAML 파일 수정이 즉시 반영되지 않음
- Runner 코드에서 직접 보장 로직 추가했으나 여전히 실패
- Config 로드 시점 문제로 추정

**해결 방안 (다음 ITER)**:
1. Base config template 생성 (모든 필수 키 포함)
2. Config validation 함수 작성
3. 필수 키 자동 채우기 로직 강화

---

## 📁 생성/수정된 파일

### 신규 생성
1. `docs/PHASE35/PHASE35_2_ITER5_REUSE_MAP.md` - 재사용 컴포넌트 맵
2. `scripts/phase35/run_iter5_isolated.py` - 격리된 러너
3. `docs/PHASE35/PHASE35_2_ITER5_PARTIAL_REPORT.md` - 본 문서
4. `artifacts/env_freeze_iter5.txt` - Python 패키지 목록

### 수정됨
5. `execution/engine.py` - 리포트 생성 실패 시 상세 로깅 + RuntimeError 추가
6. `configs/phase35/phase35_2_iter3_ssot.yaml` - 필수 키 추가 (lookback, equity, risk.per_trade, capital, position_sizing)

---

## 🎯 핵심 성과

### 1. 오염 방지 구조 확립
**이전 (ITER4)**:
```python
# 글롭으로 최신 리포트 찾기 (오염 가능)
report_files = list(Path("reports/backtest").glob("*.json"))
latest = sorted(report_files)[-1]
```

**개선 (ITER5)**:
```python
# 명시적 경로 지정 (오염 불가능)
report_path = run_dir / "backtest_report.json"
config["backtest"]["output_file"] = str(report_path)
```

### 2. 리포트 생성 실패 강화
**이전**:
```python
except Exception as e:
    logger.warning(f"리포트 생성 실패: {e}")  # 조용히 넘어감
```

**개선**:
```python
except Exception as e:
    logger.error(f"리포트 생성 실패: {e}")
    logger.error(f"스택 트레이스:\n{traceback.format_exc()}")
    raise RuntimeError(f"리포트 생성 실패: {e}") from e  # 즉시 FAIL
```

### 3. 완전 격리 구조
```
artifacts/phase35/iter5/{run_id}/
├── effective_config.yaml
├── summary.json
├── backtest_report.json
└── (향후) logs/
```

---

## 🔍 교훈 및 권장사항

### 교훈
1. **Config 검증의 중요성**: 엔진이 요구하는 필수 키를 사전에 파악하고 검증해야 함
2. **Base Config Template**: 모든 필수 키를 포함한 템플릿 필요
3. **명시적 경로 관리**: 글롭 탐색은 오염 위험이 높음

### 다음 ITER 권장사항
1. **Config Schema 정의**: JSON Schema 또는 Pydantic으로 검증
2. **Config Validator 작성**: 실행 전 모든 필수 키 검증
3. **Default Config**: 누락 키 자동 채우기 함수
4. **Integration Test**: Config 로드 → 엔진 초기화 → 1분 백테스트 자동화

---

## 📊 최종 판정

| 항목 | 상태 | 비고 |
|------|------|------|
| **Reuse Map** | ✅ PASS | 오염 지점 식별 완료 |
| **환경 재기동** | ✅ PASS | Docker/venv 정상 |
| **리포트 강화** | ✅ PASS | 예외 재발생 로직 추가 |
| **Runner 격리** | ✅ PASS | run_id 기반 완전 격리 |
| **Fast Gate** | ✅ PASS | 모든 테스트 통과 |
| **Core Regression** | ✅ PASS | 8개 테스트 통과 |
| **7D Smoke Run1** | ❌ FAIL | Config 필수 키 문제 |
| **7D Smoke Run2** | ⏸️ PENDING | Run1 실패로 미진행 |
| **재현성 검증** | ⏸️ PENDING | Run1/2 미완료 |
| **문서화** | ✅ PASS | 부분 완료 보고서 |

**종합 판정**: ⚠️ **PARTIAL PASS** (인프라 개선 완료, 실증 테스트 미완료)

---

## 🚀 다음 액션

### 즉시 조치 (ITER5.5 또는 ITER6)
1. `configs/phase35/base_complete.yaml` 생성 (모든 필수 키 포함)
2. Config validation 함수 작성
3. Run1 재실행
4. Run2 실행 + 재현성 검증

### 우선순위
- **P0**: Config 문제 해결 (차단 중)
- **P1**: 7D Smoke 완료
- **P2**: 재현성 검증
- **P3**: ROADMAP 업데이트

---

**작성 완료**: 2025-12-15 10:42  
**소요 시간**: 약 1시간 10분  
**다음 작업**: Config 완전성 보장 후 재시도
