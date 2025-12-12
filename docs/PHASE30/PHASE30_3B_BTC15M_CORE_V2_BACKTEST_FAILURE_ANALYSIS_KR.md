# PHASE30-3b: btc15m_core_v2 Backtest Failure Analysis

**Date**: 2025-12-12  
**Status**: ❌ **AC3 CRITICAL FAIL** - 0 Trades  
**Mode**: GPT-5.1 Thinking

---

## Executive Summary

PHASE30-3b에서 btc15m_core_v2 전략의 7D/1M/3M 백테스트를 실행한 결과, **모든 기간에서 0 trades**가 발생했습니다. 이는 AC3 평가 이전에 전략이 기본적인 신호 생성 능력을 상실했음을 의미하며, **CRITICAL FAIL**로 판정됩니다.

### 백테스트 결과

| Period | Candles | Trades | Expected | Status |
|--------|---------|--------|----------|--------|
| **7D Gate** | 768 | 0 | 20-60 | ❌ FAIL |
| **1M Baseline** | 2,976 | 0 | 30-80 | ❌ FAIL |
| **3M Baseline** | 8,832 | 0 | 80-120 | ❌ FAIL |

**총 8,832개 캔들 (3개월) 중 단 한 건의 거래도 발생하지 않음.**

---

## AC3 평가 결과

### AC1: Trade Count
- **기준**: 80-120 trades (3M)
- **실제**: 0 trades
- **판정**: ❌ **CRITICAL FAIL** (-100%)

### AC2: Win Rate
- **기준**: 38-42%
- **실제**: N/A (no trades)
- **판정**: ❌ **FAIL**

### AC3: Profit Factor
- **기준**: ≥1.15
- **실제**: N/A (no trades)
- **판정**: ❌ **FAIL**

### AC4: Max DD
- **기준**: ≤12%
- **실제**: 0% (no trades)
- **판정**: ⚠️ N/A

**최종 판정**: ❌ **AC3 CRITICAL FAIL** (0/4 criteria met)

---

## 근본 원인 분석 (Root Cause Analysis)

### 1. Multi-Timeframe Data 누락

**문제**: 전략이 MTF (1H/4H) 데이터를 요구하지만, 엔진이 제공하지 않음

```python
# strategies/btc15m_core_v2.py:873-874
df_1h = self.config.get('df_1h', None)  # ← None
df_4h = self.config.get('df_4h', None)  # ← None
```

**영향**:
- MTF Regime Detection이 15m 데이터로만 fallback
- Regime confidence 계산이 부정확
- 설계된 0.6×HTF + 0.4×LTF 공식이 작동하지 않음

### 2. Hysteresis V2 과도하게 엄격

**문제**: 5개 연속 캔들이 동일 regime을 유지해야 신호 생성

```python
# _check_hysteresis_v2(): 5 candles consistency required
hysteresis_candles = regime_cfg.get('hysteresis_candles', 5)
```

**영향**:
- BTC 15m 데이터는 regime이 자주 변동
- 5개 연속 조건을 만족하는 경우가 거의 없음
- V1의 3 candles에서 5로 강화된 것이 과도

### 3. Absolute Conditions 과다 차단

**Tier 1 Absolute Blocking Conditions**:
1. Confidence < min_threshold (Trend 0.35, Range 0.40)
2. CHOP regime → 무조건 차단
3. Guard conditions (consecutive loss, DD)
4. Hysteresis not met → 차단

**문제**:
- MTF 데이터 없이는 confidence가 낮게 계산됨
- Hysteresis 미충족으로 대부분 차단
- 4가지 조건 중 1개라도 실패하면 신호 차단

### 4. Config 불일치

**Indicators**:
- Config에 `bollinger_bands` 설정이 누락되어 기본값(20, 2.0) 사용
- BB Lower/Upper 시나리오가 제대로 작동하지 않을 가능성

**Regime Detection**:
- `adx_trend_threshold`, `atr_high_vol_mult` 등 주요 파라미터가 config에 없음
- 하드코딩 기본값(adx 25, atr_mult 1.5) 사용

---

## V1 vs V2 비교

