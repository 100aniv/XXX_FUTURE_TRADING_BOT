# PHASE28-2: Single Strategy Tuning Round 1 - Design Document

**일시**: 2025-12-05  
**상태**: ✅ **INFRASTRUCTURE READY** - Ready for Execution  
**판정**: **PENDING EXECUTION** - Tuning pipeline wired, awaiting Random Search run

---

## 🎯 Objectives

### Primary Goals
1. **Tuning Pipeline 구축**: PHASE25 Tuning Cluster를 btc5m_baseline_v1 전략에 연결
2. **Random Search 실행**: 25 trials (소규모, end-to-end 검증용)
3. **Bayesian Search Skeleton**: 3-5 trials (dry-run, 인프라 동작 확인)
4. **Results Infrastructure**: DB → Markdown/JSON 리포트 자동 생성

### Secondary Goals
- PHASE28-1 config 구조와 PHASE25 Tuning Cluster 호환성 확보
- Worker가 strategies 섹션을 지원하도록 확장
- 최소 침투 원칙: Engine/SSOT/Ensemble Core 무손상

---

## 📐 Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    PHASE28-2 Tuning Pipeline                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ParamSpace YAML                                              │
│  └─ configs/tuning/phase28_2_btc5m_baseline_paramspace.yml  │
│     ├─ run_metadata (phase, strategy, target_metric)        │
│     ├─ param_space (10 parameters)                          │
│     ├─ market_periods (bull, range, neutral)                │
│     └─ acceptance criteria                                   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Random Search Runner                        │   │
│  │  scripts/tuning/phase28_2_run_random_search.py       │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  1. Load ParamSpace YAML                             │   │
│  │  2. Create ParamSpace object                         │   │
│  │  3. For each period:                                 │   │
│  │     - Create Run (JobQueue.create_run)               │   │
│  │     - Generate N random param sets                   │   │
│  │     - Enqueue Jobs (JobQueue.enqueue_job)            │   │
│  │     - Start Worker (process_job → run_v2)            │   │
│  │  4. Results → tuning.results table                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Bayesian Search Runner (Skeleton)            │   │
│  │  scripts/tuning/phase28_2_run_bayesian_search.py    │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  1. Load ParamSpace YAML                             │   │
│  │  2. Create BayesianSearchConfig                      │   │
│  │  3. Run Optuna sequential (3-5 trials)               │   │
│  │  4. Results → tuning.results table                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Results Summarizer                         │   │
│  │  scripts/research/phase28_2_summarize_tuning_results.py│ │
│  ├──────────────────────────────────────────────────────┤   │
│  │  1. Query tuning.results (phase=PHASE28-2)           │   │
│  │  2. Filter valid results (min_trades≥10, MDD≤20%)    │   │
│  │  3. Group by period                                   │   │
│  │  4. Select Top N by sharpe_ratio                     │   │
│  │  5. Generate Markdown + JSON reports                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
ParamSpace YAML
      │
      ├─→ Random Search Runner
      │         │
      │         ├─→ ParamSpace.sample() × N
      │         │
      │         ├─→ JobQueue.create_run()
      │         │
      │         ├─→ JobQueue.enqueue_job() × N
      │         │
      │         └─→ TuningWorker.loop()
      │                   │
      │                   ├─→ Config merge (base + params)
      │                   │
      │                   ├─→ run_v2(mode=backtest, config)
      │                   │
      │                   └─→ JobQueue.mark_job_completed(metrics)
      │                             │
      │                             ↓
      │                       tuning.results table
      │
      └─→ Results Summarizer
                │
                ├─→ Query tuning.results
                │
                ├─→ Filter & Sort
                │
                ├─→ Generate Markdown
                │
                └─→ Generate JSON
