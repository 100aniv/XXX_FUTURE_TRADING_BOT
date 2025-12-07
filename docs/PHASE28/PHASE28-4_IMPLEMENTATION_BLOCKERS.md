# PHASE28-4: Bayesian Search Round 1 - Implementation Blockers

**Date**: 2025-12-07
**Status**: ⚠️ BLOCKED - Parameter Merge Issue

---

## 📋 작업 개요

PHASE28-3 Random Search Round 1 결과를 기반으로 Bayesian Optimization Round 1을 수행하기 위한 인프라 구축 및 실행.

## ✅ 완료된 작업 (Infrastructure Ready)

1. **설계 문서**
   - `docs/PHASE28/PHASE28-4_BAYESIAN_SEARCH_ROUND1_DESIGN.md` 작성 완료
   - Random vs Bayesian 역할 정의, Acceptance Criteria 명시

2. **Top-N 후보 추출 유틸**
   - `tuning/utils/result_selection.py` 구현 (~180 LOC)
   - PHASE28-3 results.json에서 상위 N개 후보 자동 선정
   - 스코어링, 필터링, 디듀플리케이션 로직 포함
   - 실제 PHASE28-3 데이터로 검증 완료 (Top-5 추출 성공)

3. **Config 작성**
   - `configs/tuning/phase28_4_btc5m_bayesian_search.yml` (Full 실행용)
   - `configs/tuning/phase28_4_btc5m_bayesian_search_smoke.yml` (Smoke Test용)
   - Trial 수: 각 Period당 25 trials (총 50 trials)
   - Top-N seed: PHASE28-3 상위 5개 후보

4. **실행 스크립트**
   - `scripts/tuning/phase28_4_run_bayesian_search_round1.py` (~400 LOC)
   - 환경 검증, Top-N 추출, Period별 Bayesian Search 실행
   - 임시 config 파일 생성하여 Period별 날짜 범위 적용

5. **Unit Tests**
   - `tests/tuning/test_phase28_4_bayesian_search_round1.py` (~290 LOC)
   - 결과: **8/8 PASS**
     - Environment check
     - Config 로딩
     - ParamSpace 로딩
     - Top-N 후보 추출 (샘플 데이터)
     - 스코어 계산
     - 파라미터 유사도 판단
     - Bayesian objective 패널티 로직

6. **회귀 테스트**
   - PHASE28-3 automation tests: **8/8 PASS**
   - Engine SSOT tests: **8/8 PASS**

7. **BayesianSearchTuner 수정**
   - `tuning/algorithms/bayesian_search.py` Line 238-254 수정
   - 파라미터 merge 방식을 `strategy.params` → `strategies.{selector}`로 변경
   - `merge_strategy_config()`가 top-level로 복사하는 구조에 맞춤

---

## ❌ Blocking Issue

### 문제: 파라미터가 전략에 전달되지 않음

**증상**:
- Smoke Test 실행 시 백테스트는 진행되나, 전략이 파라미터를 받지 못함
- 로그: "btc5m_baseline_v1 params: {}"
- 로그: "rsi_oversold=MISSING, rsi_overbought=MISSING" (다른 전략의 디버그 로그로 추정)

**근본 원인**:
1. **BayesianSearchTuner vs TuningWorker 차이**
   - **TuningWorker** (Random Search에서 사용):
     - JobQueue에 job enqueue
     - Worker가 job acquire하여 실행
     - Worker.process_job()에서 `strategies.{selector}`에 파라미터 삽입
     - 엔진에서 `merge_strategy_config()` 호출 → top-level로 복사
   
   - **BayesianSearchTuner** (Bayesian Search에서 사용):
     - Optuna sequential 실행 (Worker 패턴 불가)
     - _run_single_trial()에서 직접 run_v2() 호출
     - 파라미터 merge 로직이 Worker와 다름

2. **merge_strategy_config() 의존성**
   - btc5m_baseline_v1 전략은 `config.get('rsi_long_threshold', 45)`처럼 config 루트에서 파라미터 읽음
   - `merge_strategy_config()`가 `strategies.{selector}` → config 루트로 복사 (Line 544-547)
   - BayesianSearchTuner가 직접 run_v2() 호출 시, merge_strategy_config()가 호출되지 않거나 타이밍 이슈

