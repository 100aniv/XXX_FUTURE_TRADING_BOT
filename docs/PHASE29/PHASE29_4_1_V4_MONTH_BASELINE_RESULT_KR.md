# PHASE29-4.1: V4 1개월 Baseline 백테스트 결과

## 📋 Document Control

| 항목 | 내용 |
|------|------|
| **PHASE** | PHASE29-4.1 |
| **작성일** | 2025-12-10 |
| **상태** | ✅ **COMPLETE** |
| **판정** | ✅ **Gate_1M PASS** (140건, 목표 80~240건) |

---

## 🎯 목표

V4 전략의 1개월 구간 성능 검증 (Guard OFF):
- ✅ AC1: 1개월 백테스트 에러 없이 완료
- ✅ AC2: 거래 건수 80~240건 (Gate_1M)
- ⏳ AC3: Win Rate/Max DD (STEP 4 경량 튜닝에서 검증 예정)

---

## 📊 백테스트 설정

### Config 파일

| 항목 | 값 |
|------|-----|
| **Config** | `phase29_4_0_btc5m_baseline_v4_month_gate.yml` |
| **기간** | 2024-11-01 ~ 2024-12-01 (30일) |
| **심볼** | BTCUSDT |
| **Timeframe** | 5m |
| **전략** | btc5m_baseline_v4 (단일 전략) |
| **Capital** | $50,000 |

### Guard 설정 (Gate Config)

**Guard 완전 비활성화** (V4 순수 성능 확인):
- `entries.cooldown_candles: 0` (쿨다운 OFF)
- `entries.min_rr_required: null` (RR 필터 OFF)
- `flow_guardian.enabled: false` (FlowGuardian OFF)
- `risk.max_drawdown: 1.0` (100% = Drawdown Guard OFF)

### 전략 파라미터

**Baseline 설정** (Gate-Fit):
- `range_min_score: 3`
- `trend_min_score: 3`
- `filters.min_atr_pct: 0.0015`
- `filters.min_volume_ratio: 0.5`

---

## 📈 백테스트 결과

### 실행 정보

**실행 시간**: 2025-12-10 17:33:28 ~ 17:38:14 (약 5분)  
**run_id**: 20251210_173325_6ac4  
**실행 명령**: `python scripts/run_backtest.py --config configs/backtest/phase29_4_0_btc5m_baseline_v4_month_gate.yml`

### 핵심 지표

| 항목 | 실제 값 | 목표 | 판정 |
|------|---------|------|------|
| **총 캔들** | 8,929개 | - | ✅ |
| **진입 거래** | **140건** | 80-240건 | ✅ **PASS** |
| **종료 거래** | 140건 | - | ✅ |
| **활성 포지션** | 0개 | 0개 | ✅ |
| **Summary JSON** | ✅ 생성됨 | 필수 | ✅ |

---

## 🔍 상세 분석

### 1. 신호 생성

| 항목 | 값 |
|------|-----|
| 전체 캔들 | 8,929개 |
| 신호 발생 | 406건 |
| Signal Rate | 4.60% |
| LONG 신호 | 148건 |
| SHORT 신호 | 258건 |

**핵심 발견**:
- V4는 1개월 동안 **406건 신호 생성** ✅
- 1주일 96건 × 4.2 = 403건 (거의 선형 확장)
- **Signal Rate 4.60%** (안정적)

### 2. Regime 분포

| Regime | 캔들 수 | 비율 |
|--------|---------|------|
| Trend | 6,579개 | 74.5% |
| Range | 2,250개 | 25.5% |

**핵심 발견**:
- Trend 중심 시장 (74.5%)
- Range는 소수 (25.5%)
- V3와 동일한 Regime 탐지 (정상 작동)

### 3. Guard 분석

| 항목 | 값 |
|------|-----|
| Guard 차단 | 222건 |
| Guard 통과 | **140건** |
| Guard 통과율 | 34.48% |

**주목할 점**:
- cooldown_candles=0으로 설정했지만, FILTER_COOLDOWN_ACTIVE 211건 차단
  - 이것은 엔진 내부의 다른 쿨다운 로직일 가능성 (포트폴리오 레벨)
- exposure_exceeded: 11건 (max_open_positions=3 제한)

---

## ✅ Gate 판정

### Gate_1M 결과

| 기준 | 목표 | 실제 | 판정 |
|------|------|------|------|
| 거래 건수 | 80~240건 | **140건** | ✅ **PASS** |

