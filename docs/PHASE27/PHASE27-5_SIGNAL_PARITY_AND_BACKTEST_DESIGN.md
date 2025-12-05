# PHASE27-5: Signal Parity & Engine Replay 검증 - 설계 문서

**작성일**: 2025-12-04  
**상태**: 🟦 **IN PROGRESS**  
**목표**: Offline Signal Scan ↔ Engine Replay 신호 정합성 검증 및 Baseline 전략 스펙 정의

---

## Executive Summary

### 핵심 목표

**Primary Goal**: Baseline+ADX 전략의 파이프라인 정합성 검증
- ✅ Offline Signal Scan ↔ Engine Replay 신호 수 일치 검증 (±5~10% 허용)
- ✅ TradeActivityTracker 기반 Drop-off 분석 (Replay 모드)
- ✅ Baseline 전략 스펙 1차 정의 (신호 빈도, RR, 메트릭)

### 배경

**PHASE27-4 결과**:
- **Offline Scan**: 최근 30일 데이터에서 하루 평균 **139.4개 신호** (Grid Search 최적화)
- **Real PAPER 30m**: **0건 신호** (낮은 변동성, 데이터 부족)
- **문제**: Offline과 Real PAPER 간 신호 발생 차이 → 파이프라인 정합성 의문

**PHASE27-5 접근**:
1. **Engine Replay**: 동일 30일 데이터를 Engine으로 Replay하여 신호 수 비교
2. **Signal Parity**: Offline vs Replay 신호 수 차이가 ±5~10% 이내인지 검증
3. **Drop-off 분석**: Replay 기준 Strategy → Ensemble → Guard → Executor 각 단계 카운트
4. **전략 스펙 정의**: Baseline 전략의 역할, 목표 신호 빈도, 메트릭 정의

---

## 1. AS-IS 요약

### 1.1 PHASE27 진행 상황

| Phase | 목표 | 상태 | 핵심 결과 |
|-------|------|------|-----------|
| **27-0** | Drop-off 인프라 구축 | ✅ COMPLETE | TradeActivityTracker, 6 hooks, 21/21 tests |
| **27-1** | Parameter Tuning | ✅ COMPLETE | 파라미터만으로는 0-trade 해결 불가 |
| **27-2** | Strategy Redesign | ✅ COMPLETE | Baseline V1 (Percentile-based, OR logic) |
| **27-3** | ADX Integration | ⚠️ PARTIAL | ADX 구현 완료, 10m PAPER 0 신호 |
| **27-4** | Offline Signal Validation | ⚠️ CONDITIONAL PASS | Offline 139개/일, Real PAPER 0건 |
| **27-5** | Signal Parity & Replay | 🟦 IN PROGRESS | **이번 작업** |

### 1.2 현재 문제 상태

**핵심 의문**:
- Offline Scan에서는 하루 139개 신호가 발생하는데, 왜 Real PAPER 30분에서는 0건인가?
- 전략 로직이 정상인가, 아니면 Engine/Feed/Indicator 파이프라인에 문제가 있는가?

**가설**:
1. **Indicator Warmup**: Offline과 Engine의 warmup 처리 방식 차이
2. **NaN Handling**: `add_indicators()`의 NaN 제거 로직이 Engine에서 다르게 작동
3. **ADX 계산**: Offline과 Engine의 ADX 계산 결과 차이
4. **Config Mismatch**: Offline과 Engine의 파라미터 전달 방식 차이
5. **시장 상황**: Real PAPER 30분이 극도로 낮은 변동성 구간이었을 가능성

**검증 방법**:
- **동일 데이터**를 Offline Scan과 Engine Replay로 각각 실행
- 신호 수를 비교하여 파이프라인 정합성 검증

---

## 2. 목표 및 범위

### 2.1 목표

**Primary Goal**:
1. **Signal Parity 검증**: Offline Scan ↔ Engine Replay 신호 수 차이 ±5~10% 이내
2. **Drop-off 분석**: Replay 기준 Strategy → Ensemble → Guard → Executor 각 단계 카운트
3. **전략 스펙 정의**: Baseline 전략의 역할, 목표 신호 빈도, 메트릭 1차 정의

**Secondary Goal**:
- TradeActivityTracker가 Replay 모드에서도 정상 작동하는지 검증
- Baseline 전략의 실제 수익성 메트릭 수집 (Sharpe, 승률, Profit Factor 등)

