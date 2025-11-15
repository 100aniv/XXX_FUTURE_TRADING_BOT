# PHASE10: SCALPING 1m Tuning Plan (기존 인프라 재활용)

## 1. 개요
- **목표**: PHASE9-6에서 구현한 1m 스캘핑 V1 전략을 베이시안/Optuna 기반으로 튜닝하여 스캘핑다운 빈도(10~50건/일)와 성능(PF ≥ 1.10, Winrate ≥ 40%)에 근접시키는 것.
- **전제 조건**:
  - 데이터 파이프라인, 전략 로직, 백테스트 엔진은 이미 검증 완료 (PHASE9-7 복구 및 이번 90일 기준선으로 확인).
  - 현재는 "숫자만 돌려보는 단계"로, 전략 구조 자체는 변경하지 않고 CONFIG 파라미터 튜닝에 집중한다.
- **인프라 재사용**:
  - 이미 존재하는 `tuning/` 패키지의 코어 모듈들을 그대로 활용
  - `tuning.tuning_core.TunerCore` (베이시안 최적화 엔진)
  - `tuning.tuning_cli` (CLI 인터페이스)
  - `tuning.config_overlay` (Config 병합 유틸)
  - `tuning.tuning_scheduler` (스케줄러, 필요시 확장)
  - 새로운 튜닝 러너/모듈을 생성하지 않고, 기존 인프라에 scalping 1m 전략을 통합

## 2. 튜닝 대상 파라미터 정의
| 파라미터 | Config 키 | 기본값 | 탐색 범위/분포 | 영향 추정 |
|----------|-----------|--------|----------------|-----------|
| RSI 과매도 임계값 | `rsi_oversold` | 30 | [20, 40], step 1 | 낮을수록 진입 빈도 증가, 너무 낮으면 과도한 바닥에서만 진입해 기회 손실.
| RSI 과매수 임계값 | `rsi_overbought` | 70 | [60, 80], step 1 | 높을수록 숏 신호 감소, 낮추면 하락 전환 포착 가능.
| EMA Fast 기간 | `ema_fast` | 8 | [5, 15], step 1 | 짧을수록 민감, 노이즈 ↑. 길면 모멘텀 식별력이 떨어짐.
| EMA Slow 기간 | `ema_slow` | 21 | [15, 40], step 1 | 길수록 장기 추세 반영, fast와의 차이가 스위칭 빈도 결정.
| 모멘텀 룩백 | `momentum_lookback` | 5 | [2, 10], step 1 | 높을수록 패턴 확인 엄격, 진입 수 감소 가능.
| 거래량 배수 | `volume_mult` | 1.3 | [1.0, 2.5], step 0.1 | 높을수록 강한 볼륨만 허용, 낮추면 빈도 증가.
| RR (Risk/Reward) | `rr` | 1.3 | [1.1, 2.0], step 0.1 | 높이면 기대수익↑ but TP hit 낮음, 낮추면 PF에 영향.
| SL ATR 배수 | `atr_mult_sl` | 0.8 | [0.5, 1.5], step 0.05 | 작을수록 타이트한 SL, DD 감소 vs. 노이즈 청산 위험.
| 최대 보유 시간 | `max_hold_minutes` | 30 | [10, 90], step 5 | 짧게 하면 순수 스캘핑, 길면 스윙화.
| 숏 허용 | `filters.allow_short` | True | [True, False] | 숏 신호 활성화 여부.

> **탐색 전략**: 연속형은 `FloatDistribution`, 정수는 `IntDistribution`. 
> **구현**: `tuning/tuning_core.py`의 `_sample_scalping()` 함수에서 Optuna trial로 샘플링.

## 3. Objective Function 설계 (기존 인프라 활용)
1. **입력**: 
   - `TunerCore._sample_scalping(trial)` → 파라미터 샘플링
   - `config_overlay`로 base.yml + 튜닝 파라미터 병합
   - `run_backtest.py --mode backtest_clean` 실행 (90일)
2. **출력**: 
   - `artifacts/backtest_clean/<run_id>/scorecard.csv`에서 메트릭 추출
   - PF, Winrate, MaxDD, Trades, Sharpe 수집
3. **Composite Score** 예시:
   - `score = PF` (기본) + `0.1 * Winrate` - `penalty_dd` - `penalty_low_trades`
   - `penalty_dd = max(0, (abs(MaxDD) - 5) * 0.05)`
   - `penalty_low_trades = 0.05 * max(0, 100 - Trades)`
