# PHASE25-1: Tuning Cluster Infra - 설계 문서

**Date**: 2025-12-03  
**Status**: 🔄 IN PROGRESS  
**Phase**: PHASE25-1 – Tuning Cluster Infrastructure (DB + Job Queue + Worker)  
**Purpose**: 중앙 DB 기반 튜닝 클러스터 인프라 구축 (알고리즘 제외, 뼈대만)

---

## 1. 목적 (Purpose)

### 1.1 한 줄 요약
> 중앙 DB + Job Queue + Worker Skeleton을 갖춘 **튜닝 클러스터 인프라**를 설계/구현하고,  
> PHASE25-2~3에서 Random/Bayesian/LocalGrid 알고리즘을 꽂을 수 있는 상태로 만드는 것.

### 1.2 배경
- **PHASE25-0**: Long-run PAPER Harness 완료 (인프라 Acceptance PASS)
- **PHASE24**: Redis/DB/Env/Config 인프라 베이스라인 확립
- **PHASE23**: Ensemble V2 구조 완성 (5-family, Score V2)
- **현재 상태**: 개별 전략/파라미터 튜닝을 위한 자동화 인프라 필요
- **TO-BE 비전** (ENSEMBLE_STRATEGY_TOBE_V2.md):
  - 3단계 튜닝 파이프라인: Random Search → Bayesian Optimization → Local Grid
  - 중앙 DB 기반 튜닝 클러스터 (여러 Worker가 job을 병렬 처리)
  - 파라미터 탐색 결과를 DB에 저장하여 분석/비교 가능

### 1.3 In-Scope (이번 PHASE25-1에서 구현할 것)
1. **DB 스키마 설계 & 구현**
   - 튜닝 관련 3계층 스키마: `tuning.runs`, `tuning.jobs`, `tuning.results`
   - 기존 DB 관리 방식(migrations, naming conventions)과 일관되게 구현
2. **Job Queue & Worker Skeleton**
   - `tuning/cluster/job_queue.py`: Job 생성/할당/상태 관리
   - `tuning/cluster/worker.py`: Worker 클래스 (dummy 실행)
   - `scripts/infra/phase25_1_run_worker.py`: Worker CLI
3. **테스트**
   - `tests/test_phase25_1_tuning_cluster_infra.py`: 단위/통합 테스트
4. **문서 & 로드맵 업데이트**
   - 이 설계 문서 + 실행 리포트 + PHASE_ROADMAP 갱신

### 1.4 Out of Scope (이번 PHASE25-1에서 절대 하지 말 것)
- Random Search / Bayesian / Local Grid **알고리즘 로직 구현** → PHASE25-2/3
- run_v2 / backtest 엔진 통합 → PHASE25-2/3 (지금은 dummy만)
- 대규모 성능 튜닝 / 모니터링 UI → PHASE27/28+

---

## 2. AS-IS 분석

### 2.1 기존 DB 구조
```
trading_db
├── monitoring (모니터링 계층)
│   └── signals - 개별 전략 신호
├── trading (거래 실행 계층)
│   ├── decisions - 통합 결정
│   ├── trades - 거래 기록
│   ├── positions - 현재 포지션
│   └── executions - 집행 로그
└── reporting (분석 계층)
    ├── strategy_performance - 전략별 성과
    └── daily_pnl - 일별 손익
```

**특징**:
- PostgreSQL, 스키마 계층 구조 (`monitoring`, `trading`, `reporting`)
- 멱등성 보장: `UNIQUE` 제약조건 활용
- 마이그레이션: `db/migrations/*.sql` 파일로 관리
- 연결 관리: `database/postgres.py::get_db_connection()` (lazy-load)

### 2.2 기존 튜닝 코드
- **위치**: `tuning/tuning_core.py`
- **방식**: Optuna 기반 베이지안 최적화
- **Storage**: Optuna의 PostgreSQL storage 사용
- **특징**:
  - Study/Trial 단위로 관리
  - Paper/Backtest 모드 지원
  - 파라미터 자동 발행 (`configs/<전략>/active.yml`)

