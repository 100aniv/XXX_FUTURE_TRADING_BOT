# PHASE22-0 – Strategy Set Reconstruction & 5-Family Framework

**작성일**: 2025-11-21  
**업데이트**: 2025-11-22 (PHASE22 RESET)  
**상태**: 🔄 **IN PROGRESS** (전략 세트 재정의)  
**목적**: 기존 7개 전략 정리 + 5개 전략 패밀리 기반 새로운 Ensemble 설계

---

## 1. 목적 (Objective) & PHASE22 RESET

### 1.1 현황 분석

**문제점**:
- 기존 7개 전략(scalping 제외) 중 correctness/튜닝/백테스트 전혀 없음
- PHASE22 Extended Validation은 전략 품질 없이 엔진 테스트만 수행하는 상태
- 신호 발생 부재로 인한 테스트 의미 부족

**결정**:
- PHASE22 전체 중단
- PHASE22-0부터 다시 시작 (전략 세트 재정의)
- 5개 전략 패밀리 기반 새로운 Ensemble 설계

### 1.2 PHASE22-0 목표

1. **기존 전략 정리**
   - scalping_v3.py: 보존 (strategies/core/)
   - 나머지 6개: deprecated 폴더로 이동
   
2. **5개 전략 패밀리 정의**
   - Family 1: **High-Frequency Momentum** (scalping_v3)
   - Family 2: **Volatility Breakout** (신규 구현)
   - Family 3: **Mean Reversion** (신규 구현)
   - Family 4: **Trend Following** (신규 구현)
   - Family 5: **Volume-Based** (신규 구현)

3. **Ensemble v2 설계**
   - 5개 패밀리 × 1개 대표 전략 = 5개 전략
   - 각 패밀리별 명확한 역할 정의
   - 상호 보완성 확보

### 1.3 TO-BE 폴더 구조

```
strategies/
├── core/
│   └── scalping_v3.py          ← KEEP (PHASE21 검증 완료)
├── deprecated/
│   ├── breakout_old.py
│   ├── reversion_old.py
│   ├── trend_old.py
│   ├── swing_old.py
│   ├── swing_bb_old.py
│   └── daytrade_old.py
├── research/
│   ├── family_volatility_breakout.py    (TBD)
│   ├── family_mean_reversion.py         (TBD)
│   ├── family_trend_following.py        (TBD)
│   └── family_volume_based.py           (TBD)
├── __init__.py
└── ensemble.py
```

---

---

## 2. 5개 전략 패밀리 정의

### 2.1 Family 1: High-Frequency Momentum

**대표 전략**: scalping_v3.py (PHASE21 검증 완료)

| 항목 | 값 |
|------|-----|
| **Timeframe** | 3m |
| **Signal Type** | Momentum (RSI + Volume) |
| **Frequency** | High (ACTIVE) |
| **Status** | ✅ IMPLEMENTED & KEEP |
| **Trades (PHASE21)** | 92 (3 tests) |
| **PnL (PHASE21)** | -$1,429.90 |
| **Win-rate** | ~36% |
| **Role in Ensemble** | Core HF momentum generator |

**특징**:
- 3분 캔들 기반 고빈도 거래
- RSI + Volume 조합 신호
- 인프라 검증 완료 (PHASE21-1C)
- 유일하게 충분한 샘플 데이터 보유

---

### 2.2 Family 2: Volatility Breakout

**대표 전략**: TBD (신규 구현)

| 항목 | 값 |
|------|-----|
| **Timeframe** | 15m |
| **Signal Type** | Breakout (ATR + Support/Resistance) |
| **Frequency** | Low-Frequency |
| **Status** | 🔄 RESEARCH |
| **Reference** | strategies/deprecated/breakout_old.py |
| **Role in Ensemble** | Volatility regime 포착 |

**설계 계획**:
- ATR 기반 동적 지지/저항선
- Breakout 확인 후 진입
- 15분 타임프레임 (중기 변동성)
- PHASE22-1에서 구현 및 검증

---

### 2.3 Family 3: Mean Reversion

**대표 전략**: TBD (신규 구현)

| 항목 | 값 |
|------|-----|
| **Timeframe** | 5m |
| **Signal Type** | Mean Reversion (Bollinger Bands + RSI) |
| **Frequency** | Low-Frequency |
| **Status** | 🔄 RESEARCH |
| **Reference** | strategies/deprecated/reversion_old.py |
| **Role in Ensemble** | Mean-reversion regime 포착 |

