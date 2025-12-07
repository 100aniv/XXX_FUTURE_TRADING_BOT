# PHASE28-4: Bayesian Search Round 1 설계 문서

**Phase**: PHASE28-4  
**Status**: DESIGN  
**Date**: 2025-12-07  
**Author**: AI Assistant (Windsurf)

---

## 📋 목적 (Purpose)

PHASE28-3 Random Search Round 1 결과를 기반으로, 상위 Top-K 후보 파라미터를 시드로 사용한 **Bayesian Optimization Round 1**을 수행하여:

1. Random Search에서 발견한 유망 영역을 중심으로 **효율적인 파라미터 탐색**
2. **Sharpe Ratio, Net PnL, MaxDD**를 종합 고려한 최적 파라미터 세트 도출
3. 향후 Local Grid Search (PHASE28-5) 및 실시간 PAPER 검증을 위한 **기준선 확보**

이 Phase는 **Random → Bayesian → Local Grid** 튜닝 파이프라인의 중간 단계로, 엔진/전략 로직 변경 없이 **파라미터 탐색 전략**에만 집중합니다.

---

## 🎯 Scope

### In-Scope

1. **Top-N 후보 추출 로직**
   - PHASE28-3 results.json에서 상위 N개(기본 5~8개) 자동 선정
   - 필터 기준:
     - 최소 거래 수 ≥ 5 (PHASE28-3 기준 유지)
     - Sharpe Ratio, Net PnL, MaxDD 종합 점수 산출
     - 동일/유사 파라미터 중복 제거 (핵심 파라미터 변동폭 기준)

2. **Bayesian Search Round 1 실행**
   - tuning/algorithms/bayesian_search.py 재사용
   - 대상 전략: btc5m_baseline_v1
   - Market Periods: Bull, Range (PHASE28-3과 동일)
   - Trial 수: 각 Period당 25~30개 (총 50~60 trials 권장)
   - 목적 함수: Sharpe_like_ratio 최대화 (거래 수/MaxDD soft constraints)

3. **결과 집계 및 리포트**
   - DB 저장: tuning.runs/jobs/results
   - JSON: reports/tuning/phase28_4/results.json
   - Markdown: docs/PHASE28/PHASE28-4_RESULTS.md (한국어)
   - Random vs Bayesian 비교 분석

### Out-of-Scope

- ❌ Local Grid Search (PHASE28-5로 이관)
- ❌ 멀티 심볼/멀티 전략 앙상블 (PHASE29+)
- ❌ 엔진/SSOT/Guard/Portfolio 인프라 변경
- ❌ Live 연동

---

## 🏗️ 아키텍처

### 데이터 흐름

```
PHASE28-3 Results (JSON)
    ↓
Top-N 후보 추출 (Scoring + Deduplication)
    ↓
Bayesian Search Config 생성
    ↓
tuning/algorithms/bayesian_search.py
    ↓
JobQueue → TuningWorker → run_v2 → BaseStrategy
    ↓
tuning.results (DB) + results.json + RESULTS.md
```

### 주요 컴포넌트

1. **Top-N Selection Utility**
   - 위치: `tuning/utils/result_selection.py` (신규)
   - 기능: JSON 파싱, 필터링, 스코어링, 디듀플리케이션
   - 인터페이스:
     ```python
     def select_top_n_candidates(
         results_json_path: str,
         top_n: int = 5,
         min_trades: int = 5,
         max_drawdown_threshold: float = -0.20
     ) -> List[Dict[str, Any]]
     ```

2. **Bayesian Search Round 1 Script**
   - 위치: `scripts/tuning/phase28_4_run_bayesian_search_round1.py`
   - 역할:
     - 환경 검증 (Python/DB/Redis)
     - ParamSpace 로딩
     - Top-N 후보 추출 → Bayesian Search 초기 seed
     - Period별 Bayesian Search 실행
     - 결과 집계 및 리포트 생성

3. **Config**
   - 위치: `configs/tuning/phase28_4_btc5m_bayesian_search.yml`
   - 주요 필드:
     - periods: [bull, range]
     - max_trials_per_period: 25~30
     - random_seed: 84 (PHASE28-3과 구분)
     - metric: "sharpe_like_ratio"
     - min_trades_for_valid_trial: 10
     - max_allowed_drawdown: -0.15
     - top_n_seed_from_random_search: 5
     - random_search_results_path: "reports/tuning/phase28_3/results.json"