**Pain Point**:
- Optuna Study는 "실험 단위"이지만, **튜닝 세션/Job/Result**의 명확한 구조가 없음
- 여러 Worker가 동시에 튜닝하는 "클러스터" 구조가 없음
- 튜닝 결과를 체계적으로 분석/비교하기 어려움

### 2.3 설계 방향
- **새 스키마 계층 추가**: `tuning` (monitoring/trading/reporting과 동급)
- **3개 테이블**: `tuning.runs`, `tuning.jobs`, `tuning.results`
- **Job Queue**: DB 기반 구현 (`SELECT FOR UPDATE SKIP LOCKED` 패턴)
- **Worker**: Dummy 실행만 (실제 엔진 호출은 PHASE25-2/3에서)
- **기존 Optuna와 분리**: 나중에 통합 가능하도록 인터페이스 설계

---

## 3. TO-BE 설계

### 3.1 DB 스키마

#### 3.1.1 스키마 계층 추가
```sql
CREATE SCHEMA IF NOT EXISTS tuning;
```

#### 3.1.2 테이블 1: `tuning.runs` (튜닝 세션)
**목적**: 전체 튜닝 세션 단위 (예: "scalping 전략 Random Search 100 trials")

| 컬럼 | 타입 | 설명 | 제약 |
|------|------|------|------|
| `run_id` | TEXT | 튜닝 세션 ID | PRIMARY KEY |
| `phase` | TEXT | PHASE 번호 | NOT NULL, 예: 'PHASE25-2' |
| `strategy_family` | TEXT | 전략 패밀리 | NOT NULL, 예: 'momentum' |
| `strategy_name` | TEXT | 전략 이름 | NOT NULL, 예: 'scalping' |
| `mode` | TEXT | 실행 모드 | NOT NULL, 'backtest'\|'paper'\|'live' |
| `tuning_method` | TEXT | 튜닝 방법 | NOT NULL, 'random'\|'bayesian'\|'grid' |
| `target_metric` | TEXT | 최적화 목표 | NOT NULL, 'sharpe'\|'pnl'\|'win_rate' 등 |
| `total_jobs` | INTEGER | 총 Job 수 | NOT NULL, DEFAULT 0 |
| `completed_jobs` | INTEGER | 완료된 Job 수 | NOT NULL, DEFAULT 0 |
| `failed_jobs` | INTEGER | 실패한 Job 수 | NOT NULL, DEFAULT 0 |
| `status` | TEXT | Run 상태 | NOT NULL, 'PENDING'\|'RUNNING'\|'COMPLETED'\|'FAILED'\|'CANCELLED' |
| `best_job_id` | TEXT | 최고 성과 Job ID | REFERENCES tuning.jobs(job_id) |
| `best_metric_value` | NUMERIC | 최고 메트릭 값 | |
| `seed` | INTEGER | Random seed | |
| `config_override` | JSONB | Config override | |
| `metadata` | JSONB | 추가 메타데이터 | |
| `created_at` | TIMESTAMPTZ | 생성 시각 | DEFAULT now() |
| `updated_at` | TIMESTAMPTZ | 갱신 시각 | DEFAULT now() |
| `started_at` | TIMESTAMPTZ | 시작 시각 | |
| `completed_at` | TIMESTAMPTZ | 완료 시각 | |

**인덱스**:
```sql
CREATE INDEX idx_tuning_runs_status ON tuning.runs(status, created_at DESC);
CREATE INDEX idx_tuning_runs_strategy ON tuning.runs(strategy_name, created_at DESC);
CREATE INDEX idx_tuning_runs_phase ON tuning.runs(phase, created_at DESC);
```

#### 3.1.3 테이블 2: `tuning.jobs` (단일 파라미터 셋 실행)
**목적**: 개별 파라미터 조합 실행 단위 (1 job = 1 backtest/paper 실행)