### 2.2 범위

**In-Scope**:
- Engine Replay Harness 구현 (30일 전체 데이터)
- Offline vs Replay 신호 수 비교 테스트
- TradeActivityTracker JSON 생성 및 분석
- Baseline 전략 스펙 문서 작성

**Out-of-Scope**:
- 새로운 전략 구현
- 파라미터 추가 튜닝 (PHASE27-4에서 완료)
- Multi-Symbol 확장 (PHASE27-6 이후)
- 실제 수익성 백테스트 (PHASE27-7 이후)

---

## 3. 설계

### 3.1 Engine Replay Harness

#### 3.1.1 구조

**스크립트**: `scripts/research/phase27_5_btc5m_baseline_engine_replay.py`

**입력**:
- **데이터 파일**: `data/BTCUSDT_5m_2024-01-01_2024-12-31.csv` (PHASE27-4와 동일)
- **기간**: 최근 30일 (2024-11-30 ~ 2024-12-30)
- **Config**: `configs/backtest/phase27_5_baseline_replay_30d.yml`

**동작**:
1. CSV 데이터 로드 및 기간 필터링
2. `run_v2(mode='backtest', config=...)` 호출
3. TradeActivityTracker 활성화
4. Engine이 데이터를 순차 처리 (Backtest 모드)
5. 결과 JSON 저장: `docs/PHASE27/phase27_5_btc5m_engine_replay_summary.json`

**재사용 원칙**:
- ✅ 기존 `scripts/run_v2.py` 진입점 재사용
- ✅ 기존 `execution/engine.py` (run_v2) 재사용
- ✅ 기존 Backtest Adapter 재사용 (CSV 기반)
- ❌ 새로운 "미니 엔진" 생성 금지
- ❌ PHASE23-1 단일 엔진 구조 위배 금지

#### 3.1.2 Config 설계

**파일**: `configs/backtest/phase27_5_baseline_replay_30d.yml`

**기반**: `configs/paper/phase27_4_single_symbol_30m_baseline_adx.yml`

**주요 변경**:
```yaml
mode: backtest
env: backtest

# Duration: 30일 전체 (시간 제한 없음)
duration_hours: null  # 무제한 (데이터 끝까지)

# Data Source
data:
  source: csv
  file: data/BTCUSDT_5m_2024-01-01_2024-12-31.csv
  start_date: "2024-11-30"
  end_date: "2024-12-30"

# TradeActivityTracker 활성화
trade_activity_tracker:
  enabled: true
  output_file: docs/PHASE27/phase27_5_btc5m_engine_replay_summary.json

# Strategy: PHASE27-4 Grid Search Top 1 파라미터 그대로
strategies:
  btc5m_baseline_v1:
    rsi_long_threshold: 42
    rsi_short_threshold: 58
    bb_std_main: 1.2
    bb_std_strong: 1.5
    momentum_lookback: 5
    momentum_threshold: 0.001
    use_adx: true
    adx_period: 14
    adx_trend_threshold: 20
    # ... (나머지 파라미터 동일)
```

#### 3.1.3 구현 세부사항

**데이터 로딩**:
```python
# CSV 로드
df = pd.read_csv(config['data']['file'])

# timestamp 컬럼 정규화 (PHASE27-4와 동일)
if 'timestamp' in df.columns and 'time' not in df.columns:
    df = df.rename(columns={'timestamp': 'time'})

# 기간 필터링
start_date = pd.to_datetime(config['data']['start_date'])
end_date = pd.to_datetime(config['data']['end_date'])
df = df[(df['time'] >= start_date) & (df['time'] <= end_date)]
```

**Engine 호출**:
```python
from execution.engine import run_v2

# Config에 데이터 주입
config['_replay_data'] = df  # Engine이 이 데이터를 사용

# Engine 실행
run_v2(mode='backtest', config=config, clean_state=False)
```

**TradeActivityTracker 출력**:
```json
{
  "run_id": "phase27_5_btc5m_engine_replay",
  "timestamp": "2025-12-04T...",
  "mode": "backtest",
  "data_period": {
    "start": "2024-11-30 17:25:00",
    "end": "2024-12-30 15:00:00",
    "days": 30
  },
  "strategy_signals": {
    "total_evaluations": 8562,
    "true": 5741,
    "false": 2821,
    "long": 2798,
    "short": 2943
  },
  "ensemble_decisions": {
    "total": 8562,
    "tier1": 0,
    "tier2": 0,
    "skip": 8562
  },
  "guard_blocks": {
    "total": 0,
    "cooldown": 0,
    "budget": 0,
    "exposure": 0
  },
  "orders_submitted": 0,
  "trades": 0
}
```