4. **Unit Tests**
   - 위치: `tests/tuning/test_phase28_4_bayesian_search_round1.py`
   - 커버리지:
     - Config 로딩/검증
     - Top-N 후보 추출 (샘플 JSON fixture)
     - Bayesian objective 함수 (거래 수 미달 시 패널티 검증)

---

## 📊 Bayesian Search 설계

### Search 대상

- **ParamSpace**: `configs/tuning/phase28_2_btc5m_baseline_paramspace.yml` (PHASE28-3과 동일)
- **파라미터 수**: 10개
  - RSI: rsi_long_threshold, rsi_short_threshold
  - BB: bb_std_main, bb_std_strong
  - ADX: adx_trend_threshold
  - Momentum: momentum_lookback, momentum_threshold
  - Risk: atr_mult_sl, rr
  - Time: max_hold_minutes

### Period 설정

- **Bull**: 2024-11-01 ~ 2024-11-30
- **Range**: 2024-10-01 ~ 2024-10-31

(PHASE28-3과 동일, 재현성 및 비교 가능성 확보)

### Trial 수

- 각 Period당 **25~30 trials** (총 50~60 trials)
- PHASE28-3 대비 소폭 증가하여 Bayesian Optimization 효과 확인

### 목적 함수

```python
def objective(trial, params):
    # 백테스트 실행 → metrics 추출
    metrics = run_backtest(params)
    
    # Base score
    base_score = metrics['sharpe_like_ratio']
    
    # Soft constraints (패널티)
    penalty = 0.0
    if metrics['total_trades'] < 10:
        penalty += (10 - metrics['total_trades']) * 2.0
    
    if metrics['max_drawdown'] < -0.15:
        penalty += abs(metrics['max_drawdown'] + 0.15) * 50.0
    
    return base_score - penalty
```

### Random Seed

- **Random Search (PHASE28-3)**: seed=42
- **Bayesian Search (PHASE28-4)**: seed=84
- 독립적인 seed로 재현성 보장

---

## ✅ Acceptance Criteria

### AC1: 설계 문서

- [x] `docs/PHASE28/PHASE28-4_BAYESIAN_SEARCH_ROUND1_DESIGN.md` 존재
- [x] Random vs Bayesian 역할 차이, ParamSpace, Period, Metric 정의, Acceptance 기준 명시

### AC2: 코드 구현

- [ ] Top-N 후보 추출 유틸 (`tuning/utils/result_selection.py`)
- [ ] Bayesian Search Round 1 실행 스크립트 (`scripts/tuning/phase28_4_run_bayesian_search_round1.py`)
- [ ] Config (`configs/tuning/phase28_4_btc5m_bayesian_search.yml`)
- [ ] 기존 튜닝 인프라 재사용 (PHASE25-3 bayesian_search.py, JobQueue, Worker)
- [ ] 중복/오버리팩토링 없이 설계대로 구현

### AC3: 테스트

- [ ] Unit Test (`tests/tuning/test_phase28_4_bayesian_search_round1.py`)
- [ ] Config 로딩/검증 테스트
- [ ] Top-N 추출 테스트 (샘플 JSON fixture)
- [ ] Bayesian objective 함수 패널티 테스트
- [ ] 기존 테스트 전부 PASS

### AC4: Smoke Test

- [ ] 각 Period당 3~5 trials 수준 smoke test 성공
- [ ] DB/JSON 출력 정상, 예외 없음

### AC5: Full Execution

- [ ] 각 Period당 25~30 trials 완료
- [ ] 각 Period에서 필터 조건 만족 trial ≥ 3개 존재
- [ ] 거래 수 ≥ 10, Sharpe Ratio 양수 후보 ≥ 1개

### AC6: 결과 산출물