| 컬럼 | 타입 | 설명 | 제약 |
|------|------|------|------|
| `job_id` | TEXT | Job ID | PRIMARY KEY |
| `run_id` | TEXT | 소속 Run ID | NOT NULL, REFERENCES tuning.runs(run_id) ON DELETE CASCADE |
| `job_index` | INTEGER | Run 내 순번 | NOT NULL |
| `params_json` | JSONB | 파라미터 JSON | NOT NULL |
| `status` | TEXT | Job 상태 | NOT NULL, 'PENDING'\|'RUNNING'\|'COMPLETED'\|'FAILED'\|'CANCELLED' |
| `worker_id` | TEXT | 처리 중인 Worker ID | |
| `assigned_at` | TIMESTAMPTZ | Worker 할당 시각 | |
| `started_at` | TIMESTAMPTZ | 실행 시작 시각 | |
| `completed_at` | TIMESTAMPTZ | 완료 시각 | |
| `runtime_sec` | NUMERIC | 실행 시간 (초) | |
| `error_message` | TEXT | 에러 메시지 | |
| `created_at` | TIMESTAMPTZ | 생성 시각 | DEFAULT now() |
| `updated_at` | TIMESTAMPTZ | 갱신 시각 | DEFAULT now() |

**제약조건**:
```sql
UNIQUE(run_id, job_index)  -- Run 내 중복 방지
```

**인덱스**:
```sql
CREATE INDEX idx_tuning_jobs_status ON tuning.jobs(status, created_at DESC);
CREATE INDEX idx_tuning_jobs_run ON tuning.jobs(run_id, job_index);
CREATE INDEX idx_tuning_jobs_worker ON tuning.jobs(worker_id, updated_at DESC);
```

#### 3.1.4 테이블 3: `tuning.results` (실행 결과 메트릭)
**목적**: Job 실행 후 산출된 성과 메트릭

| 컬럼 | 타입 | 설명 | 제약 |
|------|------|------|------|
| `result_id` | TEXT | Result ID | PRIMARY KEY |
| `job_id` | TEXT | Job ID | NOT NULL, UNIQUE, REFERENCES tuning.jobs(job_id) ON DELETE CASCADE |
| `run_id` | TEXT | Run ID | NOT NULL, REFERENCES tuning.runs(run_id) ON DELETE CASCADE |
| `pnl` | NUMERIC | 총 PnL (USDT) | |
| `pnl_pct` | NUMERIC | PnL 비율 (%) | |
| `trade_count` | INTEGER | 거래 건수 | |
| `win_count` | INTEGER | 승리 건수 | |
| `lose_count` | INTEGER | 패배 건수 | |
| `win_rate` | NUMERIC | 승률 (%) | |
| `sharpe_ratio` | NUMERIC | Sharpe Ratio | |
| `max_drawdown` | NUMERIC | 최대 낙폭 (%) | |
| `max_drawdown_duration_hours` | NUMERIC | 최대 낙폭 지속 시간 | |
| `profit_factor` | NUMERIC | Profit Factor | |
| `avg_win` | NUMERIC | 평균 수익 | |
| `avg_lose` | NUMERIC | 평균 손실 | |
| `runtime_sec` | NUMERIC | 실행 시간 (초) | |
| `metrics_json` | JSONB | 추가 메트릭 | |
| `created_at` | TIMESTAMPTZ | 생성 시각 | DEFAULT now() |

**인덱스**:
```sql
CREATE INDEX idx_tuning_results_run ON tuning.results(run_id, sharpe_ratio DESC NULLS LAST);
CREATE INDEX idx_tuning_results_job ON tuning.results(job_id);
```

### 3.2 Job 상태 머신 (State Diagram)

