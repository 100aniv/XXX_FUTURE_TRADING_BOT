# PHASE29-2: BTC 5m Baseline V3 초기 백테스트 검증 리포트

## Executive Summary

**작성 일자**: 2025-12-09  
**Phase**: PHASE29-2 (V3 전략 초기 검증)  
**전략**: `btc5m_baseline_v3`

**핵심 발견**:
- ❌ **CRITICAL_FAIL**: 신호 빈도 극단적으로 낮음
- 1주일 백테스트: **1건** (목표: 20+ 거래)
- 1개월 백테스트: **2건** (목표: 50+ 거래)
- Signal Rate: **0.05%** (V2 대비 99% 감소)

**결론**:
- **PHASE29-3 진입 불가**: 전략 로직 재검토 필수
- V3 진입 조건이 과도하게 엄격하거나, 전략 코드에 버그 존재 가능성
- PHASE29-1 구현 검토 및 디버깅 필요

---

## 📊 Quick Nav

- [실험 설정](#실험-설정)
- [백테스트 결과](#백테스트-결과)
- [진단 분석](#진단-분석)
- [Gate 평가](#gate-평가-phase29-3-진입-조건)
- [권장 조치](#권장-조치)

---

## 🎯 실험 설정

### 목표

PHASE29-0 설계 문서 기반으로 구현된 V3 전략의 초기 성능 검증:
1. **1주일 백테스트** (Drawdown Guard OFF): 신호 빈도 측정 (최소 20+ trades)
2. **1개월 백테스트** (Drawdown Guard ON): 성능 평가 (Win Rate ≥ 45%, Max DD ≤ 15%)

### Config 설정

| 항목 | 1주일 Config | 1개월 Config |
|------|-------------|-------------|
| **파일** | `phase29_2_btc5m_baseline_v3_week.yml` | `phase29_2_btc5m_baseline_v3_month.yml` |
| **기간** | 2024-11-24 ~ 2024-12-01 | 2024-11-01 ~ 2024-12-01 |
| **심볼** | BTCUSDT | BTCUSDT |
| **Timeframe** | 5m | 5m |
| **전략** | btc5m_baseline_v3 (단일 전략) | btc5m_baseline_v3 (단일 전략) |
| **Max Drawdown** | 1.0 (100%, 사실상 OFF) | 0.15 (15%) |
| **Daily Loss Guard** | SOFT (5%) | SOFT (5%) |
| **Base Config** | `phase28_13_btc5m_baseline_v2_profile_h.yml` | 동일 |

### 전략 파라미터 (V3 기본값)

```yaml
# Multi-TP 구조
atr_mult_sl_trend: 2.0
atr_mult_sl_range: 1.5
tp1_mult: 1.2  # 1차 TP (60%)
tp2_mult: 3.0  # 2차 TP (40%)

# Regime 기준
adx_trend_threshold: 25
adx_range_threshold: 20
max_hold_minutes_trend: 120
max_hold_minutes_range: 30

# RSI/BB
rsi_long_percentile_base: 25
rsi_short_percentile_base: 75
bb_mult_main_base: 1.2
bb_mult_strong_base: 2.0

# V3 필터
v3_filters:
  enable_min_atr: true
  min_atr_pct: 0.002  # 0.2%
  enable_volume_filter: true
  min_volume_ratio: 0.8  # MA20 대비 80%
  enable_time_filter: false
```

---

## 📈 백테스트 결과

### 기간별 결과 표

| 항목 | 1주일 | 1개월 | 비고 |
|------|-------|-------|------|
| **Total Calls** | 2,205 | 8,829 | 전략 호출 횟수 |
| **Signal True** | 1 | 4 | 진입 신호 발생 |
| **Signal Rate** | 0.05% | 0.05% | ⚠️ V2 대비 99% 감소 |
| **Orders Submitted** | 1 | 2 | 실제 거래 체결 |
| **Conversion Rate** | 100% | 50% | Signal → Order 전환율 |
| **Guard Blocks** | 0 | 2 | RiskManager 차단 |
| **LONG Signals** | 0 | 1 | - |
| **SHORT Signals** | 1 | 3 | - |

### Regime 분포

| Regime | 1주일 | 1개월 |
|--------|-------|-------|
| **Trend** | 1,620 (73.5%) | 6,579 (74.5%) |
| **Range** | 585 (26.5%) | 2,250 (25.5%) |

**분석**:
- Regime 분류는 정상 작동 (Trend 74%, Range 26%)
- V2와 유사한 Regime 분포 (V2: Trend 95% → V3: 75%)

### 신호 방향별 분포

| 방향 | 1주일 | 1개월 |
|------|-------|-------|
| **LONG** | 0 | 1 (25%) |
| **SHORT** | 1 (100%) | 3 (75%) |

**분석**:
- SHORT 편향 (75%)
- 샘플 수가 너무 적어 통계적 의미 없음

---

## 🔍 진단 분석

### 1. 신호 빈도 비교 (V2 vs V3)

| 메트릭 | V2 (Profile H, 1개월) | V3 (1개월) | 변화율 |
|--------|------------------------|------------|--------|
| **Total Calls** | ~10,000 | 8,829 | -12% |
| **Signal True** | ~600 | 4 | **-99.3%** |
| **Signal Rate** | ~6% | 0.05% | **-99.2%** |
| **Orders Submitted** | ~600 | 2 | **-99.7%** |

**결론**: V3 전략의 신호 발생률이 V2 대비 **99% 감소**

### 2. 가능한 원인 가설

#### 가설 1: V3 진입 조건 과도하게 엄격
- **V2**: RSI **OR** BB (느슨한 조건)
- **V3**: RSI **AND** BB **AND** EMA Pullback **AND** DI+/DI- (엄격한 AND 로직)
- **검증 방법**: 조건별 통과율 로깅, 각 조건 하나씩 비활성화 테스트

#### 가설 2: 필터 계층 과도 차단
- V3 필터:
  - 최소 ATR 0.2%
  - Volume 80% (MA20 대비)
  - 시간대 필터 (OFF)
- **검증 방법**: 필터 개별 ON/OFF 테스트

#### 가설 3: Regime 분류 기준 오류
- ADX Trend/Range 임계값 (25/20)이 실제 시장 특성과 불일치
- **검증 방법**: Regime별 신호 분포 로깅

#### 가설 4: 전략 코드 버그
- `strategies/btc5m_baseline_v3.py`의 로직 오류:
  - 지표 계산 오류 (RSI, BB, EMA)
  - 조건 분기 오류 (Trend/Range 신호 생성)
  - Multi-TP 메타데이터 구조 오류
- **검증 방법**: 단위 테스트 강화, 디버그 로그 추가

#### 가설 5: Config 파라미터 오류
- `strategies.btc5m_baseline_v3` 섹션의 파라미터가 전략 코드에 올바르게 전달되지 않음
- **검증 방법**: Config 파싱 로그 확인

### 3. Guard 차단 분석

1개월 백테스트에서 **2건의 FILTER_RR_BELOW_MIN** 차단 발생:
- 총 4개의 Signal True 중 2개가 RiskManager에서 차단
- Conversion Rate: 50%
- **원인**: Multi-TP 구조에서 계산된 RR이 RiskManager 최소 기준(0.8?) 미달

---

## 🚦 Gate 평가 (PHASE29-3 진입 조건)

| Gate | 목표 | 실제 결과 | Status | 충족 여부 |
|------|------|-----------|--------|-----------|
| **G1: 1주 신호 빈도** | ≥ 10 trades (권장 20+) | 1 trades | ❌ FAIL | ❌ |
| **G2: 1개월 신호 빈도** | ≥ 30 trades (권장 50+) | 2 trades | ❌ FAIL | ❌ |
| **G3: Win Rate** | ≥ 45% | N/A | N/A | N/A |
| **G4: Max Drawdown** | ≤ 15% | N/A | N/A | N/A |
| **G5: Avg RR** | ≥ 1.2 | N/A | N/A | N/A |

**종합 판정**:
- **Status**: ❌ **CRITICAL_FAIL**
- **PHASE29-3 진입 가능**: ❌ **NO**
- **이유**: 신호 빈도 극단적으로 부족 (목표 대비 95% 미달)

---

## 🛠️ 권장 조치

### 즉시 조치 (PHASE29-2A: 긴급 디버깅)

1. **V3 전략 코드 검증** (`strategies/btc5m_baseline_v3.py`)
   - [ ] `signal_logic` 함수 전체 리뷰
   - [ ] 각 진입 조건 통과율 로깅 추가
   - [ ] Trend/Range 모드 분기 검증
   - [ ] Multi-TP 계산 로직 검증

2. **단위 테스트 강화** (`tests/test_btc5m_baseline_v3.py`)
   - [ ] 실제 시장 데이터로 테스트 케이스 추가
   - [ ] Regime별 신호 생성 테스트
   - [ ] 필터 동작 테스트

3. **디버그 백테스트 실행**
   - [ ] 1일 백테스트 + 상세 로그 활성화
   - [ ] 각 캔들마다 진입 조건 체크 결과 로깅
   - [ ] 필터 통과/차단 이유 로깅

### 단기 조치 (PHASE29-2B: 조건 완화 테스트)

1. **AND 로직 완화 테스트**
   - Trend 모드: 최소 3개 조건 → 2개 조건으로 완화
   - Range 모드: 모든 조건 AND → 일부 OR 허용

2. **필터 개별 ON/OFF 테스트**
   - ATR 필터 OFF
   - Volume 필터 OFF
   - 각각 1주일 백테스트 실행하여 신호 빈도 측정

3. **V2 대비 차이 격리**
   - V2 진입 조건과 동일하게 설정 후 백테스트
   - V3 고유 로직(Multi-TP, EMA Pullback)을 하나씩 추가하며 신호 변화 측정

### 중기 조치 (PHASE29-3 진입 전 재설계)

1. **V3 설계 재검토**
   - PHASE29-0 설계 문서의 가정 재검증
   - Trend Pullback 조건의 실현 가능성 재평가
   - Win Rate vs 신호 빈도 트레이드오프 재고

2. **Hybrid 접근 고려**
   - V2 진입 조건 + V3 Multi-TP 구조 혼합
   - 필터 계층을 단계적으로 도입 (ALL ON → 선택적 ON)

---

## 📋 다음 단계

### 우선순위 1: PHASE29-2A (긴급 디버깅)
- **목표**: V3 전략 코드 버그 수정 또는 원인 격리
- **기간**: 1 session
- **산출물**:
  - 디버그 로그 분석 리포트
  - 수정된 V3 전략 코드 (필요 시)

### 우선순위 2: PHASE29-2B (조건 완화 실험)
- **목표**: V3 진입 조건 완화하여 신호 빈도 확보
- **기간**: 1 session
- **산출물**:
  - 조건 완화 버전 백테스트 결과 (신호 20+ 목표)

### 우선순위 3: V3 재설계 또는 PHASE29-3 보류
- V3 설계 근본적 재검토 필요 시 PHASE29-0으로 복귀
- 또는 V2 기반 Multi-TP 구조만 추가하는 V2.1 접근 고려

---

## 📁 산출물

### Config 파일
- `configs/backtest/phase29_2_btc5m_baseline_v3_week.yml`
- `configs/backtest/phase29_2_btc5m_baseline_v3_month.yml`

### 백테스트 결과
- `reports/backtest/phase29_2/btc5m_baseline_v3_week_summary.json`
- `reports/backtest/phase29_2/btc5m_baseline_v3_month_summary.json`

### 분석 리포트
- `scripts/analysis/phase29_2_v3_backtest_diagnostics.py` (분석 스크립트)
- `reports/analysis/PHASE29/phase29_2_v3_backtest_summary.json`
- `reports/analysis/PHASE29/phase29_2_v3_backtest_summary.md`

### 문서
- `docs/PHASE29/PHASE29_2_BTC5M_BASELINE_V3_BACKTEST_KR.md` (본 문서)

---

## 🎯 Acceptance Criteria (재평가)

| 항목 | 목표 | 실제 | Status |
|------|------|------|--------|
| **A1. 1주일 백테스트 실행** | ERROR 0건 | ✅ 0건 | ✅ PASS |
| **A2. 1개월 백테스트 실행** | ERROR 0건 | ✅ 0건 | ✅ PASS |
| **A3. 1주일 신호 빈도** | ≥ 20 trades | ❌ 1 trades | ❌ FAIL |
| **A4. 1개월 신호 빈도** | ≥ 50 trades | ❌ 2 trades | ❌ FAIL |
| **A5. Win Rate** | ≥ 45% | N/A | N/A |
| **A6. Max DD** | ≤ 15% | N/A | N/A |
| **A7. 분석 리포트 작성** | JSON + MD | ✅ 완료 | ✅ PASS |
| **A8. 로드맵 업데이트** | PHASE_ROADMAP.md | ✅ 예정 | - |

**최종 판정**: ❌ **FAIL** (신호 빈도 부족)

---

## 🔚 결론

**PHASE29-2는 기술적으로 완료되었으나, V3 전략은 현재 상태로는 사용 불가**:
- 신호 발생률 0.05% (V2 대비 99% 감소)
- 1개월에 2건의 거래만 발생 (목표 50+)
- PHASE29-3 튜닝 진입 불가

**긴급 조치 필요**:
1. V3 전략 코드 재검토 및 디버깅
2. 진입 조건 완화 또는 설계 재검토
3. V2 기반 점진적 개선 고려

**PHASE29-2A (긴급 디버깅)로 진입**
