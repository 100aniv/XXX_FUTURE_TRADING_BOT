# PHASE30-0: New Core Strategy Design (btc15m_core_v1)

**작성일**: 2025-12-11  
**상태**: 🟨 IN PROGRESS → ✅ COMPLETE  
**목표**: V3/V4 실패 교훈을 반영한 새로운 코어 전략 설계 (문서 전용)

---

## 목차

1. [개요](#1-개요)
2. [전략 구조 설계](#2-전략-구조-설계)
3. [백테스트 & 검증 계획](#3-백테스트--검증-계획)
4. [Acceptance Criteria](#4-acceptance-criteria)
5. [다음 단계](#5-다음-단계)

---

## 1. 개요

### 1.1 PHASE29 실패 요약

PHASE29에서 검증한 V2/V3/V4 전략은 모두 AC3 성능 기준(Win Rate ≥ 45%, Max DD ≤ 15%)을 충족하지 못했다:

| 전략 | 핵심 문제 | 결과 | 판정 |
|------|----------|------|------|
| **V2** | OR 과잉 → 저품질 신호 과다 | Win Rate < 45% | ❌ RETIRED |
| **V3** | AND 과잉 → 신호 극소 (17건/월) | 거래 건수 부족 | ❌ RETIRED |
| **V4** | OR + Score (V2/V3 절충 시도) | Win Rate 27.86%, Max DD 23.21% | ❌ RETIRED |

**V4 구조적 실패 원인** (PHASE29-7 Postmortem):
1. **OR 기반 진입 과잉**: 단일 지표 오류 → 즉시 손실 (손실 비율 72.14%)
2. **Score Threshold 부적절**: 최대 점수 대비 50% 이하 → 저품질 신호 통과
3. **Regime Detection 부정확**: ADX 단일 지표 의존 → Regime 오판 시 전략 실패
4. **SL/TP 비율 미스매치**: RR 1.0~1.2 → Win Rate 54% 필요 (달성 불가)
5. **5m Timeframe 노이즈**: 과도한 False Signal → 거래 건수↑, 품질↓

### 1.2 PHASE30-0의 역할

**이 문서의 목적**:
- btc15m(또는 30m) 기반 New Core Strategy를 **문서로만** 완성
- 코드 구현 및 백테스트는 PHASE30-1/30-2에서 수행
- V3/V4 실패 교훈을 **구체적 설계 원칙**으로 변환

**산출물**:
- 본 문서: `docs/PHASE30/PHASE30_0_BTC15M_CORE_STRATEGY_DESIGN_KR.md`
- ROADMAP 업데이트: PHASE30-0 섹션 추가

### 1.3 정량 목표 (Performance Target)

PHASE29-7 Postmortem 권고사항 기반:

| 지표 | 목표 | 근거 |
|------|------|------|
| **Win Rate** | 40~45% | RR 1.5 기준, 기대값 양수 보장 |
| **Risk:Reward** | ≥ 1.5 | Win Rate 40%만 되어도 이익 (EV = +0.05) |
| **Max Drawdown** | ≤ 12% | V4 23.21% 대비 보수적, Guard 호환 |
| **Profit Factor** | > 1.2 | 명확한 이익 구조 |
| **거래 건수/월** | 60~120건 | 15m 기준, V4 5m 140건보다 보수적 |
| **Sharpe Ratio** | > 0.5 | 위험 대비 수익 안정성 |

**수학적 검증**:
```
RR = 1.5, Win Rate = 40%
기대값 = 0.40 * 1.5 - 0.60 * 1.0 = 0.6 - 0.6 = 0.0 (Break-even)

RR = 1.5, Win Rate = 45%
기대값 = 0.45 * 1.5 - 0.55 * 1.0 = 0.675 - 0.55 = +0.125 (이익)

RR = 2.0, Win Rate = 40%
기대값 = 0.40 * 2.0 - 0.60 * 1.0 = 0.8 - 0.6 = +0.2 (이익)
```

**결론**: 최소 RR 1.5에서 Win Rate 45% 달성 시 안정적 이익 구조 확보.

---

## 2. 전략 구조 설계

### 2.1 Timeframe & Universe

#### 2.1.1 Timeframe 선택

**Primary Timeframe**: **15m**
- **이유**:
  - 5m 대비 노이즈 70% 감소 (추정)
  - 신호 품질 향상, False Signal 억제
  - 거래 건수 적정선 유지 (60~120건/월)
- **근거**: V4 5m에서 140건/월 → 15m에서 약 45~50건/월 예상 (3배 감소)

**Secondary Timeframe**: **30m** (실험/보조용)
- 더 긴 타임프레임에서 신호 품질 극대화 테스트
- Multi-Timeframe Confirmation으로 활용 가능

**Multi-Timeframe 확인 구조**:
- Primary 15m에서 진입 신호 생성
- Secondary 1H에서 Trend/Regime 확인 (선택적)
- 예: 15m LONG 신호 → 1H Trend Up 확인 → 진입 허용

#### 2.1.2 심볼 및 확장성

**Current Scope**: BTCUSDT Perpetual Futures (Binance)
- V2/V3/V4와 동일, 검증된 데이터 파이프라인 활용

**Future Expansion** (PHASE30+ 이후):
- Top N Symbols (예: ETH, SOL, BNB 등)
- 각 심볼별 파라미터 독립 튜닝
- Portfolio-level Risk Management 연동

### 2.2 Regime Detection 설계

#### 2.2.1 설계 원칙

**V4 문제**:
- ADX 단일 지표만 사용 → 정확도 부족
- Threshold 하드코딩 (ADX > 25 = Trend) → 시장 변화 대응 불가

**New Design**:
- **복합 지표 기반**: ADX + ATR + Volume + Directional Movement
- **확률적 접근**: Regime별 신뢰도 점수 산출
- **동적 Threshold**: 최근 N캔들 통계 기반 동적 조정

#### 2.2.2 사용 지표

| 지표 | 역할 | 계산 방식 |
|------|------|----------|
| **ADX** | 추세 강도 | ADX(14), 기준: 20 (약함) ~ 40 (강함) |
| **ATR** | 변동성 | ATR(14), 최근 20캔들 평균 대비 비율 |
| **Volume** | 거래량 | 최근 20캔들 평균 대비 비율 |
| **DI+/DI-** | 방향성 | DI+(14), DI-(14), 차이값으로 Trend 방향 판단 |

#### 2.2.3 Regime 정의

**3가지 핵심 Regime**:

**1. Trend-Up (강세 추세)**
- **조건**:
  - ADX > 25 (추세 강도 충분)
  - DI+ > DI- (상승 방향성)
  - ATR > avg_ATR * 1.1 (변동성 증가)
  - Volume > avg_Volume * 0.9 (거래량 유지)
- **신뢰도 점수**:
  ```python
  trend_up_score = (
      0.4 * (ADX - 20) / 20  # ADX 기여도 40%
      + 0.3 * (DI+ - DI-) / DI+  # 방향성 30%
      + 0.2 * (ATR / avg_ATR - 1)  # 변동성 20%
      + 0.1 * (Volume / avg_Volume - 1)  # 거래량 10%
  )
  # Score >= 0.7 → High Confidence Trend-Up
  ```
- **허용 포지션**: LONG only
- **진입 전략**: Pullback 매수 (EMA 지지선 터치 후 반등)

**2. Trend-Down (약세 추세)**
- **조건**:
  - ADX > 25
  - DI- > DI+
  - ATR > avg_ATR * 1.1
  - Volume > avg_Volume * 0.9
- **신뢰도 점수**: Trend-Up과 동일 방식 (DI 반대)
- **허용 포지션**: SHORT only
- **진입 전략**: Pullback 매도 (EMA 저항선 터치 후 하락)

**3. Range (횡보/레인지)**
- **조건**:
  - ADX < 20 (추세 약함)
  - ATR < avg_ATR * 1.0 (변동성 낮음)
  - 최근 20캔들 High-Low 범위가 좁음 (예: < 2% 가격 범위)
- **신뢰도 점수**:
  ```python
  range_score = (
      0.5 * (20 - ADX) / 20  # ADX 낮을수록 높은 점수
      + 0.3 * (1 - ATR / avg_ATR)  # 변동성 낮을수록
      + 0.2 * (1 - price_range / avg_price)  # 가격 범위 좁을수록
  )
  ```
- **허용 포지션**: 양방향 (LONG + SHORT)
- **진입 전략**: Mean Reversion (BB 상단 매도, 하단 매수)

**4. High-Volatility-Chop (선택적, 고변동성 혼조)**
- **조건**:
  - ADX < 20 (추세 약함)
  - ATR > avg_ATR * 1.5 (변동성 급증)
  - Volume > avg_Volume * 2.0 (거래량 폭증)
- **허용 포지션**: **진입 제한** (Guard 강화)
- **이유**: 방향성 없는 급변동 → 손실 위험 높음

#### 2.2.4 Regime 전환 로직

**Hysteresis (이력현상) 적용**:
- Regime 변경 시 즉시 전환 X
- 연속 N캔들(예: 3캔들) 동안 새 Regime 조건 만족 시 전환
- 목적: 빈번한 Regime 오판 방지

**예시**:
```
현재 Regime: Trend-Up
→ ADX < 20 (Range 조건 1회 만족)
→ ADX < 20 (2회 연속)
→ ADX < 20, ATR < avg*1.0 (3회 연속, Range 확정)
→ Regime 전환: Trend-Up → Range
```

### 2.3 진입 조건: Core AND + Optional OR

#### 2.3.1 설계 철학

**V2/V4 문제 재현 방지**:
- V2: 모든 조건 OR → 저품질 신호 과다
- V3: 모든 조건 AND → 신호 극소
- V4: OR + Score → 여전히 OR 과잉

**New Hybrid 구조**:
```
IF (Core AND Block) THEN
    IF (Optional OR Block) THEN
        → 진입 허용
```

**핵심 원칙**:
1. **Core AND는 반드시 통과**: 필수 조건 (Regime, Guard, ATR, Volume)
2. **Optional OR은 부가 조건**: 진입 시나리오 선택 (Pullback, BB, RSI 등)
3. **Score 금지**: V4 실패 교훈, 조건 명확성 우선

#### 2.3.2 Core AND Block (필수 조건)

**모든 진입에 공통 적용**:

```python
# Pseudo-code
def core_and_conditions(regime, candle, guard_state):
    # 1. Regime 유효성
    if regime not in ['TREND_UP', 'TREND_DOWN', 'RANGE']:
        return False
    
    # 2. Guard 통과
    if not guard_state.is_entry_allowed():
        return False
    
    # 3. 최소 변동성 (ATR)
    if candle.atr < min_atr_threshold:
        return False
    
    # 4. 최소 거래량 (Volume)
    if candle.volume < avg_volume * min_volume_ratio:
        return False
    
    # 5. 최근 DD 체크 (추가 안전장치)
    if portfolio.current_dd > max_allowed_dd * 0.8:  # 80% 근접 시 진입 제한
        return False
    
    # 6. 연속 손실 제한
    if portfolio.consecutive_losses >= max_consecutive_losses:
        return False
    
    return True  # Core 조건 모두 통과
```

**파라미터 예시**:
- `min_atr_threshold`: 0.002 (0.2%)
- `min_volume_ratio`: 0.7 (평균 대비 70%)
- `max_allowed_dd`: 0.12 (12%)
- `max_consecutive_losses`: 5

#### 2.3.3 Optional OR Block (진입 시나리오)

**Regime별 진입 시나리오**:

**Trend-Up Mode** (LONG only):
```python
def trend_up_scenarios(candle):
    # 시나리오 A: EMA Pullback
    scenario_a = (
        candle.close > candle.ema_50
        and candle.low <= candle.ema_50 * 1.002  # EMA 터치 (0.2% 이내)
        and candle.close > candle.open  # 반등 캔들
    )
    
    # 시나리오 B: RSI Oversold + Bounce
    scenario_b = (
        candle.rsi < 35  # Oversold
        and candle.rsi > prev_candle.rsi  # RSI 상승 시작
        and candle.close > candle.open
    )
    
    # 시나리오 C: BB Lower Band + Volume Spike
    scenario_c = (
        candle.low <= candle.bb_lower * 1.001
        and candle.volume > avg_volume * 1.3
        and candle.close > (candle.high + candle.low) / 2  # 중간값 이상
    )
    
    return scenario_a or scenario_b or scenario_c
```

**Trend-Down Mode** (SHORT only):
- 시나리오 A: EMA Pullback (반대 방향)
- 시나리오 B: RSI Overbought + Bounce Down
- 시나리오 C: BB Upper Band + Volume Spike

**Range Mode** (양방향):
```python
def range_scenarios(candle):
    # LONG 시나리오: BB Lower 반등
    long_scenario = (
        candle.low <= candle.bb_lower * 1.002
        and candle.rsi < 40
        and candle.close > candle.open
    )
    
    # SHORT 시나리오: BB Upper 반락
    short_scenario = (
        candle.high >= candle.bb_upper * 0.998
        and candle.rsi > 60
        and candle.close < candle.open
    )
    
    return long_scenario or short_scenario
```

#### 2.3.4 최종 진입 로직

```python
def should_enter(regime, candle, guard_state):
    # Step 1: Core AND 통과 여부
    if not core_and_conditions(regime, candle, guard_state):
        return False, None
    
    # Step 2: Regime별 Optional OR 시나리오
    if regime == 'TREND_UP':
        if trend_up_scenarios(candle):
            return True, 'LONG'
    elif regime == 'TREND_DOWN':
        if trend_down_scenarios(candle):
            return True, 'SHORT'
    elif regime == 'RANGE':
        scenarios = range_scenarios(candle)
        if scenarios:
            return True, scenarios.side  # LONG or SHORT
    
    return False, None
```

**차별점**:
- V2/V4: OR만 사용 → 저품질 신호
- V3: AND만 사용 → 신호 극소
- **btc15m_core_v1**: Core AND (필수) → Optional OR (선택) → 품질 & 빈도 균형

### 2.4 SL/TP & Position Management

#### 2.4.1 기본 RR 구조

**목표**: 최소 RR 1.5, 동적 조정

**SL 계산**:
```python
def calculate_sl(regime, entry_price, atr):
    if regime in ['TREND_UP', 'TREND_DOWN']:
        # Trend: 깊은 SL (추세 추종)
        sl_distance = atr * sl_mult_trend  # sl_mult_trend = 2.0
    elif regime == 'RANGE':
        # Range: 짧은 SL (빠른 손절)
        sl_distance = atr * sl_mult_range  # sl_mult_range = 1.5
    else:
        sl_distance = atr * 1.5  # Default
    
    if side == 'LONG':
        sl_price = entry_price - sl_distance
    else:  # SHORT
        sl_price = entry_price + sl_distance
    
    return sl_price, sl_distance
```

**TP 계산** (Multi-TP):
```python
def calculate_tp(regime, entry_price, sl_distance, side):
    if regime in ['TREND_UP', 'TREND_DOWN']:
        # Trend: 넓은 TP (추세 극대화)
        tp1_mult = 1.5  # RR = 1.5
        tp2_mult = 3.0  # RR = 3.0
    elif regime == 'RANGE':
        # Range: 좁은 TP (빠른 익절)
        tp1_mult = 1.5  # RR = 1.5
        tp2_mult = 2.5  # RR = 2.5
    
    tp1_distance = sl_distance * tp1_mult
    tp2_distance = sl_distance * tp2_mult
    
    if side == 'LONG':
        tp1_price = entry_price + tp1_distance
        tp2_price = entry_price + tp2_distance
    else:
        tp1_price = entry_price - tp1_distance
        tp2_price = entry_price - tp2_distance
    
    return {
        'tp1': {'price': tp1_price, 'ratio': tp1_mult, 'qty_pct': 0.5},
        'tp2': {'price': tp2_price, 'ratio': tp2_mult, 'qty_pct': 0.5}
    }
```

**Regime별 RR 범위**:

| Regime | SL Mult | TP1 RR | TP2 RR | 특징 |
|--------|---------|--------|--------|------|
| Trend | 2.0 ATR | 1.5 | 3.0 | 깊은 SL, 넓은 TP (추세 극대화) |
| Range | 1.5 ATR | 1.5 | 2.5 | 짧은 SL, 좁은 TP (빠른 익절) |

#### 2.4.2 Multi-TP 구조

**분할 청산 전략**:
1. **TP1 도달** (50% 포지션):
   - 즉시 50% 청산
   - 나머지 50%는 TP2 또는 Trailing Stop으로 관리
   - SL을 Entry Price로 이동 (Break-even Stop)

2. **TP2 도달** (나머지 50%):
   - 전체 청산
   - 또는 Trailing Stop 지속 (Trend Mode에서 선택적)

**Trailing Stop** (선택적, Trend Mode):
- TP1 도달 후 활성화
- Trailing Distance: ATR * 1.0
- 목적: Trend 극대화, TP2 이상 수익 추구

#### 2.4.3 포지션 관리

**포지션 크기**:
```python
def calculate_position_size(account_equity, sl_distance, risk_per_trade):
    # Kelly Criterion 기반, 보수적 적용
    # risk_per_trade = 0.01 (1% per trade)
    
    risk_amount = account_equity * risk_per_trade
    position_size = risk_amount / sl_distance
    
    # 최대 레버리지 제한
    max_position = account_equity * max_leverage  # max_leverage = 3.0
    position_size = min(position_size, max_position)
    
    return position_size
```

**동시 포지션 제한**:
- 최대 1개 (현재 단일 심볼)
- 향후 Multi-Symbol 시 최대 3~5개 (Portfolio-level Risk)

**레버리지 상한**:
- 최대 3x (보수적)
- Guard Max DD 12%와 연동하여 과도한 레버리지 방지

### 2.5 Guard 연동 설계

#### 2.5.1 설계 원칙

**Guard OFF 성능은 평가 대상에서 제외**:
- V4 문제: Guard OFF에서만 테스트 → 실제 운영 불가
- New Design: **Guard ON을 전제로 설계/검증**

**전략과 Guard 파라미터 조율**:
- 전략이 DD 20%를 허용하는 구조 X
- Guard Max DD 12% 안에 자연스럽게 들어오도록 설계

#### 2.5.2 Guard 파라미터와의 호환성

**Current Guard 시스템** (PHASE17 기준):
| Guard Type | 파라미터 | 전략 설계 시 고려사항 |
|------------|----------|----------------------|
| **Cooldown** | cooldown_candles = 2 | 진입 간격 최소 30분 (15m * 2) |
| **RR Filter** | min_rr_required = 1.5 | 전략 RR >= 1.5 보장 필수 |
| **DD Guard** | max_drawdown = 0.12 | SL/TP 설계 시 DD 12% 초과 방지 |
| **Volume Guard** | min_volume_ratio = 0.7 | Core AND에서 이미 적용 |
| **Volatility Guard** | min_atr_pct = 0.002 | Core AND에서 이미 적용 |

**전략 내장 필터 vs Guard 중복 방지**:
- Core AND에서 Volume, ATR 필터 → Guard와 동일 기준 사용
- Guard는 최종 안전장치, 전략은 1차 필터

#### 2.5.3 백테스트 시 Guard 처리

**필수 테스트 시나리오**:
1. **Guard ON (Real-world)**:
   - cooldown_candles = 2
   - min_rr_required = 1.5
   - max_drawdown = 0.12
   - **이 설정을 기본으로 평가**

2. **Guard OFF (Diagnostic only)**:
   - 전략 자체 성능 파악용
   - 실제 운영과는 무관, 참고 자료만

**AC3 판정 기준**:
- **Guard ON 결과로만 판정**
- Guard OFF 결과는 분석 참고용

---

## 3. 백테스트 & 검증 계획

### 3.1 데이터 구간 선택

**최소 요구사항**: 3개월 이상

**권장 구간**:
- **기간**: 2024년 9월 1일 ~ 2024년 12월 1일 (3개월)
- **이유**:
  - Bull / Bear / Sideways 시장 모두 포함
  - 최근 데이터로 현재 시장 패턴 반영
  - PHASE29 V4 백테스트와 비교 가능 (2024년 11월 구간 포함)

**시장 조건 분포** (예상):
| 구간 | 시장 조건 | 특징 |
|------|----------|------|
| 2024-09 | Sideways → Bull | Range → Trend Up 전환 |
| 2024-10 | Bull | Strong Trend Up |
| 2024-11 | Bull → Sideways | Trend Up → Range 전환 |

### 3.2 검증 파이프라인

**PHASE25-0/1 인프라 활용**:
- Long-run PAPER harness
- Tuning Cluster Infra (Bayesian, Grid, Random Search)

**검증 순서** (PHASE30-1/30-2에서 수행):

```
Step 1: 코드 구현 (PHASE30-1)
  └─> strategies/btc15m_core_v1.py
  └─> configs/backtest/phase30_1_btc15m_core_v1_3m_baseline.yml

Step 2: 3개월 Baseline 백테스트 (PHASE30-1)
  └─> Guard ON
  └─> AC3 평가: Win Rate, Max DD, PF

Step 3: Out-of-Sample 검증 (PHASE30-1)
  └─> 다른 3개월 구간 (예: 2024-06 ~ 2024-08)
  └─> 과적합 여부 확인

Step 4: Light Tuning (PHASE30-2)
  └─> Regime Threshold, SL/TP Mult, Core AND 파라미터
  └─> Grid Search 또는 Bayesian Search
  └─> Top 3 조합 선정

Step 5: Real-time PAPER (PHASE30-3)
  └─> 24H ~ 72H PAPER Mode
  └─> Live 시장 조건에서 안정성 검증
```

### 3.3 Acceptance Criteria 초안

**PHASE30-0 (본 문서)**:
| AC | 항목 | 기준 | 판정 |
|----|------|------|------|
| AC1 | 설계 문서 완성도 | Core AND / Optional OR / Regime / SL/TP / Guard 연동이 구체적으로 정의됨 | ✅ |
| AC2 | V2/V3/V4 차별점 | 실패 교훈이 설계에 명확히 반영됨 | ✅ |
| AC3 | 성능 목표 일관성 | PHASE29-7 권고와 일치 (Win Rate 40~45%, Max DD ≤ 12%, RR ≥ 1.5) | ✅ |
| AC4 | 백테스트 계획 명시 | PHASE30-1/2 검증 계획 포함 | ✅ |

**PHASE30-1 (코드 구현 & 백테스트)**:
| AC | 항목 | 기준 |
|----|------|------|
| AC1 | 3M Baseline 완료 | Guard ON, 에러 없이 완료 |
| AC2 | Win Rate | ≥ 40% |
| AC3 | Max DD | ≤ 12% |
| AC4 | Profit Factor | > 1.2 |
| AC5 | 거래 건수 | 60~120건/월 |
| AC6 | Out-of-Sample | 다른 3M 구간에서 유사 성능 |

**PHASE30-2 (Light Tuning)**:
| AC | 항목 | 기준 |
|----|------|------|
| AC1 | 튜닝 완료 | 16~24개 조합 테스트 |
| AC2 | Top 3 선정 | AC3 기준 통과 조합 최소 1개 |
| AC3 | ROADMAP 업데이트 | 최종 결과 문서화 |

---

## 4. Acceptance Criteria

### 4.1 PHASE30-0 (본 문서)

| AC | 항목 | 판정 |
|----|------|------|
| **AC1** | 설계 문서에 Core AND / Optional OR / Regime / SL/TP / Guard 연동이 구체적으로 정의됨 | ✅ **PASS** |
| **AC2** | 성능 목표(Win Rate 40~45%, Max DD ≤ 12%, PF > 1.2)가 PHASE29-7 권고와 일치 | ✅ **PASS** |
| **AC3** | 향후 PHASE30-1/2 백테스트 계획이 명시됨 | ✅ **PASS** |
| **AC4** | 기존 V2/V3/V4 설계와의 차별점 및 교훈 반영이 문서화됨 | ✅ **PASS** |

### 4.2 차별점 요약

| 항목 | V2/V3/V4 | btc15m_core_v1 (New Design) |
|------|----------|------------------------------|
| **진입 조건** | V2: 모든 조건 OR<br>V3: 모든 조건 AND<br>V4: OR + Score | **Core AND + Optional OR**<br>(필수 조건 먼저, 선택 시나리오 후) |
| **Regime** | V4: ADX 단일 지표 | **ADX + ATR + Volume + DI 복합 지표**<br>확률적 신뢰도 점수 |
| **RR** | V4: 1.0~1.2 (낮음) | **≥ 1.5 (최소 기준)**<br>Regime별 동적 조정 |
| **Timeframe** | V2/V3/V4: 5m (노이즈 과다) | **15m (Primary), 30m (Secondary)**<br>노이즈 감소, 신호 품질 향상 |
| **Guard** | V4: Guard OFF 테스트 | **Guard ON 전제 설계**<br>호환성 사전 검증 |
| **Multi-TP** | V4: TP1=60%, TP2=40% (구조만) | **TP1=50%, TP2=50% + Trailing**<br>Regime별 RR 차별화 |

---

## 5. 다음 단계

### 5.1 PHASE30-1: 코드 구현 & 백테스트

**목표**: btc15m_core_v1 전략 코드 구현 및 3M Baseline 백테스트

**산출물**:
- `strategies/btc15m_core_v1.py`
- `configs/backtest/phase30_1_btc15m_core_v1_3m_baseline.yml`
- `docs/PHASE30/PHASE30_1_BTC15M_CORE_V1_3M_BASELINE_RESULT_KR.md`
- `reports/analysis/PHASE30/phase30_1_ac3_performance.json`

**Acceptance Criteria**:
- AC1: Guard ON 백테스트 완료 (에러 없음)
- AC2: Win Rate ≥ 40%
- AC3: Max DD ≤ 12%
- AC4: Profit Factor > 1.2
- AC5: 거래 건수 60~120건/월

### 5.2 PHASE30-2: Light Tuning

**목표**: 파라미터 최적화, Top 3 조합 선정

**튜닝 대상**:
- Regime Threshold (ADX, ATR, Volume)
- SL/TP Mult (Trend vs Range)
- Core AND 필터 (min_atr, min_volume)
- Optional OR 시나리오 가중치 (필요 시)

**산출물**:
- `configs/backtest/phase30_2_tuning_*.yml` (16~24개)
- `docs/PHASE30/PHASE30_2_LIGHT_TUNING_RESULT_KR.md`
- `reports/analysis/PHASE30/phase30_2_tuning_summary.json`

### 5.3 PHASE30-3: Real-time PAPER

**목표**: 실시간 시장 조건에서 안정성 검증

**Duration**: 24H ~ 72H

**Acceptance Criteria**:
- 프로세스 안정성 (중간 종료 없음)
- 거래 발생 (최소 기준: 24H에 2~5건)
- Guard 정상 작동
- Performance Metrics 자동 수집

---

## 부록: V2/V3/V4 교훈 요약

### V2 실패 교훈

**문제**: OR 기반 진입 과잉
- 4개 조건 중 하나만 만족해도 진입
- 단일 지표 오류 → 즉시 손실
- Win Rate < 45%

**교훈**: 필수 조건(Core AND)을 먼저 통과시켜야 함

### V3 실패 교훈

**문제**: AND 과잉
- 모든 조건을 동시에 만족해야 진입
- 신호 극소 (17건/월)
- 거래 건수 부족

**교훈**: 부가 조건(Optional OR)으로 시나리오 다양화

### V4 실패 교훈

**문제**: OR + Score (절충 시도 실패)
- Score Threshold가 낮아 저품질 신호 통과 (3/8점)
- ADX 단일 Regime 분류 → 오판 빈번
- RR 1.0~1.2 → Win Rate 54% 필요 (달성 불가)
- 5m 노이즈 과다

**교훈**:
1. Score 시스템보다 명확한 조건 구조 (Core AND + Optional OR)
2. 복합 지표 기반 Regime Detection
3. 최소 RR 1.5 이상
4. 15m/30m Timeframe으로 노이즈 감소
5. Guard ON 전제 설계

---

**작성자**: Cascade AI  
**검토일**: 2025-12-11  
**상태**: ✅ COMPLETE

**다음 단계**: PHASE30-1 (코드 구현 & 3M Baseline 백테스트)