**설계 계획**:
- Bollinger Bands 기반 평균 회귀
- RSI 극단값에서 반전 신호
- 5분 타임프레임
- PHASE22-1에서 구현 및 검증

---

### 2.4 Family 4: Trend Following

**대표 전략**: TBD (신규 구현)

| 항목 | 값 |
|------|-----|
| **Timeframe** | 1h |
| **Signal Type** | Trend (Moving Average + MACD) |
| **Frequency** | Low-Frequency |
| **Status** | 🔄 RESEARCH |
| **Reference** | strategies/deprecated/trend_old.py |
| **Role in Ensemble** | Long-term trend filter |

**설계 계획**:
- 이중 이동평균 (SMA 50/200)
- MACD 추세 확인
- 1시간 타임프레임 (장기 추세)
- PHASE22-1에서 구현 및 검증

---

### 2.5 Family 5: Volume-Based

**대표 전략**: TBD (신규 구현)

| 항목 | 값 |
|------|-----|
| **Timeframe** | 5m |
| **Signal Type** | Volume Delta (OBV + CVD) |
| **Frequency** | Low-Frequency |
| **Status** | 🔄 RESEARCH |
| **Reference** | strategies/deprecated/swing_bb_old.py |
| **Role in Ensemble** | Volume regime 포착 |

**설계 계획**:
- On-Balance Volume (OBV) 기반
- Cumulative Volume Delta (CVD) 추적
- 5분 타임프레임
- PHASE22-1에서 구현 및 검증

---

## 3. Ensemble v2 최종 구성 (5개 전략)

| Family | Strategy | Timeframe | Status | Role |
|--------|----------|-----------|--------|------|
| 1. HF Momentum | scalping_v3 | 3m | ✅ IMPLEMENTED | Core momentum generator |
| 2. Volatility Breakout | breakout_v2 | 15m | 🔄 RESEARCH | Volatility regime capture |
| 3. Mean Reversion | reversion_v2 | 5m | 🔄 RESEARCH | Mean-reversion regime |
| 4. Trend Following | trend_v2 | 1h | 🔄 RESEARCH | Long-term trend filter |
| 5. Volume-Based | volume_v2 | 5m | 🔄 RESEARCH | Volume regime capture |

**특징**:
- 5개 패밀리 × 1개 대표 전략 = 5개 전략
- 각 패밀리별 명확한 역할 정의
- 상호 보완성 확보 (Timeframe + Signal Type 다양화)
- scalping_v3만 IMPLEMENTED, 나머지는 PHASE22-1에서 구현

---

## 4. PHASE22-0 Acceptance Criteria

### 4.1 완료 항목

- [x] **폴더 구조 재정렬**
  - `strategies/core/scalping_v3.py` ← KEEP
  - `strategies/deprecated/` ← 6개 전략 보존
  - `strategies/research/` ← 신규 구현 예정

- [x] **5개 전략 패밀리 정의**
  - Family 1: High-Frequency Momentum (scalping_v3)
  - Family 2: Volatility Breakout (신규)
  - Family 3: Mean Reversion (신규)
  - Family 4: Trend Following (신규)
  - Family 5: Volume-Based (신규)

- [x] **Ensemble v2 최종 구성**
  - 5개 전략 (1개 IMPLEMENTED + 4개 RESEARCH)
  - 각 패밀리별 명확한 역할 정의
  - 상호 보완성 확보

- [x] **문서 업데이트**
  - PHASE22-0_STRATEGY_POOL.md 완료
  - PHASE_ROADMAP.md 업데이트 예정

### 4.2 다음 단계 (PHASE22-1)

**PHASE22-1: Strategy Implementation & Validation**
- Family 2~5 전략 구현
- 각 전략별 백테스트 및 파라미터 튜닝
- 12시간 Paper 테스트
- Ensemble v2 최종 검증

---

## 5. 참조

- **PHASE21 완료 리포트**: `docs/PHASE21/PHASE21-1C_ACTUAL_EXECUTION_REPORT.md`
- **기존 전략 코드**: `strategies/deprecated/`
- **Core 전략**: `strategies/core/scalping_v3.py`
- **PHASE_ROADMAP**: `PHASE_ROADMAP.md`

---

**Report Generated**: 2025-11-22  
**Status**: 🔄 **IN PROGRESS** (PHASE22-0 Strategy Set Reconstruction)