- [ ] `docs/PHASE28/PHASE28-4_RESULTS.md` (한국어 리포트)
- [ ] `reports/tuning/phase28_4/results.json` (Random/Bayesian 비교 가능)
- [ ] Period별 Best Trial Top-3 요약
- [ ] Random vs Bayesian 정성 비교 (평균 거래 수, Sharpe 분포, MaxDD 분포)
- [ ] 다음 단계 제안 (PHASE28-5 Local Grid + PAPER 초안)

### AC7: ROADMAP & Git

- [ ] `PHASE_ROADMAP.md`에 PHASE28-4 섹션 추가
- [ ] 상태: ✅ COMPLETE (작업 완료 후)
- [ ] 의미 있는 커밋 메시지로 git commit 완료

---

## 🔬 Top-N 후보 선정 로직

### 1단계: 필터링

```python
# 1차 필터
candidates = [t for t in trials if t['trade_count'] >= 5]

# 2차 필터 (optional)
candidates = [t for t in candidates if t['max_drawdown'] > -0.20]
```

### 2단계: 스코어링

```python
def calculate_score(trial):
    base_score = trial['sharpe_ratio'] * 10  # Primary
    
    # Bonus
    if trial['pnl'] > 0:
        base_score += trial['pnl'] * 0.1
    
    # Penalty
    if trial['trade_count'] < 10:
        base_score -= (10 - trial['trade_count']) * 0.5
    
    if trial['max_drawdown'] < -0.15:
        base_score -= abs(trial['max_drawdown'] + 0.15) * 20
    
    return base_score
```

### 3단계: 디듀플리케이션

핵심 파라미터 유사도 기준:
- `rsi_long_threshold`, `rsi_short_threshold`
- `bb_std_main`, `bb_std_strong`
- `atr_mult_sl`, `rr`

변동폭 임계:
- int 파라미터: ±2 이내
- float 파라미터: ±0.2 이내

동일 클러스터에서 가장 높은 score만 선택.

### 4단계: Top-N 선정

Score 기준 내림차순 정렬 → 상위 N개 선택 (기본 N=5~8)

---

## 📈 Expected Outcomes

1. **Bayesian Optimization 효과 검증**
   - Random Search 대비 평균 Sharpe Ratio 개선 여부
   - 탐색 효율성 (적은 trial로 더 나은 후보 발견)

2. **Best 파라미터 세트 확보**
   - Period별 상위 3개 후보 → PHASE28-5 Local Grid Search 시드
   - 실시간 PAPER 검증용 후보 (20분/1H/3~12H 구조)

3. **Overfitting 징후 파악**
   - 특정 Period에서만 극단적 성능 → 제외
   - Cross-period 안정성 있는 후보 우선

4. **다음 단계 제안**
   - PHASE28-5: Best k 후보 주변 Local Grid Search
   - PHASE28-6: 검증된 파라미터로 실시간 PAPER (D82 철학 반영)

---

## 🚧 Known Limitations

1. **데이터 범위**
   - Bull/Range 2개 Period만 커버 (Neutral, Bear 제외)
   - 향후 확장 시 추가 Period 검증 필요

2. **전략 단일성**
   - btc5m_baseline_v1만 대상 (다른 timeframe/전략 제외)

3. **Metric 단순화**
   - sharpe_like_ratio 중심 최적화
   - 실전에서는 MaxDD, Consistency, Regime Parity 등 추가 고려 필요

4. **Bayesian Seed 제한**
   - Top-N 후보를 초기 seed로 사용하지만, Optuna API 제약으로 완벽한 warm-start는 아님
   - 향후 개선 가능

---

## 📝 Next Steps (PHASE28-5 초안)

1. **Local Grid Search**
   - PHASE28-4 Best k 후보(k=3~5) 주변 ±1~2 step Grid
   - 미세 튜닝 (예: RSI ±2, BB ±0.1)

2. **실시간 PAPER 검증**
   - D82 철학: 20분 → 1H → 3H → 12H 단계 검증
   - 각 단계에서 Guard/Risk/Portfolio SSOT 준수
   - Live 진입 전 최종 안정성 확인

3. **Multi-Period 확장**
   - Neutral, Bear Period 추가 백테스트
   - Period-weighted 종합 평가

---

**Status**: ✅ DESIGN COMPLETE  
**Next**: Implementation (AC2 코드 구현)