### 3.2 Offline vs Replay Signal Parity 테스트

#### 3.2.1 테스트 파일

**파일**: `tests/test_phase27_5_signal_parity.py`

#### 3.2.2 테스트 시나리오

**사전 조건**:
- `docs/PHASE27/phase27_4_btc5m_baseline_signal_scan_summary.json` 존재 (Offline)
- `docs/PHASE27/phase27_5_btc5m_engine_replay_summary.json` 존재 (Replay)

**검증 내용**:

1. **총 신호 수 비교**:
   ```python
   offline_signals = offline_json['scan_result']['signals_true']
   replay_signals = replay_json['strategy_signals']['true']
   
   diff_ratio = abs(offline_signals - replay_signals) / offline_signals
   assert diff_ratio <= 0.10, f"신호 수 차이 {diff_ratio*100:.1f}% (허용: 10%)"
   ```

2. **LONG/SHORT 비율 비교**:
   ```python
   offline_long_ratio = offline_json['scan_result']['long_signals'] / offline_signals
   replay_long_ratio = replay_json['strategy_signals']['long'] / replay_signals
   
   ratio_diff = abs(offline_long_ratio - replay_long_ratio)
   assert ratio_diff <= 0.05, f"LONG 비율 차이 {ratio_diff*100:.1f}% (허용: 5%)"
   ```

3. **날짜별 신호 수 분포** (선택적):
   ```python
   # Offline과 Replay의 일별 신호 수 비교
   # 특정 날짜에 극단적 차이가 있는지 확인
   ```

**실패 시 진단 메시지**:
```python
if diff_ratio > 0.10:
    print("❌ Signal Parity 실패!")
    print("조사 후보:")
    print("  1. Indicator Warmup: Offline과 Engine의 warmup 처리 방식 차이")
    print("  2. NaN Handling: add_indicators()의 NaN 제거 로직 차이")
    print("  3. ADX 계산: Offline과 Engine의 ADX 계산 결과 차이")
    print("  4. Config Mismatch: 파라미터 전달 방식 차이")
    print("  5. Data Loading: CSV 로딩 시 timestamp 변환 차이")
```

### 3.3 TradeActivityTracker Drop-off 분석

#### 3.3.1 검증 항목

**TradeActivityTracker가 Replay 모드에서도 정상 작동하는지 확인**:

1. **Summary JSON 생성**: `phase27_5_btc5m_engine_replay_summary.json` 파일 존재
2. **필수 필드 존재**:
   - `strategy_signals.total_evaluations`
   - `strategy_signals.true/false`
   - `ensemble_decisions.total/tier1/tier2/skip`
   - `guard_blocks.total`
   - `orders_submitted`
   - `trades`

3. **Drop-off 테이블 생성**:
   ```
   Stage                 | Count  | Drop-off Rate
   ----------------------|--------|---------------
   Strategy Evaluations  | 8,562  | -
   Strategy Signals (T)  | 5,741  | 33.0%
   Ensemble Tier1/2      | 0      | 100.0% ❌
   Guard Pass            | 0      | -
   Orders Submitted      | 0      | -
   Trades Executed       | 0      | -
   ```

#### 3.3.2 소규모 수정 (필요 시)

**현재 TradeActivityTracker**:
- `metrics/trade_activity_tracker.py` (285 LOC)
- Engine hooks: 6개 (strategy_signal, ensemble_decision, guard_block, order_submit 등)

**Replay 모드 보장**:
- Config에 `trade_activity_tracker.enabled: true` 설정 시 항상 summary 파일 생성
- 파일 경로는 `docs/PHASE27/` 하위로 고정

**수정 예시** (필요 시):
```python
# metrics/trade_activity_tracker.py

def save_summary(self, output_file: str = None):
    """Summary JSON 저장"""
    if output_file is None:
        # 기본 경로: docs/PHASE27/
        output_file = f"docs/PHASE27/{self.run_id}_activity_summary.json"
    
    # ... (기존 로직)
```

### 3.4 Baseline 전략 스펙 문서화

#### 3.4.1 문서 파일

