# PHASE28-5: Local Grid Search v1 설계 문서

**생성일**: 2025-12-07  
**상태**: 🟢 **DESIGN COMPLETE**  
**목적**: Bayesian Search 상위 trials 주변에서 국지 Grid Search를 수행하여 성능 개선 가능성 탐색

---

## 📋 Executive Summary

### 문제 정의

**PHASE28-4R 결론**:
- ✅ **튜닝 인프라**: Production Ready (파라미터 전달 정상)
- ❌ **성능**: 13 trials, 모든 Sharpe ≤ 0
- **Best trial**: Sharpe -19.48, PnL -202.84 (매우 나쁨)

**가능한 원인**:
1. **파라미터 범위 부적절**: Bayesian Search의 초기 탐색 공간이 너무 넓거나 현재 시장에 맞지 않음
2. **시장 조건**: Bull/Range 구간이 Mean Reversion 전략에 불리
3. **전략 로직**: ADX 레짐 분류 또는 BB/RSI 조합의 한계

### PHASE28-5 목표

**Local Grid Search v1 구현 및 검증**:
- Bayesian Round 1 상위 trials를 **seed**로 사용
- 각 seed 주변에서 **작은 범위의 Grid**를 생성 (최대 30-40 jobs)
- **국지 정밀 탐색**으로 "덜 나쁜" 파라미터 조합 발견
- 튜닝 인프라가 **Local Grid Search까지 지원 가능**한지 검증

**명확한 기대치**:
- 당장 양의 Sharpe를 달성하는 것이 목표가 아님
- "Sharpe -19 → -10 수준"으로 개선되면 방향성 확인
- Local Grid Search 알고리즘 구조 확립 (향후 재사용)

---

## 🎯 Local Grid Search 개념

### 입력

1. **Source Run**: `phase28_4_*` (Bayesian Round 1 결과)
2. **Top-K Trials**: Sharpe 기준 상위 k개 (예: 3-5개)
   - 필터 조건: `trades >= 5` (의미 있는 거래 발생한 trials만)
3. **ParamSpace**: 기존 `phase28_2_btc5m_baseline_paramspace.yml`
4. **Grid Config**: 각 파라미터 타입별 변화 범위 설정

### 알고리즘

**단계**:
1. **Seed Selection**: DB에서 source run의 상위 k개 trials 조회
2. **Grid Generation**: 각 seed의 params_json을 중심으로 grid 생성
   - 정수형 (`rsi_long_threshold`, `adx_trend_threshold` 등): center ± 2-3
   - 실수형 (`bb_std_main`, `rr`, `atr_mult_sl` 등): center ± (range * 0.05-0.1)
   - 범주형 (`momentum_lookback`, `max_hold_minutes` 등): center ± 1 인덱스
3. **Deduplication**: 동일한 파라미터 조합 제거
4. **Limit**: 최대 jobs 수 제한 (예: 30-40개)
5. **Execution**: 각 grid point를 기존 튜닝 파이프라인으로 실행

**Grid 생성 규칙**:

```python
# 정수형 파라미터 (예: rsi_long_threshold = 40)
center = 40
delta = 2  # grid_int_delta
grid = [center - delta, center, center + delta]  # [38, 40, 42]
# ParamSpace의 min/max 범위 내로 클리핑

# 실수형 파라미터 (예: bb_std_main = 1.0, range = 0.9-1.2)
center = 1.0
ratio = 0.05  # grid_float_ratio
param_range = 1.2 - 0.9  # 0.3
delta = param_range * ratio  # 0.015
grid = [center - delta, center, center + delta]  # [0.985, 1.0, 1.015]

# 범주형 파라미터 (예: momentum_lookback = 7, candidates = [3, 5, 7, 10])
center_idx = 2  # 7의 인덱스
neighbors = 1  # grid_discrete_neighbors
indices = [center_idx - neighbors, center_idx, center_idx + neighbors]  # [1, 2, 3]
grid = [candidates[i] for i in indices if 0 <= i < len(candidates)]  # [5, 7, 10]
```