```
                 ┌──────────┐
                 │ PENDING  │  ← Job 생성 시점
                 └─────┬────┘
                       │ acquire_next_job()
                       ▼
                 ┌──────────┐
        ┌────────│ RUNNING  │
        │        └─────┬────┘
        │              │
        │      ┌───────┴────────┐
        │      │                │
        │      ▼                ▼
        │ ┌──────────┐    ┌──────────┐
        │ │COMPLETED │    │  FAILED  │
        │ └──────────┘    └──────────┘
        │
        │ (Worker timeout/kill)
        ▼
   ┌──────────┐
   │CANCELLED │
   └──────────┘
```

**상태 전이 규칙**:
1. `PENDING → RUNNING`: Worker가 `acquire_next_job()` 호출 시
2. `RUNNING → COMPLETED`: Job 실행 성공 후 `mark_job_completed()` 호출 시
3. `RUNNING → FAILED`: Job 실행 실패 후 `mark_job_failed()` 호출 시
4. `RUNNING → CANCELLED`: Worker timeout/강제 종료 시 (관리자 개입)
5. `PENDING → CANCELLED`: Run 전체 취소 시

### 3.3 Job Queue API

**모듈**: `tuning/cluster/job_queue.py`

#### 3.3.1 Public API
```python
class JobQueue:
    """중앙 DB 기반 Job Queue"""
    
    def enqueue_job(
        self,
        run_id: str,
        params: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Job을 큐에 추가
        
        Args:
            run_id: 소속 Run ID
            params: 파라미터 딕셔너리
            metadata: 추가 메타데이터
            
        Returns:
            job_id: 생성된 Job ID
        """
        pass
    
    def acquire_next_job(
        self,
        worker_id: str,
        run_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        다음 실행할 Job을 가져옴 (동시성 안전)
        
        SELECT FOR UPDATE SKIP LOCKED 패턴 사용:
        - 여러 Worker가 동시에 호출해도 중복 할당 방지
        
        Args:
            worker_id: Worker ID
            run_id: 특정 Run만 처리할 경우 Run ID 지정
            
        Returns:
            Job 정보 딕셔너리 (없으면 None)
        """
        pass
    
    def mark_job_running(self, job_id: str, worker_id: str) -> bool:
        """Job 상태를 RUNNING으로 변경"""
        pass
    
    def mark_job_completed(
        self,
        job_id: str,
        result_metrics: Dict[str, Any]
    ) -> bool:
        """
        Job 완료 처리 및 결과 저장
        
        Args:
            job_id: Job ID
            result_metrics: 결과 메트릭 딕셔너리
                예: {'pnl': 123.45, 'trade_count': 10, 'win_rate': 0.6, ...}
        """
        pass
    
    def mark_job_failed(
        self,
        job_id: str,
        error_message: str
    ) -> bool:
        """Job 실패 처리"""
        pass
    
    def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """Run 전체 상태 조회"""
        pass
    
    def cancel_run(self, run_id: str) -> bool:
        """Run 전체 취소 (PENDING/RUNNING job 모두 CANCELLED로 변경)"""
        pass
```

#### 3.3.2 동시성 처리 (SELECT FOR UPDATE SKIP LOCKED)
```python
def acquire_next_job(self, worker_id: str, run_id: Optional[str] = None):
    """동시성 안전한 Job 할당"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # WHERE status = 'PENDING' AND (run_id = %s OR %s IS NULL)
            # ORDER BY created_at ASC
            # LIMIT 1
            # FOR UPDATE SKIP LOCKED  ← 핵심!
            #
            # 설명:
            # - FOR UPDATE: Row-level lock 획득
            # - SKIP LOCKED: 다른 트랜잭션이 잡고 있는 row는 건너뜀
            # → 여러 Worker가 동시에 호출해도 각각 다른 job을 가져감
            ...
```

### 3.4 Worker Skeleton

**모듈**: `tuning/cluster/worker.py`

