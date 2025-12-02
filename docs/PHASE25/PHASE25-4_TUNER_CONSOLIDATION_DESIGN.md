# PHASE25-4: Tuner Consolidation & Local Grid Search 설계

**작성일**: 2025-12-03  
**상태**: DESIGN  
**담당**: Claude 4.5 Thinking

---

## 1. Executive Summary

PHASE25 튜닝 인프라 완성 단계:
- **Tuner Consolidation**: 레거시 튜너 정리, PHASE25 아키텍처를 canonical 구조로 확정
- **Local Grid Search**: Best K 후보 주변 국소 그리드 탐색 튜너 추가
- **Metrics Refinement**: run_id/job_id 기반 정확한 메트릭 계산 (Sharpe, MaxDD 등)
- **Worker Timeout**: Stale job 자동 실패 처리 (hanging job 방지)

### 주요 목표
- Random → Bayesian → Local Grid 3단계 튜닝 파이프라인 완성
- 메트릭 계산 정교화 (현재 근사치 → 정확 계산)
- 인프라 안정성 보강 (timeout 처리)

---

## 2. AS-IS: 현재 튜닝 구조

### 2.1 레거시 (PHASE5~6, PR13)

**파일**:
- `tuning/ensemble_tuner.py`: EnsembleTuner (Optuna 기반)
- `tuning/tuning_core.py`: TunerCore
- `tuning/config_overlay.py`: ConfigOverlay
- `scripts/run_tuner.py`, `run_tuner_loop.py`

**특징**:
- Optuna Storage 직접 사용 (별도 optuna.db)
- Ensemble 전용 (weight, threshold 튜닝)
- 단일 실행 스크립트 기반

**문제점**:
- Job Queue 없음 (분산 처리 불가)
- DB 스키마 분리 (tuning.* 테이블 미사용)
- 현재 PHASE25 아키텍처와 불일치

### 2.2 현재 (PHASE25-1/2/3)

**아키텍처**:
```
┌──────────────────────────────────────────────────────────┐
│              Tuning Algorithms Layer                      │
│                                                          │
│  RandomSearchTuner    BayesianSearchTuner               │
│  (PHASE25-2)          (PHASE25-3)                       │
│                                                          │
│  공통: ParamSpace (int/float/categorical)               │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ↓
┌──────────────────────────────────────────────────────────┐
│              Tuning Cluster Layer                        │
│                                                          │
│  JobQueue              TuningWorker                      │
│  (DB: tuning.runs/     (job 처리, 엔진 호출,             │
│   jobs/results)         메트릭 추출)                     │
└──────────────────────────────────────────────────────────┘
                         │
                         ↓
┌──────────────────────────────────────────────────────────┐
│              Execution Engine                            │
│                                                          │
│  run_v2(mode, config, clean_state)                      │
│  (backtest/paper/live 공통 진입점)                      │
└──────────────────────────────────────────────────────────┘
```

**특징**:
- Job Queue 기반 (분산 처리 가능, 단 현재는 Sequential)
- DB 스키마 통합 (tuning.runs/jobs/results)
- 엔진 재사용 (run_v2 호출)
- ParamSpace 공통 인터페이스

**Known Issues**:
1. **메트릭 추출 간소화**:
   - 최근 10분 trades 기준 (`WHERE exit_time >= now() - interval '10 minutes'`)
   - run_id/job_id 필터링 없음 → 동시 실행 시 충돌
2. **Sharpe Ratio 근사치**:
   - `pnl_pct / 10` 임시 계산
   - 실제 일별 수익률 표준편차 기반 아님
3. **Worker Timeout 없음**:
   - Hanging job 감지/처리 로직 없음
4. **MaxDD 미구현**:
   - `max_drawdown = 0.0` 고정

---

## 3. TO-BE: PHASE25-4 설계

### 3.1 Tuner Consolidation (통합)

#### 3.1.1 레거시 정리

**방침**:
- 레거시 튜너는 **DEPRECATED** 표시
- 기존 기능이 필요하면 PHASE25 구조로 포팅
- 삭제하지 않고 `tuning/ensemble_tuner.py` 상단에 deprecation 주석 추가