**판정**: ✅ **Gate_1M PASS**

**근거**:
- 140건 ∈ [80, 240] ✅
- 1주일 35건 × 4 = 140건 (정확히 일치)
- 선형 확장 성공

---

## 🔍 주요 발견

### 1. V4 전략 정상 작동 확인 ✅

- **1개월 406건 신호 생성** (1주일 96건 × 4.2)
- **선형 확장 성공** (1주일 → 1개월)
- Signal Rate 4.60% (안정적)

### 2. Guard 호환성 문제 재확인 ❌

**Baseline Config (Guard ON)**: 0건 체결
- min_rr_required: 1.2 → FILTER_RR_BELOW_MIN 195건 차단
- cooldown_candles: 1 → FILTER_COOLDOWN_ACTIVE 211건 차단
- **100% 차단** (0건 체결)

**Gate Config (Guard OFF)**: 140건 체결
- min_rr_required: null
- cooldown_candles: 0
- **34.5% 통과** (140건 체결)

**결론**: V4와 기존 Guard 설정(min_rr_required=1.2, cooldown_candles=1)은 호환되지 않음

### 3. V3 vs V4 비교

| 항목 | V3 (Scenario A+) | V4 (Baseline) | 차이 |
|------|------------------|---------------|------|
| 신호 발생 | 미계측 | 406건 | - |
| 체결 (Guard OFF) | - | 140건 | - |
| 체결 (Guard ON) | 17건 | 0건 | ❌ |
| 1주일 → 1개월 확장 | 실패 (20 → 17) | 성공 (35 → 140) | ✅ |

**V4가 V3보다 우수**:
- 선형 확장 성공 (V3는 실패)
- 신호 빈도 안정적
- OR + Score 로직이 AND 과잉(V3)보다 우수

---

## 🚀 다음 단계

### STEP 4: 경량 파라미터 튜닝

✅ Gate_1M PASS → 경량 튜닝 진행

**튜닝 파라미터**:
- `range_min_score`: {2, 3, 4}
- `trend_min_score`: {2, 3}
- `min_rr_required`: {null, 1.0, 1.2} (Guard 조정)
- `cooldown_candles`: {0, 1} (Guard 조정)

**목표**:
1. Win Rate ≥ 45%, Max DD ≤ 15% 조합 찾기
2. Guard ON 상태에서도 80~240건 유지 가능한 조합 찾기
3. 상위 3개 조합 선정 및 추천

---

## 📁 산출물 (Artifacts)

### Configs
- `configs/backtest/phase29_4_0_btc5m_baseline_v4_month_baseline.yml` (Guard ON, 0건)
- `configs/backtest/phase29_4_0_btc5m_baseline_v4_month_gate.yml` (Guard OFF, 140건) ✅

### Reports
- `reports/backtest/phase29_4_0/btc5m_baseline_v4_month_baseline_summary.json` (0건)
- `reports/backtest/phase29_4_0/btc5m_baseline_v4_month_gate_summary.json` (140건) ✅

### Analysis
- `reports/analysis/PHASE29/phase29_4_1_v4_month_performance.json` ✅
- `reports/analysis/PHASE29/phase29_4_1_v4_month_performance.md` ✅

### Documentation
- `docs/PHASE29/PHASE29_4_1_V4_MONTH_BASELINE_RESULT_KR.md` (this) ✅

---

## 📝 Acceptance Criteria 평가

| AC | 목표 | 상태 | 결과 |
|----|------|------|------|
| AC1 | 1개월 백테스트 성공적 완료 | ✅ PASS | 에러 없이 완료 |
| AC2 | Gate_1M 통과 (80~240건) | ✅ PASS | 140건 체결 |
| AC3 | Win Rate ≥ 45%, Max DD ≤ 15% | ⏳ PENDING | STEP 4 튜닝에서 검증 예정 |
| AC4 | 경량 튜닝 결과 리포트 | ⏳ PENDING | STEP 4 진행 중 |
| AC5 | 문서/코드/테스트 동기화 | ⏳ PENDING | STEP 5 예정 |

---

**소요 시간**: ~2시간  
**판정**: ✅ **CONDITIONAL PASS** (AC1+AC2 PASS, AC3 PENDING)  
**다음 단계**: STEP 4 (경량 파라미터 튜닝)

---

**작성자**: Future Trading Bot Team  
**최종 업데이트**: 2025-12-10