3. **PHASE25 Bayesian Search 미검증**
   - BayesianSearchTuner는 PHASE25-3에서 구현됨
   - 하지만 실제 production 전략 (btc5m_baseline_v1)과 연동 테스트가 없었을 가능성
   - Random Search (PHASE28-3)는 Worker 패턴으로 정상 작동 확인

**시도한 해결책**:
1. ✅ BayesianSearchTuner._run_single_trial() 수정
   - `strategy.params` → `strategies.{selector}`로 파라미터 적용 방식 변경
   - 코드 수정 완료 (Line 238-254)

2. ❌ Smoke Test 재실행
   - 여전히 파라미터가 전달되지 않음
   - 추가 디버깅 필요

---

## 🔍 추가 조사 필요 사항

1. **run_v2() 호출 시 merge_strategy_config() 타이밍**
   - BayesianSearchTuner가 직접 run_v2() 호출할 때, merge_strategy_config()가 언제 호출되는지 확인
   - engine.py Line 540-555 참조

2. **임시 config 파일 구조 검증**
   - phase28_4_run_bayesian_search_round1.py에서 생성하는 임시 config 파일 내용 확인
   - strategies.{selector} 섹션이 제대로 merge되는지 확인

3. **base config vs temporary config**
   - Period별 임시 config 생성 시, strategies 섹션이 올바르게 복사되는지 확인
   - YAML dump/load 과정에서 손실 가능성

4. **대안: Worker 패턴 사용**
   - Bayesian Search도 Worker 패턴으로 변경 가능 여부 검토
   - Optuna Study를 DB에 저장하고, Worker가 Trial 단위로 실행

---

## 🛠️ 권장 해결 방안

### Option 1: BayesianSearchTuner 완전 수정 (시간 소요 예상: 4~6시간)
1. _run_single_trial() 로직 전면 재작성
2. TuningWorker.process_job()과 동일한 config merge 로직 적용
3. 단위 테스트 추가 (config merge 검증)
4. Smoke Test 재실행 및 검증

### Option 2: Worker 패턴으로 재설계 (시간 소요 예상: 6~8시간)
1. Optuna Study를 DB 또는 파일 시스템에 저장
2. BayesianSearchTuner가 JobQueue에 job enqueue (Optuna suggest 결과)
3. TuningWorker가 job acquire하여 실행 (기존 Random Search와 동일)
4. 결과를 Optuna Study에 반영
5. 전체 파이프라인 재검증

### Option 3: Random Search 확장 (시간 소요 예상: 2~3시간)
1. PHASE28-3 Random Search를 더 많은 trial로 실행 (50~100 trials)
2. Top-N 후보를 수동으로 분석
3. Bayesian Search는 PHASE28-5 이후로 연기
4. Local Grid Search (PHASE28-5)로 직접 진행

---

## 📊 현재 상태

**AC1-AC3**: ✅ COMPLETE
- 설계 문서, 코드 구현, Unit tests

**AC4: Smoke Test**: ❌ BLOCKED
- Parameter merge issue

**AC5-AC7**: ⏸️ PENDING
- Smoke Test 성공 후 진행 가능

**전체 판정**: ⚠️ INFRASTRUCTURE READY - EXECUTION BLOCKED

---

## 🎯 권장 조치

### 단기 (이번 세션)
1. PHASE28-4 상태를 "BLOCKED" 로 명확히 표시
2. 발견한 문제와 시도한 해결책 문서화 (이 파일)
3. ROADMAP에 현재 상태 반영
4. Git 커밋: "PHASE28-4: Infrastructure Ready - Execution Blocked (Parameter Merge Issue)"

### 중기 (다음 세션)
1. Option 1 또는 Option 2 선택하여 근본 해결
2. Bayesian Search 파이프라인 완전 검증
3. Full execution 및 결과 분석

### 대안 (시간 제약 시)
1. Option 3 선택: Random Search 확장
2. PHASE28-5 Local Grid Search로 직접 진행
3. Bayesian Search는 향후 infrastructure 안정화 후 재시도

---

---

## 🔧 해결 시도 (2025-12-07 Session 2)