#### 3.4.1 Worker 클래스
```python
class TuningWorker:
    """튜닝 Job을 처리하는 Worker"""
    
    def __init__(
        self,
        worker_id: str,
        job_queue: JobQueue,
        run_id: Optional[str] = None
    ):
        """
        Args:
            worker_id: Worker ID (예: "worker-001")
            job_queue: JobQueue 인스턴스
            run_id: 특정 Run만 처리할 경우 지정
        """
        self.worker_id = worker_id
        self.job_queue = job_queue
        self.run_id = run_id
        self.running = False
    
    def loop(self, once: bool = False):
        """
        Worker 메인 루프
        
        Args:
            once: True이면 1개 job만 처리 후 종료, False이면 계속 loop
        """
        self.running = True
        
        while self.running:
            job = self.job_queue.acquire_next_job(
                worker_id=self.worker_id,
                run_id=self.run_id
            )
            
            if job is None:
                if once:
                    break
                time.sleep(5)  # 5초 대기 후 재시도
                continue
            
            try:
                result = self.process_job(job)
                self.job_queue.mark_job_completed(job['job_id'], result)
            except Exception as e:
                self.job_queue.mark_job_failed(job['job_id'], str(e))
            
            if once:
                break
    
    def process_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Job 처리 (PHASE25-1에서는 dummy 실행만)
        
        Args:
            job: Job 정보 딕셔너리
                {'job_id', 'run_id', 'params_json', ...}
        
        Returns:
            result_metrics: 결과 메트릭 딕셔너리
        
        Note:
            PHASE25-2/3에서 실제 엔진 호출 로직을 여기에 주입
        """
        import time
        import random
        
        logger.info(f"[{self.worker_id}] Processing job {job['job_id']}")
        
        # Dummy 실행: 1~3초 sleep + 랜덤 메트릭 생성
        sleep_time = random.uniform(1.0, 3.0)
        time.sleep(sleep_time)
        
        # Dummy 메트릭
        dummy_result = {
            'pnl': random.uniform(-100, 300),
            'trade_count': random.randint(10, 50),
            'win_rate': random.uniform(0.3, 0.7),
            'sharpe_ratio': random.uniform(-0.5, 2.0),
            'max_drawdown': random.uniform(5, 25),
            'runtime_sec': sleep_time
        }
        
        logger.info(f"[{self.worker_id}] Job {job['job_id']} completed: PnL={dummy_result['pnl']:.2f}")
        
        return dummy_result
    
    def stop(self):
        """Worker 중지"""
        self.running = False
```

#### 3.4.2 Worker CLI

**파일**: `scripts/infra/phase25_1_run_worker.py`

```python
#!/usr/bin/env python3
"""
PHASE25-1: Tuning Worker CLI
=============================
튜닝 Job을 처리하는 Worker를 실행하는 CLI

사용법:
    # 한 번만 실행
    python scripts/infra/phase25_1_run_worker.py --worker-id worker-001 --once
    
    # 계속 루프 (Ctrl+C로 종료)
    python scripts/infra/phase25_1_run_worker.py --worker-id worker-001
    
    # 특정 Run만 처리
    python scripts/infra/phase25_1_run_worker.py --worker-id worker-001 --run-id run_abc123
"""
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tuning.cluster.job_queue import JobQueue
from tuning.cluster.worker import TuningWorker
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


def main():
    parser = argparse.ArgumentParser(description="PHASE25-1 Tuning Worker")
    parser.add_argument("--worker-id", required=True, help="Worker ID (예: worker-001)")
    parser.add_argument("--once", action="store_true", help="1개 job만 처리 후 종료")
    parser.add_argument("--run-id", default=None, help="특정 Run만 처리")
    
    args = parser.parse_args()
    
    logger.info(f"🚀 Tuning Worker 시작: {args.worker_id}")
    if args.run_id:
        logger.info(f"   Target Run: {args.run_id}")
    if args.once:
        logger.info(f"   Mode: One-shot")
    else:
        logger.info(f"   Mode: Loop (Ctrl+C to stop)")
    
    job_queue = JobQueue()
    worker = TuningWorker(
        worker_id=args.worker_id,
        job_queue=job_queue,
        run_id=args.run_id
    )
    
    try:
        worker.loop(once=args.once)
    except KeyboardInterrupt:
        logger.info("⏹️  Worker 중지")
        worker.stop()
    
    logger.info("✅ Worker 종료")


if __name__ == "__main__":
    main()
```