**조합 수 제어**:
- 10개 파라미터 × 3 points/param = 3^10 = 59,049 조합 (폭발!)
- **안전장치**:
  1. **Core 파라미터 우선**: `rsi_long_threshold`, `rsi_short_threshold`, `bb_std_main` 등 4-5개만 grid
  2. **나머지 고정**: seed 값 그대로 사용
  3. **Max Jobs 제한**: 생성된 grid가 max_jobs를 초과하면 무작위 샘플링

### 출력

- **tuning.jobs**: job_id, run_id, params_json, status
- **tuning.results**: result_id, job_id, run_id, 메트릭들
- **run_id 형식**: `phase28_5_localgrid_seed{N}_{uuid}`
  - seed1, seed2, ... 별로 run_id 분리 (추적 편의)

---

## 🏗️ 구현 컴포넌트

### 1. LocalGridSearchTuner

**파일**: `tuning/algorithms/local_grid_search.py` (신규)

**클래스**: `LocalGridSearchTuner`

**주요 메서드**:
```python
class LocalGridSearchTuner:
    def __init__(self):
        """LocalGridSearchTuner 초기화"""
        
    def run_from_seeds(
        self,
        run_id_prefix: str,
        seed_trials: List[Dict[str, Any]],
        param_space: ParamSpace,
        grid_config: Dict[str, Any],
        base_config_path: str,
        mode: str = 'backtest',
        strategy_name: str = 'btc5m_baseline_v1',
        target_metric: str = 'sharpe_ratio'
    ) -> List[str]:
        """
        Seed trials 기반 Local Grid Search 실행
        
        Args:
            run_id_prefix: Run ID prefix (예: 'phase28_5_localgrid')
            seed_trials: Seed trial 정보 리스트 (params_json 포함)
            param_space: ParamSpace 인스턴스
            grid_config: Grid 생성 설정
            base_config_path: Base config 경로
            mode: 실행 모드
            strategy_name: 전략 이름
            target_metric: 목표 메트릭
        
        Returns:
            생성된 run_id 리스트
        """
        
    def _build_grid(
        self,
        seed_params: Dict[str, Any],
        param_space: ParamSpace,
        grid_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        단일 seed 주변에 grid 생성
        
        Args:
            seed_params: Seed trial의 파라미터
            param_space: ParamSpace
            grid_config: Grid 생성 설정
        
        Returns:
            파라미터 조합 리스트
        """
        
    def _run_single_trial(
        self,
        run_id: str,
        job_index: int,
        params: Dict[str, Any],
        base_config_path: str,
        mode: str,
        strategy_name: str,
        target_metric: str
    ) -> Dict[str, Any]:
        """
        단일 trial 실행 (BayesianSearchTuner._run_single_trial과 동일 구조)
        """
```

**재사용**:
- `build_tuning_config` (tuning/utils/config_builder.py)
- `run_v2` (execution/engine.py)
- DB 스키마 (tuning.jobs, tuning.results)
- 메트릭 추출 로직 (bayesian_search.py 참고)

### 2. Runner Script

**파일**: `scripts/tuning/phase28_5_run_local_grid_search_round1.py` (신규)

**기능**:
1. **Config 로드**: `configs/tuning/phase28_5_btc5m_local_grid_search.yml`
2. **환경 검증**: Python/DB/Redis 체크
3. **Seed Selection**: DB에서 Bayesian Round 1 상위 trials 조회
4. **LocalGridSearchTuner 실행**
5. **로그**: Seed 목록, grid 조합 수, 진행 상황

### 3. Config

**파일**: `configs/tuning/phase28_5_btc5m_local_grid_search.yml` (신규)