```

---

## 🔧 Parameter Space

### 10 Tunable Parameters

| Parameter | Type | Range | Baseline | Description |
|-----------|------|-------|----------|-------------|
| **rsi_long_threshold** | int | 40-48 | 45 | LONG 진입 RSI (낮을수록 공격적) |
| **rsi_short_threshold** | int | 52-58 | 55 | SHORT 진입 RSI (높을수록 공격적) |
| **bb_std_main** | float | 0.9-1.2 | 1.0 | BB Main 밴드 (std 배수) |
| **bb_std_strong** | float | 1.3-1.6 | 1.5 | BB Strong 밴드 (극단 진입) |
| **adx_trend_threshold** | int | 18-28 | 25 | ADX Trend vs Range 분류 |
| **momentum_lookback** | categorical | [3,5,7,10] | 5 | Momentum 계산 lookback |
| **momentum_threshold** | float | 0.0005-0.002 | 0.001 | Momentum 변화율 threshold |
| **atr_mult_sl** | float | 1.0-2.0 | 1.5 | Stop Loss 배수 (ATR 기준) |
| **rr** | float | 1.2-2.0 | 1.5 | Risk-Reward ratio |
| **max_hold_minutes** | categorical | [45,60,90,120] | 60 | 최대 보유 시간 (분) |

### Parameter Space Size
- **Total Combinations**: ~10^7 (이산화 가정)
- **Random Search Coverage**: 25 trials ≈ 0.0003% (초기 탐색)
- **Bayesian Search Coverage**: 3-5 trials (dry-run)

---

## 📊 Market Periods

### 3 Periods for Robustness

| Period | Name | Dates | Weight | Description |
|--------|------|-------|--------|-------------|
| **bull** | Bull Trend | 2024-11-01 ~ 2024-11-30 | 1.0 | 상승 추세 구간 |
| **range** | Range Consolidation | 2024-10-01 ~ 2024-10-31 | 1.0 | 횡보 구간 |
| **neutral** | Neutral Period | 2024-11-30 ~ 2024-12-30 | 1.5 | 중립 구간 (최근, 높은 가중치) |

---

## 🎯 Metrics

### Primary Metric
- **sharpe_like_ratio**: Sharpe-like ratio (일별 수익률 기반)
  - Direction: **maximize**
  - 목적: 리스크 대비 수익성 최적화

### Secondary Metrics (Filtering)
- **total_trades**: 최소 10건 (너무 적으면 제외)
- **max_drawdown**: 최대 20% (초과 시 제외)
- **win_rate**: 승률 (평가용)
- **net_pnl**: 순수익 (평가용)

---

## 🔨 Implementation Details

### 1. Worker Config Compatibility Fix

**Problem**: Worker가 PHASE28-1 config 구조 (`strategies.{strategy_name}`)를 지원하지 않음

**Solution**: Worker에 2가지 구조 지원 추가

```python
# tuning/cluster/worker.py (PHASE28-2 수정)

# 방식 1: strategy.{selected}.params (PHASE25 원래 구조)
strategy_section = config.get('strategy', {})
selected = strategy_section.get('selected', strategy_section.get('selector', 'scalping'))

if selected in strategy_section:
    # ... params 덮어쓰기

# 방식 2: strategies.{strategy_name} (PHASE27/28-1 구조)
strategies_section = config.get('strategies', {})
if selected in strategies_section:
    for key, value in params.items():
        strategies_section[selected][key] = value
```

**Impact**: PHASE28-1 config를 Worker가 인식하여 파라미터 override 가능

### 2. Random Search Execution Flow

```python
# scripts/tuning/phase28_2_run_random_search.py

1. Load YAML → ParamSpace object
2. For each period (bull/range/neutral):
   a. Create RandomSearchConfig
   b. RandomSearchTuner.create_run_and_jobs()
      - JobQueue.create_run(run_id, metadata)
      - For i in range(n_trials):
          params = param_space.sample(seed=seed+i)
          JobQueue.enqueue_job(run_id, params)
   c. TuningWorker.loop()
      - Acquire job
      - Load base_config + params override
      - run_v2(mode=backtest, config)
      - Extract metrics from DB
      - JobQueue.mark_job_completed(job_id, metrics)
3. Results → tuning.results table
```

### 3. Results Summarizer Logic

```python
# scripts/research/phase28_2_summarize_tuning_results.py

1. Query: SELECT * FROM tuning.results WHERE phase='PHASE28-2'
2. Group by period_name
3. For each period:
   - Filter: trade_count >= 10, max_drawdown <= 20%
   - Sort by sharpe_ratio DESC
   - Select top 10
4. Overall Top 10 across all periods
5. Generate Markdown:
   - Period별 Top 10 테이블
   - 전체 Top 10 테이블
   - 추천 파라미터 후보 (Top 3)
