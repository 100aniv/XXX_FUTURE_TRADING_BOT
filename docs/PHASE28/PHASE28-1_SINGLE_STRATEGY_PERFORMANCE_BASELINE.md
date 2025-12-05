# PHASE28-1: Single Strategy Performance Baseline

**Date**: 2025-12-05  
**Status**: ✅ **COMPLETE** (Infrastructure Ready, Pending Real Data Execution)  
**Strategy**: btc5m_baseline_v1 (PHASE27 Baseline + ADX)

---

## 🎯 목적

**왜 이 작업을 하는가?**

PHASE27까지는 **"전략이 숨을 쉬는가?"**(신호를 생성하는가?)를 확인했습니다.  
PHASE28-1에서는 **"전략의 성격이 무엇인가?"**(어떤 시장에서 어떻게 작동하는가?)를 파악합니다.

**핵심 질문**:
1. 이 전략은 상승장/하락장/횡보장에서 각각 어떻게 작동하는가?
2. 파라미터를 보수적/중립/공격적으로 조정하면 성능이 어떻게 바뀌는가?
3. Trade 부족 문제가 있는가? MDD가 과도한가? Expectancy는?
4. 다음 PHASE28-2 튜닝에서 어디에 집중해야 하는가?

**비목적** (이번 PHASE에서 하지 않는 것):
- ❌ 본격적인 Random/Bayesian 튜닝 (PHASE28-2에서)
- ❌ 성능 극대화 (지금은 "측정"만)
- ❌ 앙상블 통합 (단일 전략 집중)
- ❌ 모니터링/UI 확장 (PHASE30+에서)

---

## 📊 작업 범위 (Scope)

### 1. 백테스트 프리셋 Config 설계 ✅

**파일**: `configs/backtest/phase28_1_btc5m_baseline_presets.yml`

#### 시장 구간 정의 (3개)

| 구간 | 이름 | 기간 | 특징 |
|------|------|------|------|
| **상승장** | Bull Trend | 2024-10-01 ~ 2024-10-31 | 지속적 고점 갱신, Long 신호 많음 |
| **하락장** | Bear Trend | 2024-08-01 ~ 2024-08-31 | 지속적 저점 갱신, Short 신호 많음 |
| **횡보장** | Range Consolidation | 2024-11-15 ~ 2024-12-15 | 저변동성, Mean reversion 신호 |

#### 파라미터 Preset 정의 (3개)

| Preset | 설명 | RSI | BB std | Momentum | 예상 결과 |
|--------|------|-----|--------|----------|-----------|
| **Conservative** | 보수적 진입 | 40/60 | 1.5/2.0 | 강한 조건 | 신호 적음, 승률 높음 |
| **Neutral** | 현재 PHASE27 기준 | 45/55 | 1.0/1.5 | 중립 | 균형 |
| **Aggressive** | 공격적 진입 | 50/50 | 0.8/1.2 | 완화 조건 | 신호 많음, 빈도 우선 |

**공통 설정**:
- 심볼: BTCUSDT
- 타임프레임: 5m
- 초기 자본: $10,000
- 수수료: Maker 0.02%, Taker 0.04%
- 슬리피지: 0.05%
- ADX 사용: 모든 preset에서 활성화 (threshold=25)

---

### 2. Single Strategy Performance Runner 구현 ✅

**파일**: `scripts/research/phase28_1_single_strategy_performance.py`

#### 역할

각 (preset, 기간) 조합에 대해:
1. Config 병합 (common + preset + period)
2. `execution.engine.run_v2(mode='backtest')` 호출 (**단일 엔진 사용**)
3. 결과에서 메트릭 추출
4. JSON 저장 (`reports/phase28_1_btc5m_performance.json`)

#### 핵심 메트릭 (10개)

| Category | Metrics |
|----------|---------|
| **Trade 빈도** | total_trades, long_count, short_count |
| **수익성** | win_rate, gross_pnl, net_pnl |
| **리스크** | max_drawdown (%), sharpe_like_ratio |
| **효율성** | avg_holding_minutes, long_short_ratio |