4. **검증 흐름**:
   - Optuna trial → `_sample_scalping()` → config overlay → `run_backtest.py` 
   - → `scorecard.csv` → metric 계산 → Optuna trial report

> **주의**: 현재 `TunerCore`는 페이퍼 모드(Postgres trades 테이블) 기준이므로, 백테스트 모드 지원을 위해 `_objective()` 함수 확장 필요. 이는 PHASE10.1에서 구현.

## 4. 튜닝 실행 전략 (기존 TunerCore 활용)
- **Optuna 세팅** (이미 `TunerCore`에 구현됨):
  - `n_trials`: 80~120 (초기 30 trial로 sanity check 후 확대)
  - Sampler: `TPESampler(seed=42)` (Bayesian Optimization, 이미 적용됨)
  - Pruner: `MedianPruner(n_startup_trials=10)` (이미 적용됨)
  - **Storage**: PostgreSQL (`trading_db`) - 기본값
    - 환경변수 `TUNING_DB_URL` 또는 `DATABASE_URL`로 자동 결정
    - Docker: `postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db`
    - 로컬: `postgresql://trading_user:trading_pw_2024@localhost:5432/trading_db`
    - SQLite는 개발용으로만 사용 (권장하지 않음)
- **실행 모드**:
  - CLI: `python -m tuning.tuning_cli --strategy scalping --study scalping_1m_v1 --trials 30`
  - 초기엔 single-process (안정성 우선)
  - 이후 multiprocessing은 Optuna의 병렬 worker 활용 (동일 Postgres Storage 공유)
- **Overfitting 방지**:
  - 데이터 분할: `train=2024-10-01~2024-11-30`, `validation=2024-12-01~2024-12-30`
  - Trial마다 train/validation 각각 백테스트 실행하여 메트릭 수집
  - Objective는 train 점수 + validation penalty 조합
  - **구현 필요**: 현재 `TunerCore`는 단일 윈도우만 평가하므로, train/val 분리 로직 추가 필요

## 5. 아웃풋 설계 (기존 구조 활용)
- **Optuna Study 결과**:
  - PostgreSQL의 Optuna 테이블에 모든 trial 히스토리 저장 (자동)
  - Study name: `scalping_1m_v1` (또는 날짜 포함 `scalping_1m_20251115`)
- **백테스트 artifacts** (각 trial마다):
  - `artifacts/backtest_clean/<run_id>/`
    - `effective_config.yml` (trial 파라미터 적용된 최종 config)
    - `scorecard.csv`, `scorecard.md` (백테스트 결과)
- **Config 발행** (기존 `publish_params_file` 활용):
  - `configs/scalping/active.yml` (최적 파라미터 자동 발행)
  - `configs/scalping/last_published.json` (메타데이터)
  - CLI: `--publish file --publish-dir configs/scalping`
- **Study 분석**:
  - Optuna dashboard 또는 `study.best_params`, `study.best_trial` API로 최적값 확인
  - 커스텀 스크립트로 study 전체 trial을 CSV 추출 가능 (향후 구현)

## 6. 리스크 및 한계
- **1분봉 데이터량**: 90일 = 130k 캔들, trial당 4~5분. → 100 trial ≈ 8~9시간.
- **시세 품질**: Binance futures Kline, 거래 수 적으면 슬리피지/fee 모델 주의.
- **파라미터 수**: 동시에 너무 많은 파라미터를 튜닝하면 탐색 공간이 폭증 → 단계별 (Phase10.1, 10.2)로 나누는 것이 바람직.
- **실행 실패 대응**: config 충돌/timeout 발생 시 retry 로직 필요.
- **리스크 가드 튜닝 제외**: 
  - PHASE10은 **전략 파라미터**(EMA, RSI, 모멘텀, 거래량, RR, ATR, 보유시간)만 튜닝
  - **리스크 가드**(연속 손실 쿨다운 20분, 일일 손실 한도, 포지션 사이징 등)는 별도 Phase에서 튜닝 예정
  - 현재는 `base.yml` / `risk.yml`의 기본 설정 그대로 사용

## 7. PHASE10 TODO (기존 인프라 확장)

### ✅ 완료 (PHASE10.0)
- [x] `tuning/tuning_core.py`의 `_sample_scalping()` 함수를 1m 스캘핑 V1 파라미터로 업데이트
- [x] PHASE10_SCALPING_TUNING_PLAN.md 문서 작성 (기존 인프라 재활용 방향으로)