---

## 4. 마이그레이션 SQL

**파일**: `db/migrations/add_tuning_cluster_tables.sql`

```sql
-- ================================================================
-- PHASE25-1: Tuning Cluster Infrastructure
-- ================================================================
-- 튜닝 클러스터 관련 스키마 및 테이블 생성
--
-- 테이블:
-- - tuning.runs: 튜닝 세션 (예: "scalping Random Search 100 trials")
-- - tuning.jobs: 개별 파라미터 실행 (1 job = 1 backtest/paper)
-- - tuning.results: 실행 결과 메트릭
--
-- Date: 2025-12-03
-- Author: PHASE25-1 Implementation
-- ================================================================

-- 1. tuning 스키마 생성
CREATE SCHEMA IF NOT EXISTS tuning;

-- 2. tuning.runs 테이블
CREATE TABLE IF NOT EXISTS tuning.runs (
    run_id TEXT PRIMARY KEY,
    phase TEXT NOT NULL,
    strategy_family TEXT NOT NULL,
    strategy_name TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('backtest', 'paper', 'live')),
    tuning_method TEXT NOT NULL CHECK (tuning_method IN ('random', 'bayesian', 'grid', 'manual')),
    target_metric TEXT NOT NULL,
    total_jobs INTEGER NOT NULL DEFAULT 0,
    completed_jobs INTEGER NOT NULL DEFAULT 0,
    failed_jobs INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')) DEFAULT 'PENDING',
    best_job_id TEXT,
    best_metric_value NUMERIC,
    seed INTEGER,
    config_override JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- 3. tuning.jobs 테이블
CREATE TABLE IF NOT EXISTS tuning.jobs (
    job_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES tuning.runs(run_id) ON DELETE CASCADE,
    job_index INTEGER NOT NULL,
    params_json JSONB NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')) DEFAULT 'PENDING',
    worker_id TEXT,
    assigned_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    runtime_sec NUMERIC,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(run_id, job_index)
);

-- 4. tuning.results 테이블
CREATE TABLE IF NOT EXISTS tuning.results (
    result_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL UNIQUE REFERENCES tuning.jobs(job_id) ON DELETE CASCADE,
    run_id TEXT NOT NULL REFERENCES tuning.runs(run_id) ON DELETE CASCADE,
    pnl NUMERIC,
    pnl_pct NUMERIC,
    trade_count INTEGER,
    win_count INTEGER,
    lose_count INTEGER,
    win_rate NUMERIC,
    sharpe_ratio NUMERIC,
    max_drawdown NUMERIC,
    max_drawdown_duration_hours NUMERIC,
    profit_factor NUMERIC,
    avg_win NUMERIC,
    avg_lose NUMERIC,
    runtime_sec NUMERIC,
    metrics_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. 인덱스 생성

-- runs 인덱스
CREATE INDEX idx_tuning_runs_status ON tuning.runs(status, created_at DESC);
CREATE INDEX idx_tuning_runs_strategy ON tuning.runs(strategy_name, created_at DESC);
CREATE INDEX idx_tuning_runs_phase ON tuning.runs(phase, created_at DESC);

-- jobs 인덱스
CREATE INDEX idx_tuning_jobs_status ON tuning.jobs(status, created_at DESC);
CREATE INDEX idx_tuning_jobs_run ON tuning.jobs(run_id, job_index);
CREATE INDEX idx_tuning_jobs_worker ON tuning.jobs(worker_id, updated_at DESC);

-- results 인덱스
CREATE INDEX idx_tuning_results_run ON tuning.results(run_id, sharpe_ratio DESC NULLS LAST);
CREATE INDEX idx_tuning_results_job ON tuning.results(job_id);

-- 6. FK 추가 (best_job_id)
-- Note: best_job_id는 circular dependency를 피하기 위해 FK 제약조건 추가하지 않음
-- 대신 application level에서 관리

-- ================================================================
-- 마이그레이션 완료
-- ================================================================
```