**Deprecation 주석** (예시):
```python
"""
⚠️ DEPRECATED (PHASE25-4)
========================
이 모듈은 PHASE5~6 시절의 구버전 튜너입니다.
현재 PHASE25 아키텍처에서는 사용하지 않습니다.

권장 대안:
- Random Search: tuning/algorithms/random_search.py
- Bayesian Search: tuning/algorithms/bayesian_search.py
- Local Grid Search: tuning/algorithms/local_grid_search.py

이 파일은 호환성 유지를 위해 남겨두었으나,
향후 PHASE26+에서 제거될 수 있습니다.
"""
```

#### 3.1.2 공통 인터페이스 (선택)

**목적**: Random/Bayesian/LocalGrid 튜너의 공통 인터페이스 정의

**파일**: `tuning/algorithms/base.py` (새로 생성)

**내용**:
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class TuningResult:
    """튜닝 결과"""
    run_id: str
    best_params: Dict[str, Any]
    best_metric: float
    total_jobs: int
    completed_jobs: int
    failed_jobs: int

class BaseTuner(ABC):
    """튜너 공통 인터페이스"""
    
    @abstractmethod
    def create_run_and_jobs(self, config) -> str:
        """Run 생성 및 Jobs enqueue"""
        pass
    
    @abstractmethod
    def get_top_k_results(self, run_id: str, k: int, ascending: bool = False) -> List[Dict]:
        """상위 K개 결과 조회"""
        pass
```

**장점**:
- 타입 힌트 일관성
- 테스트 작성 용이
- 향후 확장성

**단점**:
- 현재 Random/Bayesian이 이미 구현되어 있어, 리팩토링 필요
- LOC 증가

**결정**: **선택 사항** (시간 여유 있으면 추가, 없으면 문서로만 정의)

### 3.2 Local Grid Search Tuner

#### 3.2.1 목적

Random/Bayesian으로 얻은 **Best K 후보 주변**에서 국소 그리드 탐색:
- Exploration (Random/Bayesian): 넓은 공간 탐색
- Exploitation (Local Grid): Best 후보 주변 정밀 탐색

#### 3.2.2 알고리즘

**입력**:
- `base_run_id`: Random/Bayesian run ID
- `top_k`: 상위 K개 후보 선택
- `grid_steps`: 각 파라미터별 그리드 스텝 수 (예: 3 → ±1 step)
- `step_factor`: 스텝 크기 비율 (예: 0.1 → 원래 범위의 10%)

**프로세스**:
1. `tuning.results`에서 `base_run_id`의 Top K 후보 조회
2. 각 후보의 파라미터를 중심으로 그리드 생성:
   - int: `center ± step * (grid_steps // 2)`
   - float: `center ± delta * (grid_steps // 2)`, delta = `(max - min) * step_factor`
   - categorical: 변경 없음 (중심값만 사용)
3. 생성된 그리드 조합을 `tuning.jobs`에 enqueue

**예시**:
```python
# Base run에서 Top 2 후보:
# 후보 1: {'rsi_oversold': 30, 'stop_loss_pct': 1.0}
# 후보 2: {'rsi_oversold': 32, 'stop_loss_pct': 1.2}

# Grid 설정:
# grid_steps = 3 (중심 + ±1)
# step_factor = 0.1

# 후보 1 주변 그리드:
# rsi_oversold: [29, 30, 31] (int, step=1)
# stop_loss_pct: [0.95, 1.0, 1.05] (float, delta=0.05)
# → 3 x 3 = 9개 조합

# 후보 2 주변 그리드:
# rsi_oversold: [31, 32, 33]
# stop_loss_pct: [1.15, 1.2, 1.25]
# → 3 x 3 = 9개 조합

# 총 18개 job 생성
```

#### 3.2.3 구현

**파일**: `tuning/algorithms/local_grid_search.py`

**클래스**:
```python
@dataclass
class LocalGridSearchConfig:
    run_name: str
    phase: str
    strategy_family: str
    strategy_name: str
    mode: str
    tuning_method: str = 'local_grid'  # DB constraint
    target_metric: str = 'sharpe_ratio'
    base_run_id: str = ''  # 기준 Run ID
    top_k: int = 3
    grid_steps: int = 3  # 홀수 권장
    step_factor: float = 0.1
    base_config_path: str = ''

class LocalGridSearchTuner:
    def __init__(self, job_queue: Optional[JobQueue] = None): ...
    
    def create_run_and_jobs(self, config: LocalGridSearchConfig) -> str:
        """
        1. Base run의 Top K 후보 조회
        2. 각 후보 주변 그리드 생성
        3. tuning.runs 레코드 생성
        4. tuning.jobs enqueue
        5. Return run_id
        """
        pass
    
    def _generate_grid_around_candidate(
        self,
        params: Dict[str, Any],
        param_space: ParamSpace,
        grid_steps: int,
        step_factor: float
    ) -> List[Dict[str, Any]]:
        """단일 후보 주변 그리드 생성"""
        pass
    
    def get_top_k_results(self, run_id: str, k: int, ascending: bool = False) -> List[Dict]:
        """결과 조회 (Random/Bayesian과 동일)"""
        pass
```

### 3.3 Metrics Refinement

#### 3.3.1 문제점

**현재 (`worker.py::_extract_metrics_from_db()`)**:
```python
sql_trades = """
SELECT ...
FROM trading.trades
WHERE exit_time >= now() - interval '10 minutes'
"""
```
- ❌ run_id/job_id 필터링 없음
- ❌ 동시 실행 시 다른 run의 trades가 섞임
- ❌ Sharpe = `pnl_pct / 10` 근사치
- ❌ MaxDD = 0.0 고정

#### 3.3.2 해결 방안

**1) run_id/job_id 기반 필터링**