#### 메트릭 계산

- **Sharpe-like Ratio**: `tuning.tuning_core._sharpe()` 재사용 (일별 수익률 기반)
- **Max Drawdown**: `tuning.tuning_core._mdd_pct_from_trades()` 재사용 (Equity curve 기반)
- **Win Rate**: `winning_trades / total_trades`
- **Net PnL**: `gross_pnl - fees`

**중복 구현 없음**: 기존 `tuning/` 모듈의 함수를 최대한 재사용

---

### 3. Unit Test 작성 ✅

**파일**: `tests/test_phase28_1_single_strategy_performance.py`

**테스트 결과**: ✅ **12/12 PASS** (100%)

#### 테스트 카테고리

1. **Config 로딩** (3 tests)
   - Config 파일 파싱
   - 3개 이상 preset 존재 확인
   - 시장 구간 정의 확인

2. **Config 병합** (1 test)
   - 백테스트용 Config 병합 로직

3. **메트릭 추출** (2 tests)
   - 트레이드 0개일 때
   - 트레이드 있을 때

4. **메트릭 Sanity Check** (3 tests)
   - 타입 확인 (int/float)
   - 범위 확인 (0 ≤ win_rate ≤ 1.0 등)
   - NaN 없음 확인

5. **최소 거래 수 Threshold** (1 test)
   - 스모크 테스트는 최소 10개 거래 필요

6. **SSOT 규칙 준수** (2 tests)
   - Runner가 `run_v2()` 사용하는지 확인
   - `signal_logic()` 직접 호출 금지 확인

---

### 4. 회귀 테스트 ✅

**실행한 테스트**:
- `tests/test_engine_single_entrypoint.py`: **8/8 PASS**
- `tests/test_phase27_8_signal_ssot_guard.py`: **6/6 PASS**

**결과**: ✅ **14/14 PASS** (100%)

**확인 사항**:
- ✅ run_v2 단일 진입점 유지
- ✅ SSOT 원칙 위반 0건
- ✅ 기존 엔진 구조 무손상

---

## 📦 산출물

### 신규 파일 (3개)

1. **`configs/backtest/phase28_1_btc5m_baseline_presets.yml`** (210 LOC)
   - 3개 시장 구간 정의
   - 3개 파라미터 preset 정의
   - 공통 설정 (수수료, 슬리피지, Portfolio, Risk 등)

2. **`scripts/research/phase28_1_single_strategy_performance.py`** (380 LOC)
   - Performance Baseline Runner
   - Config 병합, 엔진 호출, 메트릭 추출
   - `tuning_core` 함수 재사용 (Sharpe, MDD 계산)

3. **`tests/test_phase28_1_single_strategy_performance.py`** (320 LOC)
   - 12개 Unit Test
   - Config/메트릭/SSOT 검증

### 문서 (2개)

1. **`docs/PHASE28/PHASE28-1_SINGLE_STRATEGY_PERFORMANCE_BASELINE.md`** (이 문서)
2. **`PHASE_ROADMAP.md`** (PHASE28 섹션 업데이트 예정)

**Total**: +910 LOC (PHASE28-1 순증)

---

## 🚀 사용법

### 1. 전체 실행 (3 presets × 3 periods = 9 조합)

```bash
python scripts/research/phase28_1_single_strategy_performance.py
```

**출력**:
- `reports/phase28_1_btc5m_performance.json`
- 콘솔에 요약 표 출력

### 2. 스모크 테스트 (짧은 구간, 7일)

```bash
python scripts/research/phase28_1_single_strategy_performance.py --smoke
```

**용도**: 빠른 검증, 전략이 숨을 쉬는지 확인

### 3. 특정 Preset만 실행

```bash
python scripts/research/phase28_1_single_strategy_performance.py --preset neutral
```

