# PHASE28-3: Random Search Round 1 Execution - Design Document

**일시**: 2025-12-06  
**상태**: ✅ **IMPLEMENTATION COMPLETE**  
**판정**: Infrastructure and automation scripts ready for execution

---

## 🎯 Objectives

### Primary Goals (PHASE28-3 Scope)
1. **Random Search at Scale**: ≥20 trials across ≥2 market regimes
2. **Multi-Regime Evaluation**: bull, range, neutral 구간 균등 분포
3. **Automated Execution**: 완전 자동화된 실행 스크립트 (환경 검증 포함)
4. **Result Aggregation**: Top-N 후보 자동 선정 및 Markdown/JSON 리포트 생성
5. **Zero Manual Intervention**: 사용자 입력 없이 전체 프로세스 실행

### Out-of-Scope
- Bayesian Search (PHASE28-4 이후)
- Ensemble 재통합 (PHASE28-5)
- Multi-worker parallelization (Future optimization)

---

## 📐 Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│         PHASE28-3: Automated Random Search Pipeline          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  scripts/tuning/phase28_3_run_random_search_round1.py       │
│  ├─ Environment Checks                                       │
│  │  ├─ Python version (≥3.9)                                │
│  │  ├─ Postgres reachability                                │
│  │  └─ Redis reachability                                    │
│  │                                                            │
│  ├─ Run Setup                                                │
│  │  ├─ Generate unique run_id (timestamp-based)             │
│  │  ├─ Load ParamSpace YAML                                 │
│  │  └─ Validate market periods                              │
│  │                                                            │
│  ├─ Job Submission                                           │
│  │  ├─ For each market period:                              │
│  │  │  ├─ Create Run (JobQueue.create_run)                  │
│  │  │  ├─ Sample N param sets (ParamSpace.sample)           │
│  │  │  └─ Enqueue N jobs (JobQueue.enqueue_job)             │
│  │  └─ Start Worker (TuningWorker.loop)                     │
│  │                                                            │
│  ├─ Progress Monitoring                                      │
│  │  ├─ Periodic status print (every 30s)                    │
│  │  ├─ Job completion ratio tracking                        │
│  │  └─ Auto-exit when all jobs COMPLETED                    │
│  │                                                            │
│  └─ Result Aggregation                                       │
│     ├─ Query tuning.results (current run_id)                │
│     ├─ Filter valid results (trade_count≥10, MDD≤20%)       │
│     ├─ Sort by sharpe_like_ratio DESC                       │
│     ├─ Select Top-N per period + Overall Top-N              │
│     ├─ Generate Markdown report                             │
│     └─ Generate JSON results                                 │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Environment Check (Python/DB/Redis)
      │
      ├─→ PASS → Continue
      └─→ FAIL → Exit with error message
            │
            ↓
Load ParamSpace YAML
      │
      ↓
For each market period (bull, range, neutral):
      │
      ├─→ Create Run (run_id, period metadata)
      │         │
      │         ↓
      ├─→ Sample N param sets (random seed = seed + trial_index)
      │         │
      │         ↓
      ├─→ Enqueue N jobs (JobQueue)
      │         │
      │         ↓
      └─→ Start TuningWorker
                │
                ├─→ Loop until all jobs COMPLETED
                │         │
                │         ├─→ Acquire job
                │         ├─→ Backtest (run_v2)
                │         ├─→ Extract metrics
                │         └─→ Mark job COMPLETED
                │
                ↓
      Periodic Status Check (every 30s)
                │
                ├─→ Print: "[bull] 5/10 jobs completed..."
                │
                ↓
      All jobs COMPLETED
                │
                ↓
Query tuning.results (run_id filter)
                │
                ↓
Filter & Sort (trade_count≥10, sharpe_ratio DESC)
                │
                ↓
Select Top-N (10 per period, 10 overall)
                │
                ├─→ Markdown Report → docs/PHASE28/PHASE28-3_RESULTS.md
                └─→ JSON Results → reports/tuning/phase28_3/results.json
```

---

## 🔧 Implementation Details

### 1. Environment Checks

**Location**: `scripts/tuning/phase28_3_run_random_search_round1.py`

```python
def check_environment():
    """환경 검증: Python version, DB, Redis"""
    # Python version
    if sys.version_info < (3, 9):
        raise EnvironmentError("Python 3.9+ required")
    
    # Postgres
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as e:
        raise EnvironmentError(f"Postgres unreachable: {e}")
    
    # Redis (optional check, 현재 tuning은 Redis 필수 아님)
    # ...
    
    logger.info("✅ Environment check PASSED")