**방법 A**: trades 테이블에 run_id 컬럼 추가 (DB 스키마 변경)
- 장점: 정확한 필터링
- 단점: 마이그레이션 필요, 엔진 수정 (run_id 전파)

**방법 B**: 시간 기반 isolation (현재 방식 개선)
- 장점: 스키마 변경 불필요
- 단점: 완벽하지 않음 (동시 실행 시 여전히 충돌 가능)
- 개선: `WHERE exit_time BETWEEN start_time AND end_time` (Worker가 start/end 기록)

**방법 C**: 별도 테이블 사용 (tuning.job_trades)
- 장점: tuning 전용 테이블
- 단점: 복잡도 증가

**결정**: **방법 B** (시간 기반 개선) + 향후 PHASE26에서 방법 A 검토

**구현**:
```python
def _extract_metrics_from_db(self, run_id: str, job_id: str, start_time: float, end_time: float):
    sql_trades = """
    SELECT ...
    FROM trading.trades
    WHERE exit_time >= to_timestamp(%s)
      AND exit_time <= to_timestamp(%s)
    """
    # start_time, end_time은 job 시작/종료 시각 (epoch)
```

**2) Sharpe Ratio 정확 계산**

**현재**:
```python
sharpe_ratio = pnl_pct / 10.0  # 임시 근사
```

**개선** (일별 수익률 기반):
```python
def _calculate_sharpe_ratio(trades: List[Dict]) -> float:
    """
    Sharpe Ratio 계산 (일별 수익률 기반)
    
    Args:
        trades: 거래 목록 [{'pnl_usdt': ..., 'exit_time': ...}, ...]
    
    Returns:
        float: Sharpe Ratio (연율화)
    """
    if len(trades) < 2:
        return 0.0
    
    # 1. 일별 수익률 계산 (단순화: trade별 pnl을 일별로 그룹화)
    # 실제로는 equity curve 필요하나, 여기서는 간단히 처리
    
    daily_returns = []
    # 예시: trade별 pnl_pct를 일별로 합산
    # (정확한 계산은 portfolio equity 기반이어야 하나, 간소화)
    
    for trade in trades:
        pnl_pct = trade['pnl_pct'] if 'pnl_pct' in trade else 0.0
        daily_returns.append(pnl_pct / 100.0)
    
    # 2. 평균 및 표준편차
    mean_return = np.mean(daily_returns)
    std_return = np.std(daily_returns)
    
    if std_return == 0:
        return 0.0
    
    # 3. Sharpe Ratio (연율화: sqrt(365))
    sharpe = (mean_return / std_return) * np.sqrt(365)
    
    return sharpe
```