| Aspect | V1 | V2 | Impact |
|--------|----|----|--------|
| **MTF Data** | 15m only | 1H/4H + 15m | ❌ V2는 MTF 없이 작동 불가 |
| **Hysteresis** | 3 candles | 5 candles | ❌ +67% 엄격함 → 신호 차단 |
| **Min Confidence** | 0.25 | 0.35-0.40 | ❌ +40-60% → 신호 차단 |
| **Core Filters** | All block | 2-Tier (Absolute + Penalty) | ⚠️ Tier 1이 너무 엄격 |
| **OR Scenarios** | 8 | 14 | ⚠️ 더 많지만 실행 안 됨 |

**결론**: V2는 V1보다 **구조적으로 더 엄격**하며, MTF 데이터 없이는 작동하지 않도록 설계되었으나, 인프라가 이를 지원하지 않음.

---

## 단위 테스트 vs 실제 백테스트 차이

### 단위 테스트: 15/15 PASS ✅

```
tests/test_btc15m_core_v2.py::test_regime_detection_mtf_trend_up PASSED
tests/test_btc15m_core_v2.py::test_signal_logic_integration PASSED
...
=============== 15 passed, 3 warnings in 1.88s ================
```

**왜 단위 테스트는 통과했는가?**
- 테스트는 **합성 데이터**로 ideal 조건을 시뮬레이션
- MTF 데이터를 명시적으로 제공 (`df_1h`, `df_4h`)
- Hysteresis, confidence 조건을 충족하도록 데이터 구성
- 개별 함수 로직은 정상이지만, **통합 환경에서 데이터/설정 불일치**

### 실제 백테스트: 0 trades ❌

**실패 원인**:
- 엔진이 MTF 데이터를 전달하지 않음
- Config가 전략 요구사항과 불일치
- 실제 시장 데이터는 ideal 조건을 충족하지 못함

---

## 기술적 부채 (Technical Debt)

### 1. MTF 데이터 파이프라인 부재

**현재 상태**:
- 엔진은 단일 timeframe 데이터만 제공 (`df_15m`)
- MTF 전략을 위한 인프라 없음

**필요 작업**:
- `HistoricalFeed`에서 여러 timeframe 동시 로드
- 엔진에서 전략에 `df_1h`, `df_4h` 전달
- Resampling 또는 별도 파일 로드 메커니즘 구현

**예상 작업량**: 2-3 days (PHASE31)

### 2. 전략-엔진 인터페이스 불일치

**문제**:
- `BaseStrategy.compute_signal(df)` 시그니처는 단일 DataFrame만 받음
- V2 전략은 3개 DataFrame (`df_15m`, `df_1h`, `df_4h`) 필요
- `self.config`를 통한 우회 전달은 비표준적

**해결 방안**:
- `BaseStrategy` 인터페이스 확장
- `compute_signal(df_dict: Dict[str, pd.DataFrame])` 형태로 변경
- 또는 전략별 custom 인터페이스 지원

**예상 작업량**: 1-2 days (PHASE31)

### 3. Config Schema 불완전

**문제**:
- 전략이 요구하는 config 파라미터가 문서화되지 않음
- Base config와 strategy config 간 merge 로직 불명확
- 필수 vs 선택 파라미터 구분 없음

**해결 방안**:
- Config validation layer 추가
- 전략별 required config schema 정의
- Runtime에 missing config 경고

---

## 즉시 수정 가능한 임시 해결책

### Option A: V2를 V1 방식으로 Downgrade

**변경사항**:
1. MTF Regime → 15m only (V1 방식)
2. Hysteresis 5 → 3 candles
3. Min confidence 0.35/0.40 → 0.25 (V1 수준)

**장점**: 빠른 수정, 기존 인프라 호환  
**단점**: V2 설계 의도 포기, 성능 개선 불가

### Option B: 인프라 개선 후 V2 재테스트

**변경사항**:
1. MTF 데이터 파이프라인 구축
2. 엔진-전략 인터페이스 확장
3. Config schema 정의 및 validation

**장점**: V2 설계 의도 유지, 장기적 확장성  
**단점**: 시간 소요 (2-4 days), 인프라 리스크

---

## 권장 사항 (Recommendations)

### 단기 (Immediate)

1. **PHASE30-3b → FAIL로 종료**
   - 현재 V2 구현은 실행 불가 상태
   - AC3 평가 불가 (0 trades)