### 완료된 작업
1. **공통 Config Builder 추출** (~150 LOC)
   - `tuning/utils/config_builder.py` 생성
   - TuningWorker와 BayesianSearchTuner가 100% 동일한 config merge 로직 사용
   - `build_tuning_config()` 함수로 통합

2. **TuningWorker 수정**
   - 기존 config merge 로직을 `build_tuning_config()` 호출로 대체
   - Line 239-253: 60 LOC → 15 LOC로 간소화

3. **BayesianSearchTuner 수정**
   - 동일한 `build_tuning_config()` 사용
   - Line 234-245: 파라미터 merge 로직 통합

4. **테스트 검증**
   - Config builder 단독 테스트: ✅ 파라미터 12/12 삽입 성공
   - PHASE28-4 Unit Tests: ✅ 8/8 PASS
   - PHASE28-3 회귀 테스트: ✅ 1/1 PASS

5. **Minimal Bayesian Test 실행**
   - 1 trial 실행: ❌ 여전히 파라미터 전달 실패
   - 로그: `btc5m_baseline_v1 params: {}` (빈 dict)
   - 로그: `rsi_oversold=MISSING` (scalping 전략 파라미터 - 잘못된 전략 참조?)

### 발견된 추가 이슈

**이슈 1: Ensemble 경로 의심**
- Config: `ensemble.enabled: false`, `strategy.use_ensemble: false`
- 하지만 로그에서 ensemble 경로의 DEBUG 메시지 출력됨
- Line 1533/1544: PHASE22-4 DEBUG (ensemble 경로)
- 가능성: 엔진이 ensemble 경로를 타고 있거나, SignalGenerator 초기화 과정에서 config가 잘못 전달됨

**이슈 2: DB 에러**
- `trading.portfolio` 테이블 부재
- PHASE28-2에서 portfolio 테이블 의존성 제거 작업이 완료되었어야 하나, BayesianSearchTuner._extract_metrics_from_db()는 아직 portfolio 테이블을 참조
- Line 381: `SELECT equity FROM trading.portfolio`

### 추가 분석 필요 사항

1. **엔진 초기화 흐름 완전 추적**
   - use_ensemble=false일 때 SignalGenerator 초기화 과정
   - merge_strategy_config() 결과가 실제로 어디로 전달되는지
   - 단일 전략 vs Ensemble 경로 분기 조건 재검증

2. **BayesianSearchTuner DB 의존성 수정**
   - `_extract_metrics_from_db()`에서 portfolio 테이블 제거
   - TuningWorker와 동일하게 trades 테이블만 사용하도록 수정

3. **Config 전달 경로 디버깅**
   - engine.py Line 552-560: merge_strategy_config() 호출 후 signal_gen_config
   - 이 config가 실제로 BaseStrategy에 전달되는지 확인
   - Ensemble 경로가 의도치 않게 활성화되는 조건 확인

### 현재 판정

- **Infrastructure**: ✅ COMPLETE
  - 공통 config builder 완성
  - TuningWorker/BayesianSearchTuner 통합
  - 단위 테스트 PASS
  
- **Execution**: ❌ STILL BLOCKED
  - 파라미터 전달 문제 미해결
  - 엔진 내부 config 흐름 재조사 필요

### 권장 다음 단계

1. **Option 1A: 엔진 경로 완전 추적** (2~3시간 예상)
   - SignalGenerator 초기화 과정 완전 디버깅
   - use_ensemble=false 조건에서 config 전달 흐름 검증
   - 필요 시 엔진 내부 config 전달 로직 수정

2. **Option 1B: BayesianSearchTuner DB 수정 먼저** (30분 예상)
   - portfolio 테이블 의존성 제거
   - TuningWorker와 동일한 메트릭 추출 로직 사용
   - 최소한 백테스트 완료 → 메트릭 추출 경로 확보

3. **Option 2: Worker 패턴 재설계** (6~8시간, 근본 해결)
   - Bayesian Search도 JobQueue + TuningWorker 사용
   - Random Search와 100% 동일한 실행 흐름 보장
   - Optuna Study를 DB 또는 파일로 관리

---

**최종 업데이트**: 2025-12-07 15:40
**작성자**: AI Assistant (Windsurf)