**주의**: 완벽한 Sharpe 계산은 equity curve 필요. 여기서는 **근사 개선**만 수행.

**3) Max Drawdown 계산**

**추가**:
```python
def _calculate_max_drawdown(trades: List[Dict]) -> Tuple[float, float]:
    """
    Max Drawdown 계산
    
    Args:
        trades: 거래 목록 (시간 순 정렬 필요)
    
    Returns:
        (max_drawdown_pct, max_drawdown_duration_hours)
    """
    if not trades:
        return 0.0, 0.0
    
    # 1. Cumulative PnL 계산
    cumulative_pnl = []
    running_pnl = 0.0
    for trade in trades:
        running_pnl += trade['pnl_usdt']
        cumulative_pnl.append(running_pnl)
    
    # 2. Running Peak 및 Drawdown 계산
    peak = cumulative_pnl[0]
    max_dd = 0.0
    dd_start_idx = 0
    dd_end_idx = 0
    
    for i, pnl in enumerate(cumulative_pnl):
        if pnl > peak:
            peak = pnl
            dd_start_idx = i
        
        dd = (peak - pnl) / abs(peak) if peak != 0 else 0.0
        
        if dd > max_dd:
            max_dd = dd
            dd_end_idx = i
    
    # 3. Duration 계산 (시간)
    if dd_end_idx > dd_start_idx:
        start_time = trades[dd_start_idx]['exit_time']
        end_time = trades[dd_end_idx]['exit_time']
        duration_hours = (end_time - start_time).total_seconds() / 3600
    else:
        duration_hours = 0.0
    
    return max_dd * 100, duration_hours
```

### 3.4 Worker Timeout

#### 3.4.1 문제점

현재 Worker는 job 처리 중 무한 대기 가능:
- 백테스트 엔진이 hang되면 job이 RUNNING 상태로 계속 남음
- 다른 worker가 해당 job을 다시 처리할 수 없음

#### 3.4.2 해결 방안

**Stale Job 감지 및 실패 처리**:

**파일**: `tuning/cluster/job_queue.py`

**함수 추가**:
```python
def mark_stale_jobs_as_failed(self, max_runtime_sec: int = 3600) -> int:
    """
    Stale RUNNING job을 FAILED로 전환
    
    Args:
        max_runtime_sec: 최대 허용 실행 시간 (초, 기본 1시간)
    
    Returns:
        int: 실패 처리된 job 수
    """
    sql = """
    UPDATE tuning.jobs
    SET status = 'FAILED',
        error_message = 'Job timeout: exceeded max runtime',
        updated_at = now()
    WHERE status = 'RUNNING'
      AND (EXTRACT(EPOCH FROM (now() - started_at)) > %s)
    RETURNING job_id
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (max_runtime_sec,))
            failed_jobs = cur.fetchall()
            conn.commit()
    
    count = len(failed_jobs)
    if count > 0:
        logger.warning(f"⚠️  Stale job {count}개를 FAILED로 전환")
    
    return count
```

**사용법**:
- 별도 스크립트에서 주기적으로 호출 (예: cron)
- 또는 Worker loop에서 주기적으로 호출 (최소 부하)

**테스트**:
- 인위적으로 오래된 RUNNING job 생성
- `mark_stale_jobs_as_failed()` 호출
- FAILED 전환 확인

---

## 4. 구현 우선순위

### 4.1 필수 (PHASE25-4 Acceptance Criteria)

1. ✅ **Local Grid Search Tuner** (tuning/algorithms/local_grid_search.py)
2. ✅ **Metrics Refinement** (worker.py 개선)
3. ✅ **Worker Timeout** (job_queue.py 추가)
4. ✅ **테스트** (3개 테스트 파일, 모두 PASS)
5. ✅ **문서** (DESIGN + REPORT)