**옵션**: `conservative`, `neutral`, `aggressive`

---

## ✅ Acceptance Criteria

| 항목 | 목표 | 실제 | 판정 |
|------|------|------|------|
| **시장 구간** | 3개 이상 | 3개 (상승/하락/횡보) | ✅ PASS |
| **Preset** | 3개 이상 | 3개 (보수/중립/공격) | ✅ PASS |
| **핵심 메트릭** | 최소 10개 | 10개 (trades, win_rate, pnl, mdd, sharpe 등) | ✅ PASS |
| **메트릭 재사용** | 기존 함수 우선 | `tuning_core` 함수 재사용 | ✅ PASS |
| **Unit Test** | 주요 기능 커버 | 12/12 PASS | ✅ PASS |
| **회귀 테스트** | SSOT/Engine 무손상 | 14/14 PASS | ✅ PASS |
| **최소 거래 수** | ≥10 trades (스모크) | Pending (실제 실행 후 확인) | ⏳ PENDING |
| **엔진 단일화** | run_v2만 사용 | ✅ 확인 완료 | ✅ PASS |
| **PHASE_ROADMAP 업데이트** | 28-1 반영 | Pending | ⏳ PENDING |
| **Git 커밋** | 의미 있는 커밋 | Pending | ⏳ PENDING |

**현재 상태**: ✅ **7/10 PASS**, ⏳ **3/10 PENDING**

**PENDING 항목**:
1. **실제 백테스트 실행**: 실제 데이터로 9개 조합 실행 후 최소 거래 수 확인
2. **PHASE_ROADMAP 업데이트**: PHASE28 섹션 정리
3. **Git 커밋**: 최종 커밋

---

## 📋 실제 실행 후 분석할 내용

실제 백테스트 실행 후, 다음 질문에 답변:

### 1. 전략의 성격 파악

**질문**:
- 이 전략은 추세 추종인가, Mean Reversion인가?
- 상승장/하락장/횡보장에서 각각 어떻게 작동하는가?
- Long/Short 비율은?

**예시 답변** (실제 실행 후 작성):
```
- Range 구간: Long/Short 균형 (50:50), Mean reversion 특성
- Trend 구간: 추세 방향 신호 많음 (Bull에서 Long 70%)
- 승률: Range 55%, Trend 45% (빈도 vs 승률 trade-off)
```

### 2. Preset별 성능 차이

**질문**:
- Conservative/Neutral/Aggressive 중 어느 것이 가장 균형잡혔는가?
- Trade 부족 문제가 있는가? (total_trades < 10)
- MDD가 과도한가? (>15%)

**예시 답변** (실제 실행 후 작성):
```
- Conservative: trades 15, win_rate 60%, MDD 8% → 안정적
- Neutral: trades 35, win_rate 52%, MDD 12% → 균형
- Aggressive: trades 75, win_rate 45%, MDD 18% → 과도한 리스크
```

### 3. 다음 PHASE28-2 튜닝 포인트

**질문**:
- 어떤 파라미터를 우선 튜닝해야 하는가?
- Trade 빈도를 늘려야 하는가, 승률을 높여야 하는가?
- Risk 파라미터 조정이 필요한가?

**예시 답변** (실제 실행 후 작성):
```
- Neutral preset 기준으로 튜닝 시작
- RSI threshold를 42~48 범위에서 세밀 조정 (Trade 빈도 증가)
- BB std_main을 0.9~1.1 범위에서 튜닝 (진입 타이밍 개선)
- SL을 1.0%~2.0% 범위에서 튜닝 (MDD 감소)
```

---

## 📊 예상 메트릭 구조 (JSON 출력)