**파일**: `docs/PHASE27/PHASE27-5_BASELINE_SPEC_AND_METRICS.md`

#### 3.4.2 내용 구성

**1. 전략 역할 정의**:
```markdown
## 1. Baseline 전략 역할

**btc5m_baseline_v1**:
- **목적**: 저변동성/레인지 구간의 mean-reversion 스캘핑
- **심볼**: BTCUSDT (단일 심볼)
- **타임프레임**: 5m
- **레짐**: ADX 기반 Range/Trend 구분
- **진입 로직**: OR 기반 (여러 조건 중 하나만 만족)
- **위험 관리**: ATR 기반 SL, RR 1.5, 최대 보유 60분
```

**2. 1차 정량 스펙**:
```markdown
## 2. 정량 스펙 (PHASE27-4 기준)

### 신호 빈도
- **목표 범위**: 하루 20~60개 (심볼당)
- **현재 실적**: 하루 139.4개 (Grid Search 최적화)
- **판정**: ⚠️ 과다 (추가 완화 필요)

### 위험 관리
- **SL**: ATR × 1.5
- **TP**: RR 1.5 (SL × 1.5)
- **최대 보유**: 60분
- **Leverage**: 기본 3x (최소 1x, 최대 5x)

### 파라미터 (Grid Search Top 1)
- `rsi_long_threshold`: 42
- `rsi_short_threshold`: 58
- `bb_std_main`: 1.2
- `bb_std_strong`: 1.5
- `adx_trend_threshold`: 20
```

**3. 향후 측정 메트릭**:
```markdown
## 3. 백테스트 메트릭 (PHASE27-7 이후)

### 수익성
- **Sharpe Ratio**: 목표 > 1.0
- **Profit Factor**: 목표 > 1.2
- **승률**: 목표 > 40%
- **평균 RR**: 목표 > 1.2

### 안정성
- **Max Drawdown**: 목표 < 15%
- **Win Streak**: 최대 연속 승리
- **Loss Streak**: 최대 연속 손실

### 활동성
- **Trade Frequency**: 하루 20~60개
- **평균 보유 시간**: < 60분
- **Long/Short 균형**: 40~60%
```

---

## 4. Acceptance Criteria

### 4.1 MUST (필수 조건)

| 항목 | 기준 | 검증 방법 |
|------|------|-----------|
| **Engine Replay 실행** | 30일 전체 데이터 정상 처리 | 스크립트 exit code 0 |
| **TradeActivityTracker JSON** | Summary 파일 생성 | 파일 존재 확인 |
| **Signal Parity** | Offline vs Replay 신호 수 차이 ±10% 이내 | 단위 테스트 PASS |
| **LONG/SHORT 균형** | 비율 차이 ±5% 이내 | 단위 테스트 PASS |
| **Drop-off 분석** | 각 단계 카운트 정상 수집 | JSON 필드 검증 |
| **단위 테스트** | 모든 테스트 PASS | pytest 실행 |
| **Baseline 스펙 문서** | 역할/정량 스펙/메트릭 정의 | 문서 작성 완료 |

### 4.2 SHOULD (권장 조건)

| 항목 | 기준 | 검증 방법 |
|------|------|-----------|
| **날짜별 신호 분포** | 특정 날짜 극단적 차이 없음 | 시각화 또는 통계 분석 |
| **Regime별 신호 분포** | Offline vs Replay 일치 | JSON 비교 |
| **실행 시간** | 30일 Replay < 10분 | 시간 측정 |

### 4.3 최종 판정 기준

**PASS**:
- Signal Parity ±10% 이내
- TradeActivityTracker 정상 작동
- 모든 단위 테스트 PASS
- Baseline 스펙 문서 작성 완료

**FAIL**:
- Signal Parity > ±10% (파이프라인 정합성 문제)
- TradeActivityTracker JSON 미생성
- 단위 테스트 실패

---

## 5. 산출물 목록

### 5.1 코드

1. **Engine Replay Harness**: `scripts/research/phase27_5_btc5m_baseline_engine_replay.py`
2. **Config**: `configs/backtest/phase27_5_baseline_replay_30d.yml`
3. **Signal Parity 테스트**: `tests/test_phase27_5_signal_parity.py`
4. **TradeActivityTracker 수정** (필요 시): `metrics/trade_activity_tracker.py`

### 5.2 데이터