### 4.2 선택 (시간 여유 시)

1. ⏸️ **공통 인터페이스** (tuning/algorithms/base.py)
2. ⏸️ **Local Grid CLI** (scripts/infra/phase25_4_run_local_grid_search.py)
3. ⏸️ **레거시 정리** (deprecated/ 폴더 이동)

---

## 5. 테스트 전략

### 5.1 Test Coverage

| Test File | 목적 | 예상 시간 |
|-----------|------|-----------|
| `test_phase25_4_local_grid_search.py` | Local Grid 생성 로직, Run/Job 레코드 | ~2s |
| `test_phase25_4_metrics_refinement.py` | 메트릭 계산 정확도, run 간 분리 | ~3s |
| `test_phase25_4_worker_timeout.py` | Stale job 감지 및 실패 처리 | ~1s |

### 5.2 회귀 테스트

**기존 테스트 유지** (PHASE25-1/2/3):
- `test_phase25_1_tuning_cluster_infra.py`: 7/7 PASS
- `test_phase25_2_random_search_pipeline.py`: 3/3 PASS
- `test_phase25_3_bayesian_search_pipeline.py`: 5/5 PASS

**신규 테스트** (PHASE25-4):
- `test_phase25_4_local_grid_search.py`: 4/4 PASS (예상)
- `test_phase25_4_metrics_refinement.py`: 3/3 PASS (예상)
- `test_phase25_4_worker_timeout.py`: 2/2 PASS (예상)

**Total**: 24/24 PASS (예상)

---

## 6. Acceptance Criteria

PHASE25-4 완료 조건:

### 6.1 Tuner Consolidation
- [x] 레거시 튜너 deprecated 표시 (주석)
- [x] PHASE25 아키텍처 문서화

### 6.2 Local Grid Search
- [ ] `LocalGridSearchTuner` 구현 및 테스트 PASS
- [ ] Grid candidate 생성 로직 검증
- [ ] Run/Job 레코드 생성 확인

### 6.3 Metrics Refinement
- [ ] run_id/job_id 기반 메트릭 계산 (시간 isolation)
- [ ] Sharpe Ratio 개선 (일별 수익률 기반 근사)
- [ ] MaxDD 계산 구현

### 6.4 Worker Timeout
- [ ] `mark_stale_jobs_as_failed()` 구현
- [ ] 테스트 PASS

### 6.5 문서 & Git
- [ ] `PHASE25-4_TUNER_CONSOLIDATION_DESIGN.md` (본 문서)
- [ ] `PHASE25-4_TUNING_PIPELINE_REPORT.md`
- [ ] `PHASE_ROADMAP.md` 업데이트
- [ ] Git commit

---

## 7. Known Limitations

### 7.1 메트릭 완전성
- 현재: 시간 기반 isolation (완벽하지 않음)
- 향후: trades 테이블에 run_id 컬럼 추가 (PHASE26)

### 7.2 Sharpe Ratio 근사
- 현재: trade별 pnl_pct 기반 근사
- 향후: equity curve 기반 정확한 계산 (PHASE26)

### 7.3 Local Grid Only
- 현재: Sequential 실행 (단일 Worker)
- 향후: 멀티 Worker 병렬 실행 (PHASE26)

### 7.4 Worker Timeout
- 현재: 수동 호출 또는 주기적 호출
- 향후: Worker 내부 자동 heartbeat (PHASE26)

---

## 8. References

- **PHASE25-1 Design**: docs/PHASE25/PHASE25-1_TUNING_CLUSTER_INFRA_DESIGN.md
- **PHASE25-2 Report**: (코드 참조)
- **PHASE25-3 Design**: docs/PHASE25/PHASE25-3_BAYESIAN_SEARCH_PIPELINE_DESIGN.md
- **PHASE_ROADMAP.md**: 프로젝트 전체 로드맵

---

**설계 완료일**: 2025-12-03  
**상태**: ✅ DESIGN COMPLETE  
**다음 단계**: Task B (Local Grid Search 구현)
