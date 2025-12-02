# PHASE25-3: Bayesian Search Pipeline Design

**작성일**: 2025-12-03  
**상태**: COMPLETE  
**담당**: Claude 4.5 Thinking

---

## 1. Executive Summary

Bayesian Optimization (Optuna TPE) 기반 하이퍼파라미터 튜닝 파이프라인 구현.  
Random Search (PHASE25-2) 대비 효율적인 파라미터 탐색으로 더 적은 trial로 최적해 발견.

### 주요 목표
- **Optuna 기반 Bayesian Optimization**: TPE (Tree-structured Parzen Estimator) 알고리즘 사용
- **Sequential 튜닝**: 단일 프로세스에서 순차 실행 (향후 분산 확장 준비)
- **기존 Infra 재사용**: tuning.runs/jobs/results 스키마 그대로 사용
- **Random Search 호환**: ParamSpace, Worker, JobQueue 등 공통 모듈 재사용

---

## 2. AS-IS (Before PHASE25-3)

### 2.1 Random Search Pipeline (PHASE25-2)
- **tuning/algorithms/random_search.py**: ParamSpace, RandomSearchTuner
- **Random sampling**: seed 기반 재현 가능 랜덤 샘플링
- **Worker + Engine**: 실제 백테스트 엔진 호출, DB 메트릭 저장
- **장점**: 구현 간단, 병렬화 용이
- **단점**: 비효율적 탐색 (모든 파라미터 독립적으로 샘플링)

### 2.2 Tuning Cluster Infra (PHASE25-1)
- **DB 스키마**: tuning.runs, tuning.jobs, tuning.results
- **JobQueue**: 동시성 안전 job 관리, 상태 머신
- **Worker**: use_dummy / real backtest 모드 지원

---

## 3. TO-BE (PHASE25-3 Design)

### 3.1 Bayesian Search Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 BayesianSearchTuner                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Optuna Study (TPE)                      │   │
│  │                                                      │   │
│  │  1. Suggest params (Bayesian)                       │   │
│  │  2. Run backtest (execution/engine)                 │   │
│  │  3. Extract metrics (DB query)                      │   │
│  │  4. Report to Optuna                                │   │
│  │  5. Update posterior                                │   │
│  │  6. Repeat                                          │   │
│  └──────────────────────────────────────────────────────┘   │
│                       ↓                                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        tuning.runs / jobs / results (DB)            │   │
│  │                                                      │   │
│  │  - Run metadata (bayesian)                          │   │
│  │  - Job per trial (params_json)                      │   │
│  │  - Results (metrics)                                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Key Components

#### 3.2.1 BayesianSearchConfig
```python
@dataclass
class BayesianSearchConfig:
    run_name: str
    phase: str
    strategy_family: str
    strategy_name: str
    mode: str  # 'backtest', 'paper'
    tuning_method: str  # 'bayesian'
    target_metric: str  # 'sharpe_ratio', 'pnl', etc.
    n_trials: int
    base_config_path: str
    param_space: ParamSpace  # 재사용
    direction: str  # 'maximize' or 'minimize'
    seed: Optional[int] = None
```

#### 3.2.2 BayesianSearchTuner
```python
class BayesianSearchTuner:
    def __init__(self, job_queue: Optional[JobQueue] = None)
    
    def run_sequential(self, config: BayesianSearchConfig) -> str:
        """Sequential Bayesian Search 실행"""
        # 1. Run 생성
        # 2. Optuna Study 생성 (TPE sampler)
        # 3. study.optimize(objective, n_trials)
        # 4. Best trial 정보 업데이트
        # 5. Return run_id
    
    def _objective(self, trial, config, run_id) -> float:
        """Optuna objective 함수"""
        # 1. trial.suggest_*로 파라미터 제안
        # 2. _run_single_trial() 호출
        # 3. target_metric 반환
    
    def _run_single_trial(self, run_id, job_index, params, config):
        """단일 trial 실행"""
        # 1. tuning.jobs 레코드 생성 (RUNNING)
        # 2. Base config 로드 + params override
        # 3. run_v2(mode, config, clean_state=True)
        # 4. _extract_metrics_from_db()
        # 5. tuning.results 레코드 삽입
        # 6. tuning.jobs 상태 업데이트 (COMPLETED/FAILED)
    
    def _suggest_params_from_space(self, trial, param_space):
        """ParamSpace를 Optuna suggest API로 변환"""
        # int: trial.suggest_int(name, min, max, log)
        # float: trial.suggest_float(name, min, max, log)
        # categorical: trial.suggest_categorical(name, values)
    
    def _extract_metrics_from_db(self, run_id, job_id):
        """DB에서 백테스트 결과 메트릭 추출"""
        # Random Search / Worker와 동일한 로직
```