1. **Engine Replay Summary**: `docs/PHASE27/phase27_5_btc5m_engine_replay_summary.json`
2. **Drop-off 분석 표**: 보고서에 포함

### 5.3 문서

1. **설계 문서**: `docs/PHASE27/PHASE27-5_SIGNAL_PARITY_AND_BACKTEST_DESIGN.md` (본 문서)
2. **실행 보고서**: `docs/PHASE27/PHASE27-5_SIGNAL_PARITY_AND_DROP_OFF_REPORT.md`
3. **Baseline 스펙**: `docs/PHASE27/PHASE27-5_BASELINE_SPEC_AND_METRICS.md`

### 5.4 Git

1. **Commit**: `[PHASE27-5] Baseline+ADX Signal Parity & Engine Replay Harness`

---

## 6. 구현 계획

### 6.1 작업 순서

1. **설계 문서 작성** ✅ (본 문서)
2. **Config 생성**: `phase27_5_baseline_replay_30d.yml`
3. **Engine Replay Harness 구현**: `phase27_5_btc5m_baseline_engine_replay.py`
4. **Signal Parity 테스트 구현**: `test_phase27_5_signal_parity.py`
5. **TradeActivityTracker 검증** (필요 시 수정)
6. **Baseline 스펙 문서 작성**: `PHASE27-5_BASELINE_SPEC_AND_METRICS.md`
7. **실행 및 검증**:
   - pytest 전체 실행
   - Engine Replay 실행 (30일)
   - Signal Parity 검증
8. **실행 보고서 작성**: `PHASE27-5_SIGNAL_PARITY_AND_DROP_OFF_REPORT.md`
9. **ROADMAP 업데이트**
10. **Git 커밋**

### 6.2 예상 소요 시간

- 설계 문서: 30분 ✅
- Config + Harness 구현: 1시간
- 테스트 구현: 30분
- 실행 및 검증: 30분
- 문서 작성: 1시간
- **총 예상**: 3~4시간

---

## 7. 리스크 및 대응

### 7.1 리스크

| 리스크 | 확률 | 영향 | 대응 방안 |
|--------|------|------|-----------|
| **Signal Parity 실패** (>±10%) | 중 | 높음 | Indicator warmup, NaN 처리, ADX 계산 로직 비교 분석 |
| **Engine Replay 실패** | 낮 | 높음 | 기존 run_v2 + Backtest Adapter 재사용으로 리스크 최소화 |
| **TradeActivityTracker 미작동** | 낮 | 중 | Config 설정 확인, Engine hooks 재검증 |
| **30일 Replay 시간 과다** | 중 | 낮 | 데이터 크기 축소 (7일) 또는 병렬 처리 고려 |

### 7.2 대응 전략

**Signal Parity 실패 시**:
1. Offline과 Replay의 Indicator 계산 결과 비교 (CSV 덤프)
2. ADX 계산 로직 검증 (단위 테스트)
3. NaN 처리 방식 확인 (`add_indicators()` 동작)
4. Config 파라미터 전달 경로 추적

**Engine Replay 실패 시**:
1. 기존 `run_backtest.py` 참고하여 데이터 로딩 방식 확인
2. `run_v2()` 진입점 디버깅
3. Backtest Adapter 로그 확인

---

## 8. 참고 문서

- `docs/PHASE27/PHASE27-0_TRADE_ACTIVITY_DIAGNOSIS_REPORT.md`
- `docs/PHASE27/PHASE27-2_STRATEGY_REDESIGN_REPORT.md`
- `docs/PHASE27/PHASE27-3_ADX_INTEGRATION_REPORT.md`
- `docs/PHASE27/PHASE27-4_BASELINE_SIGNAL_VALIDATION_REPORT.md`
- `docs/PHASE27/PHASE27-4_BASELINE_SIGNAL_VALIDATION_DESIGN.md`
- `docs/PHASE27/phase27_4_btc5m_baseline_signal_scan_summary.json`
- `strategies/btc5m_baseline_v1.py`
- `indicators/core_indicators.py`
- `metrics/trade_activity_tracker.py`
- `execution/engine.py`
- `scripts/run_v2.py`
- `scripts/run_backtest.py`
- `PHASE_ROADMAP.md`

---

**작성일**: 2025-12-04  
**상태**: 🟦 **IN PROGRESS**  
**다음 단계**: Config 생성 및 Engine Replay Harness 구현