```

### 2. Run ID Generation

```python
def generate_run_id(base_name: str) -> str:
    """Generate unique run_id with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}"

# Example: "btc5m_baseline_tuning_round1_20251206_153045"
```

### 3. Job Submission

```python
def submit_jobs(param_space: ParamSpace, period: str, n_trials: int, seed: int):
    """Submit N jobs for a market period"""
    run_id = generate_run_id(f"phase28_3_{period}")
    
    # Create run
    job_queue.create_run(
        run_id=run_id,
        phase="PHASE28-3",
        strategy_family="baseline",
        strategy_name="btc5m_baseline_v1",
        tuning_method="random",
        target_metric="sharpe_like_ratio",
        metadata={"period": period, "n_trials": n_trials}
    )
    
    # Enqueue N jobs
    for i in range(n_trials):
        params = param_space.sample(seed=seed + i)
        job_queue.enqueue_job(
            run_id=run_id,
            params=params,
            period_name=period
        )
    
    return run_id
```

### 4. Progress Monitoring

```python
def monitor_progress(run_id: str, total_jobs: int, check_interval: int = 30):
    """Monitor job completion and print status"""
    while True:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT status, COUNT(*) as count
                    FROM tuning.jobs
                    WHERE run_id = %s
                    GROUP BY status
                """, (run_id,))
                status_counts = dict(cur.fetchall())
        
        completed = status_counts.get('COMPLETED', 0)
        failed = status_counts.get('FAILED', 0)
        
        print(f"[{run_id}] Progress: {completed}/{total_jobs} completed, {failed} failed")
        
        if completed + failed >= total_jobs:
            break
        
        time.sleep(check_interval)