#### 3.2.3 CLI Runner (scripts/infra/phase25_3_run_bayesian_search.py)
```python
def main():
    # 1. CLI args 파싱
    # 2. ParamSpace 로드 (YAML or default)
    # 3. BayesianSearchConfig 생성
    # 4. BayesianSearchTuner.run_sequential()
    # 5. get_top_k_results() 조회
    # 6. print_top_k_results()
    # 7. save_summary_report() (Markdown)
```

### 3.3 ParamSpace → Optuna 변환

| ParamSpace Type | Optuna API | Notes |
|-----------------|------------|-------|
| `int` | `trial.suggest_int(name, min, max, log)` | log=True면 log-uniform sampling |
| `float` | `trial.suggest_float(name, min, max, log)` | log=True면 log-uniform sampling |
| `categorical` | `trial.suggest_categorical(name, values)` | 범주형 |

### 3.4 Optuna TPE 알고리즘

**TPE (Tree-structured Parzen Estimator)**:
- Bayesian Optimization의 일종
- 과거 trial 결과를 활용해 다음 파라미터 제안
- 좋은 결과를 낸 파라미터 주변을 집중 탐색
- Random Search 대비 **5~10배 적은 trial로 최적해 발견**

**작동 원리**:
1. 초기 몇 trial은 랜덤 샘플링 (exploration)
2. 이후 trial은 과거 결과 기반 (exploitation)
3. Good trials vs Bad trials 분리 (threshold)
4. Good trials 밀도 높은 영역 우선 탐색

---

## 4. 구현 세부사항

### 4.1 기존 코드 재사용

**재사용 항목**:
- `ParamSpace`: Random Search와 동일한 파라미터 정의 구조
- `tuning.runs/jobs/results` 스키마: 변경 없음
- `JobQueue.create_run()`: Run 생성 헬퍼
- `Worker._extract_metrics_from_db()`: 메트릭 추출 로직 (패턴 재사용)
- `execution/engine.run_v2()`: 백테스트 엔진 (동일)

**새로 구현**:
- `BayesianSearchTuner`: Optuna 연동 로직
- `BayesianSearchConfig`: Bayesian 전용 설정
- `_objective()`: Optuna objective 함수
- `_suggest_params_from_space()`: ParamSpace → Optuna 변환

### 4.2 Sequential vs Distributed

**PHASE25-3 (Sequential)**:
- 단일 프로세스에서 순차 실행
- Optuna Study가 한 프로세스에서 관리
- 장점: 구현 단순, Optuna의 Bayesian 로직 온전히 활용
- 단점: 병렬화 불가 (느림)

**Future (PHASE26+, Distributed)**:
- 멀티 Worker 분산 실행
- Optuna의 RDB Storage 사용 (PostgreSQL)
- 각 Worker가 독립적으로 trial 수행
- Study 상태는 DB로 공유

### 4.3 실패 처리

**Trial 실패 시**:
1. `_run_single_trial()` 내부에서 Exception catch
2. tuning.jobs.status = 'FAILED', error_message 저장
3. Optuna에는 penalty 값 반환 (예: sharpe=-10.0)
4. Study는 계속 진행 (다른 trial 탐색)

**전체 Study 실패 시**:
- Run status = 'FAILED' (자동, tuning.runs)
- 로그에 stacktrace 기록
- CLI는 exit code 1 반환

---

## 5. Test Strategy

### 5.1 Test Coverage

| Test | 목적 | 소요 시간 |
|------|------|-----------|
| `test_optuna_param_space_conversion` | ParamSpace → Optuna 변환 검증 | ~1s |
| `test_bayesian_config_validation` | Config validation 로직 | ~0.5s |
| `test_optuna_study_basic` | Optuna Study 기본 동작 | ~0.5s |
| `test_bayesian_search_handles_failed_trials` | 실패 케이스 처리 | ~1s |
| `test_bayesian_search_runner_cli_smoke` | CLI 모듈 import | ~0.5s |
| `test_bayesian_search_creates_run_and_results` | DB 통합 (slow) | ~1분 |