2. **PHASE30-4 취소**
   - Light Tuning은 의미 없음 (신호 생성 자체 불가)

3. **V1으로 Rollback**
   - `btc15m_core_v1`을 baseline으로 유지
   - V2 설계는 보류

### 중기 (Next Phase)

4. **PHASE31: MTF Infrastructure**
   - MTF 데이터 파이프라인 구축
   - 엔진-전략 인터페이스 확장
   - Config validation layer 추가

5. **PHASE32: V2 Light (Simplified)**
   - MTF 제거, 15m only로 단순화
   - Hysteresis 3 candles로 완화
   - 14 OR Scenarios + Dynamic RR만 적용
   - 인프라 부담 없이 V2 핵심 아이디어 테스트

### 장기 (Future)

6. **PHASE33: Full V2 Re-implementation**
   - MTF 인프라 완성 후 재구현
   - 2-Tier + 14 OR + MTF Regime 완전 구현
   - AC3 재평가

---

## 교훈 (Lessons Learned)

### 1. 단위 테스트만으로는 불충분

- **문제**: 개별 함수는 정상이지만, 통합 환경에서 실패
- **교훈**: E2E 백테스트를 unit test와 함께 병행
- **Action**: 향후 전략 구현 시 7D gate를 먼저 실행 (implementation 단계에서)

### 2. 인프라 요구사항 사전 검증

- **문제**: V2 설계 시 MTF 인프라 필요성을 확인했지만, 구현 전에 인프라 준비하지 않음
- **교훈**: 전략 설계 시 인프라 gap을 먼저 해결
- **Action**: PHASE 시작 전 infrastructure readiness check 추가

### 3. Incremental Implementation

- **문제**: V1 → V2로 한 번에 큰 변화 (MTF + Hysteresis + 2-Tier + 14 OR)
- **교훈**: 기능을 하나씩 추가하고 각 단계에서 백테스트
- **Action**: 향후 V2 Light (PHASE32)는 점진적 구현 방식 적용

### 4. Config Schema가 중요

- **문제**: Config 불일치로 전략이 기본값에 의존, 디버깅 어려움
- **교훈**: Config validation + schema 정의 필수
- **Action**: PHASE31에서 config validation layer 구축

---

## 다음 단계 (Next Steps)

### Immediate (Today)

1. ✅ **PHASE30-3b 문서화 완료**
2. **PHASE_ROADMAP 업데이트**
   - PHASE30-3b: FAIL (0 trades, infrastructure gap)
   - PHASE30-4/5: CANCELLED
   - Next: PHASE31 (MTF Infrastructure) 또는 PHASE32 (V2 Light)

3. **Git Commit + Push**
   - 현재까지 작업 (indicator fix, unit tests, configs, failed backtests) 커밋
   - Commit message: "PHASE30-3b: Critical fail - 0 trades due to MTF infrastructure gap"

### Short-term (This Week)

4. **Decision Point**: V2 Light (PHASE32) vs MTF Infra (PHASE31)
   - Option A: PHASE32 먼저 (빠른 실험, 2-3 days)
   - Option B: PHASE31 먼저 (인프라 완성, 3-5 days)

5. **V1 Maintenance**
   - `btc15m_core_v1`을 production baseline으로 유지
   - V1 filter tuning (PHASE30-1d) 재고려

---

## 결론

PHASE30-3b는 **CRITICAL FAIL**로 종료됩니다. btc15m_core_v2 전략은 설계상으로는 V1 대비 우수하지만, 현재 인프라가 MTF 데이터 제공을 지원하지 않아 실행 불가 상태입니다.

**핵심 결론**:
- ✅ 전략 로직 자체는 정상 (unit tests 15/15 PASS)
- ❌ 인프라-전략 간 gap으로 통합 실행 실패 (0 trades)
- ⚠️ V2 설계 의도는 유효하나, PHASE31/32에서 재구현 필요

**권장 경로**: PHASE32 (V2 Light, 15m only) → PHASE31 (MTF Infra) → PHASE33 (Full V2)

---

**Document Status**: ✅ COMPLETE  
**Next Action**: Update PHASE_ROADMAP + Git Commit + GitHub Push