### 🔧 구현 필요 (PHASE10.1)
- [ ] **백테스트 모드 Objective 구현** (`tuning/tuning_core.py`):
  - 현재 `TunerCore._objective()`는 페이퍼 모드 전용 (Postgres trades 테이블 쿼리)
  - 백테스트 모드용 objective 추가:
    - `run_backtest.py` 실행 (subprocess 또는 engine 직접 호출)
    - `artifacts/backtest_clean/<run_id>/scorecard.csv` 파싱
    - Composite score 계산 (PF + Winrate + DD/Trades penalty)
  - Mode 선택: `TunerCore(..., mode='backtest'|'paper')`
  
- [ ] **Train/Validation 분할 로직**:
  - 단일 trial에서 train (10~11월) / validation (12월) 두 번 백테스트 실행
  - Train score + validation penalty 조합으로 최종 score 산출
  - Overfitting 방지 메커니즘

- [ ] **Config overlay 검증**:
  - `tuning/config_overlay.py`가 scalping 파라미터 병합을 올바르게 처리하는지 확인
  - 필요시 nested dict merge 로직 보강

- [ ] **CLI 확장** (`tuning/tuning_cli.py`):
  - `--mode backtest` 옵션 추가 (현재는 페이퍼 전용)
  - 백테스트 파라미터: `--start-date`, `--end-date`, `--data-path`, `--symbol`, `--timeframe`

- [ ] **Scheduler 통합** (`tuning/tuning_scheduler.py`):
  - scalping 1m 튜닝 Job 정의 (선택사항, 수동 실행도 가능)

### 🚀 향후 개선 (PHASE10.2+)
- [ ] Study 전체 trial 히스토리 CSV/JSON 추출 스크립트
- [ ] Optuna dashboard 연동 (웹 UI로 trial 시각화)
- [ ] 리스크 가드 파라미터 튜닝 (연속 손실 쿨다운, 일일 손실 한도 등)
- [ ] 멀티프로세싱 최적화 (병렬 백테스트 실행)

### 📝 주의사항
- **전략 로직 수정 금지**: `strategies/scalping.py`는 변경하지 않음 (CONFIG 파라미터만 튜닝)
- **엔진/리스크 수정 금지**: `execution/`, `risk/` 모듈은 PHASE10에서 건드리지 않음
- **기존 전략 보존**: `swing_bb`, `daytrade` 등 다른 전략의 튜닝 샘플러는 그대로 유지

---

## 8. 90일 기준선 (Baseline, 튜닝 전)

### 백테스트 결과 (2024-10-01 ~ 2024-12-30, BTCUSDT 1m)
| 지표 | 값 | 목표 | 상태 |
|------|-----|------|------|
| **Trades** | 25건 | ≥ 100건 | ❌ (-75건) |
| **Winrate** | 32.0% | ≥ 40% | ❌ (-8%p) |
| **Profit Factor** | 0.24 | ≥ 1.10 | ❌ (-0.86) |
| **Max Drawdown** | -2.21% | > -20% | ✅ |
| **Sharpe Ratio** | -0.68 | - | - |
| **일별 거래 빈도** | 0.28건/일 | 10~50건/일 | ❌ (스캘핑 기준 미달) |

### 스캘핑다운 평가
**결론: 저빈도 Day/Swing 수준, 스캘핑 정의(10~50건/일)와 거리 -9.7 ~ -49.7건/일**

- **빈도 문제**: 90일간 25건 → 0.28건/일. 진정한 스캘핑(10~50건/일)에 한참 못 미침.
- **신호 조건 과도하게 엄격**: EMA 교차 + RSI 극단 + 모멘텀 패턴 + 거래량 급증을 **모두 AND 조건**으로 결합해 진입 기회가 극히 적음.
- **튜닝 방향**: 
  - RSI 임계값 완화 (oversold 20→30, overbought 70→65 등)
  - 거래량 배수 하향 (1.3→1.0~1.2)
  - 모멘텀 조건 완화 (lookback 줄이기 또는 허용 범위 확대)
  - EMA 기간 조정 (fast 단축, slow 단축으로 크로스 빈도 증가)

### Artifacts 경로
- `artifacts/backtest_clean/20251115_120809_lx9a/scorecard.md`
- `artifacts/backtest_clean/20251115_120809_lx9a/scorecard.csv`
- `artifacts/backtest_clean/20251115_120809_lx9a/effective_config.yml`