**Optuna 의존성**:
- `optuna = pytest.importorskip("optuna")`
- Optuna 미설치 시 전체 테스트 SKIP
- CI/CD: `pip install optuna` 필요

### 5.2 회귀 테스트

**기존 테스트 유지**:
- PHASE25-1: 7/7 PASS
- PHASE25-2: 3/3 PASS

**신규 테스트**:
- PHASE25-3: 5/5 PASS (기본), 1/1 SKIP (slow)

---

## 6. Known Limitations

### 6.1 메트릭 추출 간소화
- 현재: 최근 10분 trades 기준 계산
- 이슈: run_id 필터링 없음 → 동시 실행 시 충돌 가능
- 해결: PHASE25-4에서 run_id 기반 정확한 메트릭 추출

### 6.2 Sharpe Ratio 근사치
- 현재: `pnl_pct / 10` (임시 계산)
- 이슈: 실제 일별 수익률 표준편차 기반 아님
- 해결: PHASE25-4에서 정확한 Sharpe 계산

### 6.3 Sequential Only
- 현재: 단일 프로세스 순차 실행
- 이슈: 병렬화 불가 → 느림
- 해결: PHASE26에서 Optuna RDB Storage + 멀티 Worker

### 6.4 No Worker Timeout
- 현재: trial 실행 시 timeout 없음
- 이슈: 무한 대기 가능
- 해결: PHASE25-4에서 Worker heartbeat + timeout

---

## 7. Acceptance Criteria

### 7.1 구현
- [x] tuning/algorithms/bayesian_search.py
  - [x] BayesianSearchConfig
  - [x] BayesianSearchTuner
  - [x] Optuna objective 함수
  - [x] ParamSpace → Optuna 변환
- [x] scripts/infra/phase25_3_run_bayesian_search.py
  - [x] CLI 인자 파싱
  - [x] Run 실행
  - [x] 결과 출력 및 요약 리포트
- [x] tuning/algorithms/__init__.py 업데이트

### 7.2 테스트
- [x] 기존 테스트 유지
  - [x] PHASE25-1: 7/7 PASS
  - [x] PHASE25-2: 3/3 PASS
- [x] 신규 테스트
  - [x] tests/test_phase25_3_bayesian_search_pipeline.py
  - [x] 5/5 PASS (Optuna 연동, Config, Study, Failed handling, CLI)

### 7.3 문서
- [x] docs/PHASE25/PHASE25-3_BAYESIAN_SEARCH_PIPELINE_DESIGN.md
- [x] docs/PHASE25/PHASE25-3_BAYESIAN_SEARCH_PIPELINE_REPORT.md
- [x] PHASE_ROADMAP.md 업데이트

### 7.4 Git
- [x] 의미 있는 커밋 메시지
- [x] git status / git diff --stat 확인

---

## 8. Next Steps (PHASE25-4+)

### PHASE25-4: Grid Search + Local Optimization
- Grid Search 알고리즘 추가
- Best candidates 주변 local fine-tuning
- 메트릭 추출 정교화 (run_id 필터링)

### PHASE26: Distributed Tuning
- Optuna RDB Storage (PostgreSQL)
- 멀티 Worker 병렬 실행
- Worker heartbeat + timeout
- Job priority queue

### PHASE27: Ensemble Strategy Tuning
- 앙상블 가중치 튜닝
- 전략 조합 최적화
- 멀티 심볼 최적화

---

## 9. References

- **Optuna Documentation**: https://optuna.readthedocs.io/
- **TPE Paper**: "Algorithms for Hyper-Parameter Optimization" (Bergstra et al., 2011)
- **PHASE25-1 Design**: docs/PHASE25/PHASE25-1_TUNING_CLUSTER_INFRA_DESIGN.md
- **PHASE25-2 Design**: (해당 파일 없음, 코드 참조)

---

**설계 완료일**: 2025-12-03  
**구현 완료일**: 2025-12-03  
**상태**: ✅ COMPLETE