**구조**:
```yaml
run_name: "PHASE28-5: Local Grid Search Round 1"
base_run_id_prefix: "phase28_5_btc5m_localgrid_round1"

# Source: PHASE28-4 Bayesian Round 1 결과
source:
  run_id_prefix: "phase28_4_"
  min_trades: 5
  top_k_trials: 3

# Grid 생성 설정
grid_config:
  # Core 파라미터 (grid 생성 대상)
  core_params:
    - rsi_long_threshold
    - rsi_short_threshold
    - bb_std_main
    - bb_std_strong
    - adx_trend_threshold
  
  # Grid 규칙
  int_delta: 2         # 정수형 ± delta
  float_ratio: 0.05    # 실수형 ± (range * ratio)
  discrete_neighbors: 1 # 범주형 ± neighbors
  max_jobs: 30         # 최대 jobs 수

# Base config
base_config_path: "configs/backtest/phase28_2_btc5m_tuning_base.yml"
param_space_path: "configs/tuning/phase28_2_btc5m_baseline_paramspace.yml"

# 전략 및 실행 설정
strategy:
  name: "btc5m_baseline_v1"
  family: "mean_reversion"

mode: "backtest"
target_metric: "sharpe_ratio"

# Period (Bayesian Round 1과 동일)
periods:
  - name: "bull"
    start: "2024-11-01"
    end: "2024-11-30"
  - name: "range"
    start: "2024-10-01"
    end: "2024-10-31"

# Output
output:
  json:
    path: "reports/tuning/phase28_5/local_grid_round1_results.json"
  markdown:
    path: "docs/PHASE28/PHASE28-5_LOCAL_GRID_SEARCH_ROUND1_RESULTS.md"
```

### 4. Progress/Analysis Scripts

**파일 1**: `scripts/temp_check_phase28_5_progress.py` (신규)
- DB에서 `run_id LIKE 'phase28_5_%'` 조회
- Completed/Running/Failed 통계
- Sharpe/PnL/Trades 분포 표 출력

**파일 2**: `scripts/tuning/phase28_5_summarize_local_grid_round1.py` (신규)
- DB에서 `phase28_5_%` 결과 집계
- Top-N trials 상세 출력
- Bayesian Round 1과 성능 비교
- JSON + Markdown 리포트 생성

---

## 📊 Grid 생성 예시

### Seed Trial (Bayesian Round 1 Best)
```json
{
  "rsi_long_threshold": 47,
  "rsi_short_threshold": 58,
  "bb_std_main": 1.18,
  "bb_std_strong": 1.33,
  "adx_trend_threshold": 24,
  "momentum_lookback": 7,
  "momentum_threshold": 0.00176,
  "atr_mult_sl": 1.64,
  "rr": 1.37,
  "max_hold_minutes": 45
}
```

### Grid 생성 (Core 5개 파라미터만)
```python
grid_config = {
    "core_params": ["rsi_long_threshold", "rsi_short_threshold", "bb_std_main", 
                    "bb_std_strong", "adx_trend_threshold"],
    "int_delta": 2,
    "float_ratio": 0.05
}

# rsi_long_threshold: [45, 47, 49]
# rsi_short_threshold: [56, 58, 60]
# bb_std_main: [1.13, 1.18, 1.23] (range=0.9-1.2 → delta=0.015)
# bb_std_strong: [1.28, 1.33, 1.38] (range=1.3-1.6 → delta=0.015)
# adx_trend_threshold: [22, 24, 26]

# Total: 3^5 = 243 조합 (max_jobs=30이면 무작위 30개 샘플링)
```

---

## 🔬 테스트 전략

### Unit Tests

**파일**: `tests/tuning/test_local_grid_search.py` (신규)

**테스트 케이스**:
1. **test_build_grid_int_param**: 정수형 파라미터 grid 생성 검증
2. **test_build_grid_float_param**: 실수형 파라미터 grid 생성 검증
3. **test_build_grid_categorical_param**: 범주형 파라미터 grid 생성 검증
4. **test_grid_deduplication**: 중복 조합 제거 검증
5. **test_max_jobs_limit**: max_jobs 제한 검증
6. **test_param_space_bounds**: ParamSpace min/max 경계 확인

### Integration Tests