6. Generate JSON: 전체 결과 raw data
```

---

## ✅ Acceptance Criteria

### A1. Random Search Execution
- [x] Random Search Runner 구현 완료
- [ ] **PENDING**: 실제 실행 (≥20 trials)
- [ ] **PENDING**: tuning.runs/results에 결과 저장 확인

### A2. Bayesian Search Skeleton
- [x] Bayesian Search Runner 구현 완료
- [ ] **PENDING**: Dry-run 실행 (≥3 trials)
- [ ] **PENDING**: end-to-end 동작 확인

### A3. Results Summarizer
- [x] Summarizer 스크립트 구현 완료
- [ ] **PENDING**: Markdown 리포트 생성 확인
- [ ] **PENDING**: docs/PHASE28/PHASE28-2_TUNING_ROUND1_REPORT.md 생성

### A4. Tests
- [x] Unit Tests: 16/16 PASS
- [x] Regression Tests: 26/26 PASS
- [x] SSOT/Engine 무손상 확인

### A5. Documentation
- [x] Design Doc: docs/PHASE28/PHASE28-2_TUNING_ROUND1_DESIGN.md
- [ ] **PENDING**: Report Doc: docs/PHASE28/PHASE28-2_TUNING_ROUND1_REPORT.md (실행 후 생성)

---

## 📝 Files Created/Modified

### Created
```
configs/tuning/phase28_2_btc5m_baseline_paramspace.yml
scripts/tuning/phase28_2_run_random_search.py
scripts/tuning/phase28_2_run_bayesian_search.py
scripts/research/phase28_2_summarize_tuning_results.py
tests/test_phase28_2_tuning_infrastructure.py
docs/PHASE28/PHASE28-2_TUNING_ROUND1_DESIGN.md
```

### Modified
```
tuning/cluster/worker.py (PHASE28-2: strategies 섹션 지원 추가, +18 LOC)
```

### Total LOC
- **New**: ~1,200 LOC
- **Modified**: ~18 LOC
- **Tests**: ~350 LOC

---

## 🚀 Next Steps (Execution)

### 1. Random Search 실행
```bash
# Dry-run (Jobs 생성만)
python scripts/tuning/phase28_2_run_random_search.py --dry-run

# 실제 실행 (25 trials × 3 periods = 75 jobs)
python scripts/tuning/phase28_2_run_random_search.py --trials 25

# 특정 period만 (테스트용)
python scripts/tuning/phase28_2_run_random_search.py --trials 10 --period neutral
```

**예상 시간**: 25 trials × 30-60초 = 12-25분 (per period)

### 2. Bayesian Search Skeleton 실행
```bash
# Dry-run
python scripts/tuning/phase28_2_run_bayesian_search.py --dry-run

# 실제 실행 (3-5 trials, neutral period만)
python scripts/tuning/phase28_2_run_bayesian_search.py --trials 5 --period neutral
```

**예상 시간**: 5 trials × 30-60초 = 2-5분

### 3. 결과 집계 및 리포트 생성
```bash
# DB 결과 조회 및 리포트 생성
python scripts/research/phase28_2_summarize_tuning_results.py --top-n 10
```

**Output**:
- Markdown: `docs/PHASE28/PHASE28-2_TUNING_ROUND1_REPORT.md`
- JSON: `reports/tuning/phase28_2/phase28_2_tuning_results.json`

### 4. DB 확인
```sql
-- Run 상태 확인
SELECT run_id, phase, strategy_name, tuning_method, total_jobs, completed_jobs, status
FROM tuning.runs
WHERE phase = 'PHASE28-2'
ORDER BY created_at DESC;

-- 결과 확인
SELECT r.run_id, r.job_id, r.pnl_pct, r.sharpe_ratio, r.trade_count, j.params_json
FROM tuning.results r
JOIN tuning.jobs j ON r.job_id = j.job_id
WHERE r.run_id LIKE 'btc5m_baseline_tuning_round1%'
ORDER BY r.sharpe_ratio DESC
LIMIT 10;
```

---

## ⚠️ Known Limitations

### 1. Small Trial Count
- **Random Search**: 25 trials (전체 공간의 0.0003%)
- **Purpose**: End-to-end 파이프라인 검증, 본격 튜닝은 PHASE28-3

### 2. Worker Isolation
- **Issue**: 동시 실행 시 DB/Redis 충돌 가능
- **Mitigation**: `clean_state=True` + 시간 기반 isolation
- **Recommendation**: Sequential 실행 (현재 구현)

### 3. Config Merging Complexity
- **Issue**: 2가지 config 구조 지원 (PHASE25 vs PHASE27/28-1)
- **Mitigation**: Worker에 양쪽 로직 추가
- **Future**: Config 구조 통일 (PHASE29)

---

## 📊 Expected Outcomes

### After Random Search (25 trials × 3 periods)
- **Total Jobs**: 75개
- **Valid Results**: ~50-60개 (70-80%, min_trades≥10 필터링 후)
- **Top 10 per period**: Period별 최적 파라미터 세트
- **Overall Top 10**: 전체 통합 최적 파라미터 세트
- **Top 3 Candidates**: PHASE28-3/PHASE29에 넘길 추천 파라미터

### Insights Expected
- **RSI threshold**: 42-44 (LONG), 55-56 (SHORT)가 유리할 것으로 예상
- **BB std**: 1.0-1.1 (Main), 1.4-1.5 (Strong)가 균형 좋을 것
- **ADX threshold**: 20-22가 Range/Trend 분류에 적합할 것
- **Period 특성**: bull에서는 trend-following, range에서는 mean-reversion 파라미터가 유리할 것

---

**Status**: ✅ Infrastructure READY → ⏳ PENDING EXECUTION

**Next**: Random Search 실행 → Results Summarizer → PHASE28-2 REPORT 생성