```json
{
  "run_timestamp": "2025-12-05T13:00:00",
  "config_path": "configs/backtest/phase28_1_btc5m_baseline_presets.yml",
  "smoke_test": false,
  "preset_filter": null,
  "results_by_preset_period": {
    "conservative": {
      "bull_trend": {
        "preset_description": "보수적 진입, 신호 빈도 낮음",
        "period_description": "상승 추세 구간",
        "metrics": {
          "total_trades": 15,
          "win_rate": 0.60,
          "gross_pnl": 250.0,
          "net_pnl": 235.0,
          "max_drawdown": 8.5,
          "sharpe_like_ratio": 1.25,
          "avg_holding_minutes": 45.0,
          "long_short_ratio": 2.0,
          "long_count": 10,
          "short_count": 5
        }
      },
      "bear_trend": { ... },
      "range_consolidation": { ... }
    },
    "neutral": { ... },
    "aggressive": { ... }
  }
}
```

---

## 🔒 SSOT/Engine 구조 보존

| 항목 | PHASE27 | PHASE28-1 | 변화 |
|------|---------|-----------|------|
| **엔진 진입점** | run_v2 단일 | run_v2 단일 | ✅ 유지 |
| **신호 경로** | BaseStrategy.compute_signal → Tracker | 동일 | ✅ 유지 |
| **메트릭 계산** | tuning_core 함수 | 동일 재사용 | ✅ 유지 |
| **튜닝 인프라** | tuning/ 구현 완료 | 사용 안 함 (28-2에서) | ✅ 유지 |

**pytest 검증**:
- Unit Test: 12/12 PASS
- 회귀 테스트: 14/14 PASS
- **Total**: 26/26 PASS (100%)

---

## 🎯 다음 단계 (PHASE28-2)

### PHASE28-2: Single Strategy Tuning Round 1

**목적**: PHASE28-1 결과를 바탕으로 실제 튜닝 실행

**계획**:
1. PHASE28-1에서 가장 균형잡힌 preset 선택 (예: Neutral)
2. 핵심 파라미터 3~5개 선정:
   - RSI thresholds (rsi_long, rsi_short)
   - BB std (bb_std_main, bb_std_strong)
   - Exits (sl_pct, tp_levels)
3. Random Search 100회 또는 Bayesian Search 50회
4. 최적 파라미터 세트 도출
5. 최종 검증 (Validation Set)

**사용 인프라**: `tuning/algorithms/random_search.py` 또는 `bayesian_search.py` (PHASE25 완성)

**기간**: 예상 2~3일

---

## 💡 핵심 교훈

### 이번 PHASE에서 얻은 것

1. **전략 성격 파악 프로세스 구축**:
   - 시장 구간별 성능 측정 방법론
   - Preset 기반 파라미터 민감도 분석

2. **기존 인프라 재사용**:
   - `tuning_core` 메트릭 함수 재사용
   - `execution.engine.run_v2()` 단일 엔진 사용
   - SSOT 원칙 유지

3. **측정 우선, 최적화는 나중**:
   - 이번 PHASE는 "측정"만 집중
   - 본격 튜닝은 PHASE28-2에서

### 피한 함정

1. ❌ 새로운 엔진 만들지 않음
2. ❌ 메트릭 계산 중복 구현 안 함
3. ❌ 모니터링/UI 확장하지 않음 (PHASE30+로 미뤄짐)

---

## 🎉 결론

**Status**: ✅ **PHASE28-1 Infrastructure COMPLETE**  
**Tests**: 26/26 PASS (12 Unit + 14 Regression)  
**Ready For**: 실제 백테스트 실행 및 PHASE28-2 튜닝

**핵심 성과**:
- btc5m_baseline_v1 전략의 성능 측정 인프라 완성
- 3 presets × 3 periods = 9 조합 백테스트 준비 완료
- 10개 핵심 메트릭 정의 및 계산 로직 구현
- SSOT/Engine 구조 100% 보존

**다음 작업**:
1. 실제 데이터로 백테스트 실행
2. 결과 분석 후 이 문서 업데이트
3. PHASE28-2 튜닝 계획 수립

---

**Note**: 이 문서는 실제 백테스트 실행 후 "분석 결과" 섹션을 추가하여 완성됩니다.