```

### 5. Result Aggregation

```python
def aggregate_results(run_ids: List[str], top_n: int = 10):
    """Aggregate results and generate reports"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Query results
            cur.execute("""
                SELECT 
                    r.run_id,
                    r.job_id,
                    r.pnl,
                    r.pnl_pct,
                    r.sharpe_ratio,
                    r.trade_count,
                    r.win_rate,
                    r.max_drawdown,
                    j.params_json
                FROM tuning.results r
                JOIN tuning.jobs j ON r.job_id = j.job_id
                WHERE r.run_id = ANY(%s)
                  AND r.trade_count >= 10
                  AND r.max_drawdown <= 20.0
                ORDER BY r.sharpe_ratio DESC
            """, (run_ids,))
            results = cur.fetchall()
    
    # Select Top-N
    top_n_results = results[:top_n]
    
    # Generate Markdown
    generate_markdown_report(top_n_results, "docs/PHASE28/PHASE28-3_RESULTS.md")
    
    # Generate JSON
    generate_json_results(results, "reports/tuning/phase28_3/results.json")
```

---

## ✅ Acceptance Criteria

### A1. Random Search Execution
- [ ] ≥20 trials 성공 실행
- [ ] ≥2 market periods 분포 (e.g., bull + range, or range + neutral)
- [ ] tuning.results에 메트릭 자동 기록
- [ ] 정상 완료: 모든 job.status='COMPLETED'

**Minimum**: 20 trials total (e.g., 10 per period × 2 periods)

---

### A2. Automated Execution
- [ ] 환경 검증 자동 실행 (Python/DB/Redis)
- [ ] 사용자 입력 없이 전체 프로세스 완료
- [ ] 에러 발생 시 자동 로깅 (DB + stdout)
- [ ] 진행 상황 자동 출력 (30s 간격)

**Test Command**:
```bash
python scripts/tuning/phase28_3_run_random_search_round1.py --trials 20 --periods bull,range
```

---

### A3. Result Aggregation
- [ ] Top-N 선정 (sharpe_like_ratio 기준, trade_count≥10, MDD≤20%)
- [ ] Markdown 리포트 생성: `docs/PHASE28/PHASE28-3_RESULTS.md`
- [ ] JSON 결과 저장: `reports/tuning/phase28_3/results.json`
- [ ] Period별 분석 + 전체 Top-N 통합

**Expected Output**:
- Markdown: Top 10 per period + Overall Top 10 + 추천 후보 3개
- JSON: 전체 결과 raw data (filtering 후)

---

### A4. Testing
- [ ] Unit tests: `pytest -q tests/tuning/test_phase28_3_automation.py`
- [ ] Smoke test: 2 trials × 1 period, DB writes 검증
- [ ] No user input during tests

**Test Coverage**:
- Environment check logic
- Run ID generation (uniqueness)
- Job submission (param sampling)
- Progress monitoring (status query)
- Result aggregation (filtering, sorting)

---

### A5. Documentation
- [ ] Design Doc: `docs/PHASE28/PHASE28-3_RANDOM_SEARCH_ROUND1_DESIGN.md`
- [ ] Results Report: `docs/PHASE28/PHASE28-3_RESULTS.md` (auto-generated)
- [ ] PHASE_ROADMAP.md 업데이트 (PHASE28-2 COMPLETE, PHASE28-3 IN PROGRESS)

---

## 📝 Files to Create/Modify

### Created
```
scripts/tuning/phase28_3_run_random_search_round1.py  (NEW, ~400 LOC)
tests/tuning/test_phase28_3_automation.py              (NEW, ~200 LOC)
docs/PHASE28/PHASE28-3_RANDOM_SEARCH_ROUND1_DESIGN.md (NEW, this file)
docs/PHASE28/PHASE28-3_RESULTS.md                     (auto-generated)
reports/tuning/phase28_3/results.json                  (auto-generated)
```

### Modified
```
PHASE_ROADMAP.md (PHASE28-2 status update, PHASE28-3 entry)
```

---

## 🚀 Execution Plan

### Step 1: Implementation
1. Create `scripts/tuning/phase28_3_run_random_search_round1.py`
   - Environment checks
   - Job submission loop
   - Progress monitoring
   - Result aggregation

2. Create unit tests
   - `tests/tuning/test_phase28_3_automation.py`

### Step 2: Testing
```bash
# Unit tests
pytest -q tests/tuning/test_phase28_3_automation.py

# Smoke test (2 trials, 1 period)
python scripts/tuning/phase28_3_run_random_search_round1.py --trials 2 --periods bull --smoke

# Full run (20 trials, 2 periods)
python scripts/tuning/phase28_3_run_random_search_round1.py --trials 20 --periods bull,range
```

### Step 3: Verification
```sql
-- Run 상태 확인
SELECT run_id, phase, total_jobs, completed_jobs, status
FROM tuning.runs
WHERE phase = 'PHASE28-3'
ORDER BY created_at DESC;

-- 결과 확인
SELECT r.job_id, r.pnl_pct, r.sharpe_ratio, r.trade_count
FROM tuning.results r
WHERE r.run_id LIKE 'phase28_3%'
ORDER BY r.sharpe_ratio DESC
LIMIT 10;
```

### Step 4: Documentation
1. Generate reports (auto)
2. Update PHASE_ROADMAP.md
3. Git commit

---

## ⚠️ Known Limitations

### 1. Sequential Execution
- **Current**: Jobs are processed sequentially by single worker
- **Future**: Multi-worker parallelization (PHASE29+)

### 2. Market Period Selection
- **Current**: Manual selection via CLI args (--periods bull,range)
- **Future**: Auto-select periods based on historical volatility/regime

### 3. Parameter Space
- **Current**: Fixed 10 parameters from PHASE28-2 ParamSpace
- **Future**: Expand parameter space based on PHASE28-3 results

---

## 📊 Expected Outcomes

### After 20 Trials × 2 Periods (40 jobs total)
- **Total Jobs**: 40개
- **Valid Results**: ~28-32개 (70-80%, trade_count≥10 필터링 후)
- **Top 10 per period**: Period별 최적 파라미터 세트
- **Overall Top 10**: 전체 통합 최적 파라미터 세트
- **Top 3 Candidates**: PHASE28-4/PHASE29에 넘길 추천 파라미터

### Performance Expectations
- **Execution Time**: 40 jobs × 30-60초 = 20-40분
- **DB Storage**: ~40 rows (tuning.results) + ~80-200 rows (trading.trades)
- **Report Size**: Markdown ~5KB, JSON ~30-50KB

---

## 🔗 Related Documents

- [PHASE28-2 Design](./PHASE28-2_TUNING_ROUND1_DESIGN.md)
- [PHASE28-2 Final Report](./PHASE28_2_FINAL_REPORT.md)
- [PHASE_ROADMAP.md](../../PHASE_ROADMAP.md)

---

## 🎉 Implementation Summary

### Completed (2025-12-06)

#### 1. Automated Execution Script
- **File**: `scripts/tuning/phase28_3_run_random_search_round1.py` (~610 LOC)
- **Features**:
  - ✅ Environment checks (Python version, Postgres connection)
  - ✅ ParamSpace loading and validation
  - ✅ Job submission (RandomSearchTuner + JobQueue)
  - ✅ Worker execution with run_id filtering
  - ✅ Progress monitoring (periodic status check)
  - ✅ Result aggregation (filter by trade_count≥10, MDD≤20%)
  - ✅ Report generation (Markdown + JSON)

#### 2. Unit Tests
- **File**: `tests/tuning/test_phase28_3_automation.py` (~265 LOC)
- **Results**: ✅ **8/8 PASS**
  - Environment check (Python version, DB connection)
  - ParamSpace loading and sampling
  - Run ID generation (uniqueness with milliseconds)
  - Job submission (smoke test with DB writes)
  - Result aggregation (empty results handling)
  - Report generation (Markdown + JSON with mock data)

#### 3. Smoke Test
- **Command**: `python scripts/tuning/phase28_3_run_random_search_round1.py --trials 2 --periods bull --smoke`
- **Results**: ✅ **SUCCESS**
  - Run ID: `phase28_3_bull_e75e59bd`
  - Trial 1: 3 trades, PnL: -131.42, Sharpe: -59.74
  - Trial 2: 4 trades, PnL: -67.71, Sharpe: -11.82, Win Rate: 25%
  - DB records: ✅ `tuning.results` and `trading.trades` properly linked

#### 4. Code Improvements
- Added `generate_run_id()` function with millisecond precision
- Enhanced Worker with run_id filtering to prevent cross-run job processing
- Fixed TuningWorker initialization (job_queue parameter)

---

**Status**: ✅ **IMPLEMENTATION COMPLETE**

**Next**: Execute full Random Search (20+ trials, 2+ periods) when ready