**스모크 실행**:
```bash
# 가상환경 활성화
.\trading_bot_env\Scripts\Activate.ps1

# Docker 확인
docker ps | grep -E "postgres|redis"

# 스모크 실행 (10-20 trials)
python scripts/tuning/phase28_5_run_local_grid_search_round1.py \
    --config configs/tuning/phase28_5_btc5m_local_grid_search_smoke.yml \
    --smoke

# 진행 상황 확인
python scripts/temp_check_phase28_5_progress.py

# 결과 집계
python scripts/tuning/phase28_5_summarize_local_grid_round1.py
```

---

## 📈 성공 기준 (Acceptance Criteria)

### AC1 — LocalGridSearchTuner 구현
- ✅ `tuning/algorithms/local_grid_search.py` 존재
- ✅ `LocalGridSearchTuner` 클래스 구현
- ✅ Seed trials → grid 생성 → 실행 → DB 저장

### AC2 — Runner & Config
- ✅ `scripts/tuning/phase28_5_run_local_grid_search_round1.py` 존재
- ✅ `configs/tuning/phase28_5_btc5m_local_grid_search.yml` 존재
- ✅ 실행 시 `tuning.jobs`/`tuning.results`에 `phase28_5_%` 기록

### AC3 — 리포트
- ✅ `docs/PHASE28/PHASE28-5_LOCAL_GRID_SEARCH_ROUND1_DESIGN.md` (본 문서)
- ✅ `docs/PHASE28/PHASE28-5_LOCAL_GRID_SEARCH_ROUND1_RESULTS.md`
- ✅ `reports/tuning/phase28_5/local_grid_round1_results.json`
- ✅ RESULTS 문서 포함 내용:
  - Total trials, valid trials (trades ≥ 5)
  - Sharpe/PnL/Win% 분포
  - Bayesian Round 1 대비 성능 비교

### AC4 — 테스트
- ✅ `tests/tuning/test_local_grid_search.py` 존재
- ✅ pytest 실행 시 PASS

### AC5 — ROADMAP & Git
- ✅ `PHASE_ROADMAP.md` 업데이트 (28-5: COMPLETE)
- ✅ Git commit (의미 있는 메시지)

---

## 🚀 향후 확장 (PHASE28-6+)

### 옵션 1: Multi-Period Local Grid
- 각 period (Bull/Range) 별 최적 파라미터 탐색
- Period-specific tuning

### 옵션 2: 전략 로직 개선
- ADX 레짐 분류 개선
- BB/RSI 조합 재검토
- 새로운 지표 추가 (예: Volume, Momentum)

### 옵션 3: 멀티 레짐 앙상블
- Bull/Range/Bear 각 regime에 특화된 파라미터 세트
- Dynamic regime switching

### 옵션 4: 실전 검증
- Paper Trading으로 Local Grid 상위 파라미터 검증
- 실제 시장에서 성능 확인

---

## 📝 Notes

### 설계 철학
- **"추가 인프라"가 아니라 "이미 있는 인프라 위의 정밀 탐색 층"**
- 기존 Random/Bayesian Search와 동일한 DB 스키마, Config Builder, Engine 재사용
- 과도한 리팩토링 금지: 최소한의 변경으로 목표 달성

### 제약사항
- **Grid 폭발 방지**: Core 파라미터만 grid, 나머지는 seed 고정
- **Max Jobs 제한**: 30-40개 수준 (실행 시간 고려)
- **현실적 기대치**: 당장 양의 Sharpe 달성보다는 "덜 나쁜" 방향 확인

### 리스크
1. **Grid 조합 폭발**: Core 파라미터만 grid로 제한하여 완화
2. **Seed가 이미 나쁜 경우**: Local 탐색으로도 개선 어려움 → 전략 로직 개선 필요
3. **시장 조건**: Bull/Range 구간이 전략에 불리할 수 있음 → 다양한 period 추가 필요

---

**Author**: Windsurf AI Assistant  
**Phase**: PHASE28-5  
**Date**: 2025-12-07  
**Status**: 🟢 **DESIGN COMPLETE**