---

## 5. Acceptance Criteria

PHASE25-1 완료 기준:

1. **DB 스키마** ✅
   - `tuning` 스키마 생성
   - `tuning.runs`, `tuning.jobs`, `tuning.results` 테이블 정의
   - 인덱스 및 제약조건 적용
   - 마이그레이션 SQL 실행 성공

2. **Job Queue** ✅
   - `tuning/cluster/job_queue.py` 구현
   - Public API: `enqueue_job`, `acquire_next_job`, `mark_job_running`, `mark_job_completed`, `mark_job_failed`
   - 동시성 안전: `SELECT FOR UPDATE SKIP LOCKED` 패턴 구현
   - 2개 이상 Worker가 동시에 `acquire_next_job` 호출 시 중복 할당 방지

3. **Worker Skeleton** ✅
   - `tuning/cluster/worker.py` 구현
   - `TuningWorker` 클래스: `loop(once=True/False)` 지원
   - `process_job()`: Dummy 실행 (sleep + 랜덤 메트릭 생성)
   - `scripts/infra/phase25_1_run_worker.py`: Worker CLI

4. **테스트** ✅
   - `tests/test_phase25_1_tuning_cluster_infra.py` 작성
   - 테스트 시나리오:
     1. DB 스키마 기본 동작 (INSERT/SELECT/UPDATE)
     2. Job Queue 동시성 (2개 Worker가 각각 다른 job 할당받는지 확인)
     3. Worker Skeleton (dummy 실행 후 COMPLETED 상태 및 메트릭 저장 확인)
   - 전체 테스트 PASS

5. **문서 & 로드맵** ✅
   - `docs/PHASE25/PHASE25-1_TUNING_CLUSTER_INFRA_DESIGN.md` (이 문서)
   - `docs/PHASE25/PHASE25-1_TUNING_CLUSTER_INFRA_REPORT.md` (실행 리포트)
   - `PHASE_ROADMAP.md`: PHASE25-1 상태 ✅ COMPLETE로 갱신

6. **Git** ✅
   - 의미 있는 커밋 메시지
   - 불필요한 임시 파일/디버그 출력 제거

---

## 6. Known Issues & Limitations

### 6.1 Known Issues (PHASE25-1 범위 내)
- **Worker Timeout 처리 없음**: Worker가 중간에 죽으면 `RUNNING` 상태로 남음
  - 해결: PHASE25-2에서 Worker heartbeat + timeout 로직 추가
- **Run 취소 시 실행 중인 Worker 강제 종료 없음**: `cancel_run()` 호출 시 DB 상태만 변경
  - 해결: PHASE25-2에서 Worker 제어 메커니즘 추가

### 6.2 Limitations (Out of Scope)
- **실제 엔진 호출 없음**: Dummy 메트릭만 생성 (PHASE25-2/3에서 구현)
- **알고리즘 로직 없음**: Random/Bayesian/Grid 파라미터 생성 로직 없음 (PHASE25-2/3)
- **대규모 성능 튜닝 없음**: 수만 개 job 처리 시 성능 이슈 가능 (PHASE27+)

---

## 7. Next Steps (PHASE25-2/3)

### PHASE25-2: Random Search Pipeline
- Random Search 알고리즘 구현
- `process_job()`에서 실제 backtest 엔진 호출
- 100~1000 trials 실행 및 결과 분석

### PHASE25-3: Bayesian + Local Grid
- Bayesian Optimization (Optuna TPE) 통합
- Local Grid Search around best candidates
- 최종 파라미터 셋 선정 로직

---

**Document Status**: 🟢 READY FOR IMPLEMENTATION  
**Review Date**: 2025-12-03  
**Author**: Cascade AI (PHASE25-1 Design)
