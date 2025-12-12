# PHASE30-2: btc15m_core_v2 Strategy Redesign Specification

**작성일**: 2025-12-12  
**상태**: ✅ **DESIGN COMPLETE**  
**목표**: Core V1 구조적 한계 극복을 위한 전면 재설계

---

## 목차

1. [개요](#1-개요)
2. [성능 목표 (To-Be Metrics)](#2-성능-목표-to-be-metrics)
3. [구조 비교: Core V1 vs Core V2](#3-구조-비교-core-v1-vs-core-v2)
4. [Regime Detection V2 설계](#4-regime-detection-v2-설계)
5. [Core AND V2 설계](#5-core-and-v2-설계)
6. [Optional OR Scenario V2 설계](#6-optional-or-scenario-v2-설계)
7. [SL/TP & Multi-TP V2 설계](#7-sltp--multi-tp-v2-설계)
8. [Risk & Guard Integration](#8-risk--guard-integration)
9. [파라미터 테이블](#9-파라미터-테이블)
10. [PHASE30-3 Implementation Plan](#10-phase30-3-implementation-plan)

---

## 1. 개요

### 1.1 PHASE30-1 시리즈 핵심 교훈

**3회 시도 결과 요약**:

| PHASE | 필터 강도 | 거래 (3M) | 월평균 | Win Rate | Profit Factor | 판정 |
|-------|----------|----------|--------|----------|---------------|------|
| **30-1** | Strict | 15건 | 5/월 | N/A | N/A | ❌ 거래 부족 |
| **30-1b** | Relaxed | 138건 | 46/월 | 28.99% | 0.67 | ❌ 품질 미달 |
| **30-1c** | Mid | 48건 | 16/월 | 31.25% | 0.77 | ❌ 모두 미달 |

**공통 실패 원인**:
1. **필터 조정만으로는 해결 불가**: Strict → Relaxed → Mid 모두 AC3 미달
2. **Regime Detection 신뢰도 한계**: 15m 단독으로는 0.25 신뢰도도 부족
3. **Optional OR 시나리오 부족**: 8개 시나리오로는 다양한 시장 상황 대응 불가
4. **RR vs Win Rate 미스매치**: RR 1.5 + Win Rate 31.25% → EV = -0.22 (마이너스)
5. **필터 곱셈 효과**: 3개 필터 동시 적용 시 예상보다 65% 과도 감소

**정량적 증거**:
```
필터 통과율 추정 (30-1c):
- min_confidence 0.2 → 0.25: 통과율 ~80%
- min_atr_pct 0.0015 → 0.00175: 통과율 ~85%
- min_volume_ratio 0.5 → 0.6: 통과율 ~70%
→ 예상 전체 통과율 = 0.80 × 0.85 × 0.70 = 47.6%
→ 예상 거래수 = 138 × 0.476 ≈ 66건
→ 실제 거래수 = 48건 (예상보다 27% 추가 감소)
→ 원인: 필터 간 상관관계 (독립적이지 않음)
```

### 1.2 PHASE29-7 (V4 Postmortem) 핵심 교훈

**V4 전략 실패 원인**:
- **OR 기반 Score 조합** → 저품질 신호 과다 (Win Rate 27.86%)
- **ADX 단일 지표 Regime 분류** → 정확도 부족
- **5m Timeframe 노이즈** → False Signal 과다
- **낮은 RR (1.0~1.2)** → Win Rate 54% 필요 (달성 불가)

**보존할 요소**:
- ✅ Regime-Aware 구조 (Trend/Range 분리)
- ✅ Multi-TP 구조 (TP1 50%, TP2 50%)
- ✅ ATR 기반 SL/TP 계산
- ✅ Guard 시스템 연동

**폐기할 요소**:
- ❌ OR 기반 Score 조합
- ❌ ADX 단일 지표 Regime 분류
- ❌ 낮은 RR (1.0~1.2)
- ❌ 5m Timeframe 고집

### 1.3 Core V2 설계 철학

**근본적 구조 변경**:
1. **Higher Timeframe Regime** (1H/4H) + 15m Entry
2. **필터 독립성 확보**: "절대 조건" vs "패널티/가중치 조건" 분리
3. **Optional OR 확장**: 8개 → 12~16개 시나리오
4. **동적 RR 조정**: Regime별 + Win Rate 목표 기반
5. **Guard 포지션 조정 통합**: 진입 차단뿐 아니라 크기 조정

**차별점**:
- **V1**: 15m 단독 Regime, 8 시나리오, RR 1.5 고정 → 실패
- **V2**: 1H/4H 참조, 12~16 시나리오, RR 2.0~2.5 동적 → 목표

---

## 2. 성능 목표 (To-Be Metrics)

### 2.1 정량 목표

| 지표 | 목표 | V1 실제 (30-1c) | Gap | 근거 |
|------|------|----------------|-----|------|
| **거래 건수 (3M)** | 80~120건 | 48건 | -32건 | 월 27~40건 (15m 적정) |
| **월평균 거래** | 27~40건/월 | 16건/월 | -11건 | V2 시나리오 확장 효과 |
| **Win Rate** | 38~42% | 31.25% | -6.75%p | RR 2.0 기준 손익분기 33% |
| **Profit Factor** | ≥ 1.2 | 0.77 | +0.43 | 명확한 이익 구조 |
| **Max Drawdown** | ≤ 12% | 0.9% | OK | Guard와 연동 |
| **Risk:Reward** | 2.0~2.5 | 1.5 | +0.5 | Regime별 동적 |

### 2.2 수학적 검증

**Expected Value (EV) 계산**:

```
RR = 2.0, Win Rate = 35%
EV = 0.35 * 2.0 - 0.65 * 1.0 = 0.7 - 0.65 = +0.05 (손익분기)

RR = 2.0, Win Rate = 40%
EV = 0.40 * 2.0 - 0.60 * 1.0 = 0.8 - 0.6 = +0.20 (이익)

RR = 2.5, Win Rate = 35%
EV = 0.35 * 2.5 - 0.65 * 1.0 = 0.875 - 0.65 = +0.225 (이익)
```

**결론**: RR 2.0 이상이면 Win Rate 35%만 되어도 이익 구조 확보 가능.

### 2.3 Timeframe 전략

**Primary**: 15m (Entry & Execution)
- 5m 대비 노이즈 70% 감소
- 신호 품질 향상, False Signal 억제
- 거래 건수 적정선 유지 (30~40건/월)

**Secondary**: 1H / 4H (Regime Detection)
- Higher TF에서 "대세 Regime" 판단
- 15m Entry와 1H Regime의 방향 일치 확인
- Regime 신뢰도 상승 효과

---

## 3. 구조 비교: Core V1 vs Core V2

### 3.1 전체 구조 비교표

| 항목 | **Core V1** (PHASE30-1) | **Core V2** (PHASE30-2) | 변경 효과 |
|------|------------------------|------------------------|----------|
| **Regime Detection** | 15m 단독 (ADX+ATR+Vol+DI) | **1H/4H + 15m** 복합 | 신뢰도 0.25 → 0.35~0.4 |
| **Regime 신뢰도 계산** | Local TF only | **0.6 × Higher TF + 0.4 × Local TF** | 대세 추세 우선 반영 |
| **Hysteresis** | 3 캔들 유지 | **5 캔들 + 조건 강화** | False 전환 억제 |
| **Core AND 필터** | 3개 (곱셈 효과) | **2-Tier** (절대/패널티 분리) | 거래량 과도 감소 방지 |
| **Optional OR 시나리오** | 8개 (Trend 3+3, Range 2) | **12~16개** (Regime별 4~5개) | 다양한 시장 대응 |
| **SL/TP RR** | 1.5 고정 | **2.0~2.5** (Regime별 동적) | Win Rate 35%로 이익 구조 |
| **Multi-TP 비중** | TP1 50%, TP2 50% | **TP1 70%, TP2 30%** | 빠른 이익 실현 |
| **Guard 통합** | 진입 차단만 | **진입 차단 + 포지션 크기 조정** | 연속 손실 시 적응 |

### 3.2 진입 로직 비교

**Core V1**:
```python
IF Core AND (Regime + ATR + Volume + Confidence >= 0.25):
    IF Optional OR (8 scenarios):
        → ENTER
```

**Core V2**:
```python
# Step 1: Higher TF Regime 확인
higher_regime = get_regime_1h()  # TREND_UP, TREND_DOWN, RANGE, CHOP
if higher_regime == 'CHOP':
    return NO_ENTRY  # Choppy 시장 진입 금지

# Step 2: Regime 신뢰도 계산
confidence = 0.6 * higher_regime_score + 0.4 * local_regime_score
if confidence < 0.35:
    return NO_ENTRY

# Step 3: 2-Tier Core AND
if NOT core_absolute_conditions():  # 절대 조건 (Guard, DD, 연속손실)
    return NO_ENTRY

# Step 4: Optional OR (12~16 scenarios)
if match_any_scenario(regime, df):
    position_size = calculate_size_with_penalty(atr, volume)  # 패널티 반영
    → ENTER with adjusted size
```

### 3.3 차별점 요약

**핵심 변화**:
1. **Higher TF Regime 도입** → 신뢰도 35~40% 목표
2. **2-Tier Core AND** → 필터 곱셈 효과 완화
3. **시나리오 확장** → 8 → 12~16개
4. **동적 RR** → 1.5 → 2.0~2.5
5. **포지션 크기 조정** → Guard와 통합

---

## 4. Regime Detection V2 설계

### 4.1 Higher Timeframe Regime (1H/4H)

**목적**: 15m 단독 Regime의 신뢰도 한계 극복

**V1 문제**:
- 15m ADX+ATR+Volume+DI → 신뢰도 0.25도 부족
- 2024-11 BTC 시장: Trend/Range 경계 모호한 구간 다수
- 잦은 Regime 전환 → False Entry 증가

**V2 해결책**:
```python
def detect_regime_v2(df_1h, df_4h, df_15m, config):
    """
    Multi-Timeframe Regime Detection
    
    Returns:
        {
            'regime': str,  # TREND_UP, TREND_DOWN, RANGE, CHOP
            'confidence': float,  # 0~1.0
            'higher_tf_score': float,
            'local_tf_score': float,
            'hysteresis_met': bool
        }
    """
    
    # Step 1: 1H Regime 판단 (대세)
    regime_1h = _detect_single_tf(df_1h, '1H')
    score_1h = regime_1h['confidence']
    
    # Step 2: 4H Regime 판단 (초대세)
    regime_4h = _detect_single_tf(df_4h, '4H')
    score_4h = regime_4h['confidence']
    
    # Step 3: 15m Regime 판단 (Entry용)
    regime_15m = _detect_single_tf(df_15m, '15m')
    score_15m = regime_15m['confidence']
    
    # Step 4: Higher TF Score (1H 70%, 4H 30%)
    higher_tf_score = 0.7 * score_1h + 0.3 * score_4h
    
    # Step 5: Final Confidence (Higher TF 60%, Local TF 40%)
    final_confidence = 0.6 * higher_tf_score + 0.4 * score_15m
    
    # Step 6: Regime 일치 여부 확인
    if regime_1h['regime'] != regime_15m['regime']:
        # 불일치 시 패널티
        final_confidence *= 0.7
    
    # Step 7: Hysteresis 체크
    hysteresis_met = check_hysteresis(df_15m, regime_15m['regime'])
    
    return {
        'regime': regime_1h['regime'],  # Higher TF 우선
        'confidence': final_confidence,
        'higher_tf_score': higher_tf_score,
        'local_tf_score': score_15m,
        'hysteresis_met': hysteresis_met
    }
```

### 4.2 Regime 정의 (4가지)

**1. TREND_UP (강세 추세)**
- **조건**:
  - 1H: ADX > 25, DI+ > DI-, EMA(20) < EMA(50) < Price
  - 4H: ADX > 20, DI+ > DI-
  - 15m: ADX > 20, DI+ > DI-
- **신뢰도 점수**:
  ```python
  score = (
      0.3 * (adx_1h - 20) / 20  # 1H ADX 기여 30%
      + 0.2 * (di_diff_1h / di_plus_1h)  # 1H 방향성 20%
      + 0.2 * (adx_4h - 15) / 15  # 4H ADX 20%
      + 0.15 * (atr_1h / avg_atr_1h - 1)  # 1H 변동성 15%
      + 0.15 * (volume_1h / avg_volume_1h - 1)  # 1H 거래량 15%
  )
  # Score >= 0.7 → High Confidence
  # Score 0.4~0.7 → Medium
  # Score < 0.4 → Low (진입 금지)
  ```

**2. TREND_DOWN (약세 추세)**
- TREND_UP의 역방향 (DI- > DI+, Price < EMA)

**3. RANGE (횡보)**
- **조건**:
  - 1H: ADX < 20, BB Width < avg_width * 0.8
  - 4H: ADX < 25
  - 15m: ADX < 25
- **신뢰도 점수**: ADX 낮을수록 + BB Width 좁을수록 ↑

**4. CHOP (고변동성 횡보)**
- **조건**:
  - 1H: ADX < 20, ATR > avg_atr * 1.5, Volume > avg_volume * 1.3
  - **특징**: 방향 없이 변동성만 높음 (진입 금지)
- **대응**: V2에서는 CHOP 감지 시 **진입 차단**

### 4.3 Hysteresis (Regime 전환 조건)

**V1 문제**: 3 캔들만 유지 → 빈번한 False 전환

**V2 해결책**:
```python
def check_hysteresis(df, new_regime, prev_regime, config):
    """
    Regime 전환 시 최소 조건 검증
    
    Args:
        new_regime: 새로 감지된 Regime
        prev_regime: 이전 Regime
    
    Returns:
        bool: Hysteresis 조건 충족 여부
    """
    min_candles = 5  # 최소 5캔들 유지
    
    if new_regime == prev_regime:
        return True  # 동일 Regime 유지
    
    # Regime 전환 조건
    recent_5 = df.iloc[-5:]
    
    if new_regime == 'TREND_UP':
        # 최근 5캔들 중 4개 이상이 TREND_UP 조건 충족
        trend_up_count = sum([
            (row['adx_14'] > 25 and row['di_plus_14'] > row['di_minus_14'])
            for _, row in recent_5.iterrows()
        ])
        return trend_up_count >= 4
    
    elif new_regime == 'RANGE':
        # 최근 5캔들 모두 ADX < 20
        range_count = sum([
            row['adx_14'] < 20
            for _, row in recent_5.iterrows()
        ])
        return range_count >= 5  # 엄격한 조건
    
    # 기타 Regime도 유사 로직
    return False
```

### 4.4 Regime 신뢰도 임계값

| Regime | Min Confidence | 권장 Confidence | 비고 |
|--------|---------------|----------------|------|
| TREND_UP | 0.35 | 0.40~0.50 | Higher TF 동의 필수 |
| TREND_DOWN | 0.35 | 0.40~0.50 | Higher TF 동의 필수 |
| RANGE | 0.40 | 0.45~0.55 | 더 엄격 (Range는 정확도 중요) |
| CHOP | - | - | 진입 금지 |

**V1 대비 개선**:
- V1: min_confidence = 0.25 (너무 낮음)
- V2: min_confidence = 0.35 (Higher TF 반영 시 달성 가능)

---

## 5. Core AND V2 설계

### 5.1 V1 문제: 필터 곱셈 효과

**PHASE30-1c 실제 사례**:
```
3개 필터 동시 적용:
- min_confidence 0.2 → 0.25: 통과율 ~80%
- min_atr_pct 0.0015 → 0.00175: 통과율 ~85%
- min_volume_ratio 0.5 → 0.6: 통과율 ~70%

예상 전체 통과율 = 0.80 × 0.85 × 0.70 = 47.6%
예상 거래수 = 138 × 0.476 ≈ 66건
실제 거래수 = 48건 (예상보다 27% 추가 감소)

원인: 필터 간 상관관계 (독립적이지 않음)
```

**근본 문제**:
- 저변동성 + 낮은 거래량 구간에서 **3개 필터가 모두 동시 차단**
- AND 조건이미로 하나라도 실패하면 전체 실패
- 필터를 완화하면 거래 늘지만 품질 저하 (Win Rate 28.99%)

### 5.2 V2 해결책: 2-Tier Core AND

**철학**: "절대 조건" vs "패널티/가중치 조건" 분리

#### Tier 1: 절대 조건 (하나라도 실패 시 진입 금지)

```python
def check_absolute_conditions(regime_info, guard_state, portfolio):
    """
    절대적으로 충족해야 하는 조건
    
    Returns:
        (bool, str): (통과 여부, 실패 사유)
    """
    
    # 1. Regime Confidence (최소 기준)
    if regime_info['confidence'] < 0.35:
        return False, f"low_confidence_{regime_info['confidence']:.2f}"
    
    # 2. CHOP 시장 차단
    if regime_info['regime'] == 'CHOP':
        return False, "chop_market_blocked"
    
    # 3. Guard 통과
    if not guard_state.is_entry_allowed():
        return False, "guard_blocked"
    
    # 4. Max DD 근접 (80% 이상)
    if portfolio.current_dd > 0.096:  # 12% × 0.8
        return False, f"dd_near_limit_{portfolio.current_dd:.2%}"
    
    # 5. 연속 손실 한계
    if portfolio.consecutive_losses >= 8:  # 최대 10, 80% 시점
        return False, f"consecutive_loss_{portfolio.consecutive_losses}"
    
    # 6. Hysteresis 충족
    if not regime_info['hysteresis_met']:
        return False, "hysteresis_not_met"
    
    return True, "absolute_pass"
```

#### Tier 2: 패널티/가중치 조건 (진입 허용, 포지션 크기 조정)

```python
def calculate_position_penalty(df, regime_info, config):
    """
    패널티 조건: 진입은 허용하되, 포지션 크기를 조정
    
    Returns:
        float: position_size_multiplier (0.5~1.0)
    """
    last = df.iloc[-1]
    recent = df.iloc[-20:]
    
    multiplier = 1.0  # 기본값
    
    # 1. ATR 패널티
    atr = float(last.get('atr_14', 0))
    price = float(last['close'])
    atr_pct = atr / price if price > 0 else 0.0
    
    min_atr_pct = config.get('filters', {}).get('min_atr_pct', 0.0015)
    if atr_pct < min_atr_pct:
        # ATR 부족 시 크기 30% 감소
        multiplier *= 0.7
    elif atr_pct < min_atr_pct * 1.2:
        # 경계 구간 10% 감소
        multiplier *= 0.9
    
    # 2. Volume 패널티
    volume = float(last.get('volume', 0))
    avg_volume = float(recent['volume'].mean()) if 'volume' in recent.columns else volume
    volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
    
    min_volume_ratio = config.get('filters', {}).get('min_volume_ratio', 0.5)
    if volume_ratio < min_volume_ratio:
        # Volume 부족 시 크기 30% 감소
        multiplier *= 0.7
    elif volume_ratio < min_volume_ratio * 1.2:
        # 경계 구간 10% 감소
        multiplier *= 0.9
    
    # 3. Regime Confidence 패널티
    confidence = regime_info['confidence']
    if confidence < 0.40:
        # 낮은 신뢰도 시 크기 20% 감소
        multiplier *= 0.8
    elif confidence < 0.45:
        # 중간 신뢰도 시 크기 10% 감소
        multiplier *= 0.9
    
    # 4. 최소 크기 보장 (50%)
    multiplier = max(multiplier, 0.5)
    
    return multiplier
```

### 5.3 2-Tier 효과

**V1 vs V2 비교**:

| 상황 | V1 (AND 곱셈) | V2 (2-Tier) | 효과 |
|------|-----------------|-----------|
| ATR 0.15%, Vol 0.6, Conf 0.38 | ❌ 진입 차단 | ✅ 진입 (70% 크기) | 거래 기회 보존 |
| ATR 0.18%, Vol 0.55, Conf 0.36 | ❌ 진입 차단 | ✅ 진입 (50% 크기) | 거래 기회 보존 |
| ATR 0.12%, Vol 0.4, Conf 0.30 | ❌ 진입 차단 | ❌ 진입 차단 (Tier 1 실패) | 저품질 차단 |
| ATR 0.20%, Vol 0.8, Conf 0.45 | ✅ 진입 (100%) | ✅ 진입 (100%) | 동일 |

**예상 효과**:
- 거래 기회 30~40% 증가 (48건 → 65~70건)
- 평균 포지션 크기 80~85% (패널티 반영)
- Win Rate 유지 또는 소폭 상승 (크기 조정 효과)

---

## 6. Optional OR Scenario V2 설계

### 6.1 V1 문제: 시나리오 부족

**현재 V1 시나리오** (8개):
- Trend-Up: EMA Pullback, RSI Oversold, BB Lower (3개)
- Trend-Down: EMA Pullback, RSI Overbought, BB Upper (3개)
- Range: BB Lower Bounce, BB Upper Fade (2개)

**문제점**:
1. 시나리오 간 중복 (EMA Pullback + RSI 동시 충족 시 두 개 트리거)
2. Trend 시장에서 Range 시나리오 없음
3. Breakout, Momentum, Divergence 등 주요 패턴 미포함
4. Volume Profile, Multi-TF Confirmation 미적용

### 6.2 V2 해결책: 12~16 시나리오 확장

#### Trend-Up Mode (LONG only, 5개 시나리오)

**1. EMA Pullback (V1 유지)**
```python
scenario_a = (
    price > ema_50 and
    low <= ema_50 * 1.002 and
    price > open_price
)
```

**2. RSI Oversold + Bounce (V1 유지)**
```python
scenario_b = (
    rsi < 35 and
    rsi > prev_rsi and
    price > open_price
)
```

**3. BB Lower + Volume Spike (V1 유지)**
```python
scenario_c = (
    low <= bb_lower * 1.001 and
    volume > avg_volume * 1.3 and
    price > (high + low) / 2
)
```

**4. Breakout + Confirmation (NEW)**
```python
scenario_d = (
    price > recent_20_high and  # 20캔들 고점 돌파
    volume > avg_volume * 1.5 and  # Volume Spike
    adx_15m > 25 and  # 15m 추세 강화
    regime_1h == 'TREND_UP'  # 1H Trend 확인
)
```

**5. Momentum Divergence (NEW)**
```python
scenario_e = (
    price < prev_5_low and  # 가격 저점 갱신
    rsi > prev_5_rsi_low and  # RSI 저점은 높음 (Bullish Divergence)
    volume > avg_volume * 1.2 and
    regime_1h == 'TREND_UP'
)
```

#### Trend-Down Mode (SHORT only, 5개 시나리오)

- Scenario A~C: V1 유지 (반대 방향)
- Scenario D: Breakdown + Confirmation
- Scenario E: Bearish Divergence

#### Range Mode (양방향, 4개 시나리오)

**1. BB Lower Bounce (LONG, V1 유지)**
```python
long_scenario_a = (
    low <= bb_lower * 1.002 and
    rsi < 40 and
    price > open_price
)
```

**2. BB Upper Fade (SHORT, V1 유지)**
```python
short_scenario_a = (
    high >= bb_upper * 0.998 and
    rsi > 60 and
    price < open_price
)
```

**3. Support/Resistance Bounce (NEW)**
```python
# LONG: Support 반등
long_scenario_b = (
    price <= support_level * 1.005 and  # Support 근처
    volume > avg_volume * 1.2 and
    price > open_price  # 반등 캔들
)

# SHORT: Resistance 반락
short_scenario_b = (
    price >= resistance_level * 0.995 and
    volume > avg_volume * 1.2 and
    price < open_price
)
```

**4. Fakeout Play (NEW)**
```python
# LONG: False Breakdown 후 반등
long_scenario_c = (
    prev_low < bb_lower and  # 이전 캔들 BB 돌파
    price > bb_lower and  # 현재 캔들 복귀
    volume < avg_volume * 0.8 and  # 낮은 Volume (Fakeout)
    price > open_price
)
```

### 6.3 시나리오 우선순위

**동시에 여러 시나리오 트리거 시**:
```python
def select_best_scenario(matched_scenarios, regime_info):
    """
    여러 시나리오 트리거 시 우선순위 선택
    
    Priority:
    1. Breakout/Breakdown (Volume + Momentum)
    2. Divergence (Reversal Signal)
    3. EMA Pullback (Trend Following)
    4. Support/Resistance Bounce
    5. BB + RSI (Oversold/Overbought)
    """
    priority_order = [
        'breakout', 'breakdown',  # 최고 우선
        'divergence',
        'ema_pullback',
        'support_resistance',
        'bb_rsi'
    ]
    
    for priority in priority_order:
        if priority in matched_scenarios:
            return priority
    
    # 우선순위 없으면 첫 번째 시나리오
    return matched_scenarios[0]
```

### 6.4 V2 시나리오 총 개수

| Regime | V1 시나리오 | V2 시나리오 | 추가 |
|--------|-----------|-----------|------|
| Trend-Up | 3 | **5** | +2 |
| Trend-Down | 3 | **5** | +2 |
| Range | 2 | **4** | +2 |
| **총계** | **8** | **14** | **+6** |

**예상 효과**:
- 거래 기회 40~60% 증가 (48건 → 70~80건)
- 다양한 시장 패턴 대응 가능
- 시나리오별 성능 분석 가능 (DB metadata 활용)

---

## 7. SL/TP & Multi-TP V2 설계

### 7.1 V1 문제: RR vs Win Rate 미스매치

**PHASE30-1c 실제 결과**:
```
RR = 1.5, Win Rate = 31.25%
EV = 0.3125 × 1.5 - 0.6875 × 1.0 = 0.46875 - 0.6875 = -0.22 (마이너스)

손익분기 계산:
RR = 1.5 → Win Rate 필요 = 1.0 / (1.0 + 1.5) = 40%
실제 Win Rate 31.25% < 40% → 구조적 손실
```

**V1 SL/TP 구조**:
- Trend: SL = 2.0 ATR, TP1 = 1.5 × SL (RR 1.5), TP2 = 3.0 × SL (RR 3.0)
- Range: SL = 1.5 ATR, TP1 = 1.5 × SL (RR 1.5), TP2 = 2.5 × SL (RR 2.5)
- Multi-TP: TP1 50%, TP2 50%

**문제점**:
1. RR 1.5는 Win Rate 40% 필요 → 실제 31.25%로 불가능
2. TP1 50% 비중은 너무 낮음 → 변동성 리스크 노출
3. TP2 도달률 낮음 (50% 포지션 유지 시)

### 7.2 V2 해결책: 동적 RR 2.0~2.5 + TP1 70%

#### 7.2.1 Regime별 RR 설계

**목표 RR 및 Win Rate 관계**:

| Target Win Rate | Min RR 필요 | V2 RR 설정 | 기대값 (EV) |
|-----------------|------------|-----------|---------------|
| 35% | 1.86 | 2.0 | +0.05 (소폭 이익) |
| 38% | 1.63 | 2.0 | +0.14 (이익) |
| 40% | 1.50 | 2.0 | +0.20 (이익) |

**V2 Regime별 RR**:

```python
def calculate_sl_tp_v2(regime, entry_price, atr, side, config):
    """
    Regime별 동적 SL/TP 계산
    
    Returns:
        {
            'sl_price': float,
            'tp1_price': float,
            'tp2_price': float,
            'tp1_qty_pct': float,  # 0.7 (70%)
            'tp2_qty_pct': float,  # 0.3 (30%)
            'rr_tp1': float,
            'rr_tp2': float
        }
    """
    
    # Regime별 SL 배수 & RR
    if regime == 'TREND_UP' or regime == 'TREND_DOWN':
        sl_mult = 1.8  # V1 2.0 → 1.8 (약간 타이트)
        rr_tp1 = 2.0   # V1 1.5 → 2.0 (상향)
        rr_tp2 = 3.5   # V1 3.0 → 3.5 (상향)
    
    elif regime == 'RANGE':
        sl_mult = 1.5  # 동일
        rr_tp1 = 2.0   # V1 1.5 → 2.0 (상향)
        rr_tp2 = 3.0   # V1 2.5 → 3.0 (상향)
    
    else:
        # Default (should not reach here)
        sl_mult = 1.5
        rr_tp1 = 2.0
        rr_tp2 = 3.0
    
    # SL 계산
    sl_distance = atr * sl_mult
    
    if side == 'LONG':
        sl_price = entry_price - sl_distance
        tp1_price = entry_price + sl_distance * rr_tp1
        tp2_price = entry_price + sl_distance * rr_tp2
    else:  # SHORT
        sl_price = entry_price + sl_distance
        tp1_price = entry_price - sl_distance * rr_tp1
        tp2_price = entry_price - sl_distance * rr_tp2
    
    return {
        'sl_price': sl_price,
        'tp1_price': tp1_price,
        'tp2_price': tp2_price,
        'tp1_qty_pct': 0.7,  # 통사 → 70%
        'tp2_qty_pct': 0.3,  # 30%
        'rr_tp1': rr_tp1,
        'rr_tp2': rr_tp2,
        'sl_distance': sl_distance
    }
```

#### 7.2.2 Multi-TP 비중 조정

**V1 vs V2 비교**:

| 항목 | V1 | V2 | 변경 효과 |
|------|----|----|---------|
| **TP1 비중** | 50% | **70%** | 빠른 이익 실현 |
| **TP2 비중** | 50% | **30%** | 변동성 리스크 감소 |
| **TP1 RR** | 1.5 | **2.0** | Win Rate 35%로 이익 구조 |
| **TP2 RR** | 3.0 (Trend) | **3.5** | 추가 상승 여력 |

**비중 변경 이유**:
1. **TP1 70%**: 대부분의 포지션을 빠르게 실현 → 심리적 안정성 ↑
2. **TP2 30%**: 소수 포지션으로 Trend 극대화 시도
3. **변동성 리스크 감소**: 70% 조기 청산 → 대부분 이익 보호

#### 7.2.3 Break-Even Stop & Trailing Stop

**Break-Even Stop** (TP1 도달 후):
```python
def move_to_breakeven(position, tp1_reached):
    """
    TP1 도달 시 SL을 Entry Price로 이동
    """
    if tp1_reached:
        new_sl = position.entry_price  # Break-even
        # 또는 약간 이익 보장 (Entry + 0.2 ATR)
        new_sl = position.entry_price + 0.2 * position.atr * position.side_mult
        return new_sl
    return position.sl_price
```

**Trailing Stop** (Trend 모드, TP1 도달 후):
```python
def trailing_stop_v2(position, current_price, regime):
    """
    Trend 모드에서 TP1 도달 후 Trailing Stop 활성화
    
    Trailing Distance: 1.0 ATR
    """
    if regime not in ['TREND_UP', 'TREND_DOWN']:
        return position.sl_price  # Range는 Trailing 미적용
    
    if not position.tp1_reached:
        return position.sl_price
    
    trailing_distance = position.atr * 1.0
    
    if position.side == 'LONG':
        new_sl = current_price - trailing_distance
        # 기존 SL보다 높을 때만 업데이트
        return max(new_sl, position.sl_price)
    else:  # SHORT
        new_sl = current_price + trailing_distance
        return min(new_sl, position.sl_price)
```

### 7.3 V2 기대 성과

**시뮬레이션 (Win Rate 38% 가정)**:

```
100건 거래 시:
- Win: 38건
  - TP1 도달: 38 × 0.7 = 26.6건 × RR 2.0 = +53.2R
  - TP2 도달: 38 × 0.3 × 0.5 = 5.7건 × RR 3.5 = +20.0R
  (가정: TP2 도달률 50%)
  - 총 Win: +73.2R

- Loss: 62건
  - 총 Loss: -62R

Net PnL = +73.2R - 62R = +11.2R
Profit Factor = 73.2 / 62 = 1.18

비교 (V1, Win Rate 31.25%):
Net PnL = -0.22R (per trade)
Profit Factor = 0.77

V2 개선 효과:
- PF: 0.77 → 1.18 (+53% 상승)
- EV: -0.22R → +0.11R (from loss to profit)
```

**핵심 개선 요인**:
1. RR 1.5 → 2.0 (손익분기 Win Rate 40% → 35%)
2. TP1 70% 비중 (빠른 이익 실현)
3. Win Rate 31.25% → 38% 목표 (V2 구조 개선으로 달성 가능)

---

## 8. Risk & Guard Integration

### 8.1 V1 문제: 연속 손실 시 기회 박살

**PHASE30-1c 문제**:
- 연속 손실 10회 도달 시 진입 완전 차단
- 차단 후 쿨다운 30분 → 추가 기회 상실
- Guard는 "차단"만 가능, "크기 조정" 불가

### 8.2 V2 해결책: Guard 포지션 조정 통합

#### 8.2.1 연속 손실 단계별 대응

```python
def get_position_size_by_consecutive_loss(base_size, consecutive_losses):
    """
    연속 손실 횟수에 따른 포지션 크기 조정
    
    Args:
        base_size: 기본 포지션 크기
        consecutive_losses: 현재 연속 손실 횟수
    
    Returns:
        float: 조정된 포지션 크기
    """
    
    if consecutive_losses <= 2:
        # 정상 구간: 100% 크기
        return base_size * 1.0
    
    elif consecutive_losses <= 4:
        # 경계 구간: 80% 크기
        return base_size * 0.8
    
    elif consecutive_losses <= 6:
        # 주의 구간: 60% 크기
        return base_size * 0.6
    
    elif consecutive_losses <= 8:
        # 위험 구간: 40% 크기
        return base_size * 0.4
    
    else:
        # 한계 초과: 진입 차단
        return 0.0
```

**V1 vs V2 비교**:

| 연속 손실 | V1 (V1) | V2 | 효과 |
|-----------|---------|----|
| 0~2회 | 100% | 100% | 동일 |
| 3~4회 | 100% | **80%** | 점진적 축소 |
| 5~6회 | 100% | **60%** | 리스크 감소 |
| 7~8회 | 100% | **40%** | 최소 기회 보존 |
| 9~10회 | ❌ 차단 | **40%** | 기회 유지 |
| 11회+ | ❌ 차단 | ❌ 차단 | 동일 |

#### 8.2.2 DD 기반 포지션 조정

```python
def get_position_size_by_dd(base_size, current_dd, max_dd=0.12):
    """
    현재 DD에 따른 포지션 크기 조정
    
    Args:
        current_dd: 현재 Drawdown (0~1.0)
        max_dd: 최대 허용 DD (0.12 = 12%)
    """
    
    dd_ratio = current_dd / max_dd
    
    if dd_ratio < 0.5:
        # DD < 6%: 정상
        return base_size * 1.0
    
    elif dd_ratio < 0.7:
        # DD 6~8.4%: 경계
        return base_size * 0.8
    
    elif dd_ratio < 0.85:
        # DD 8.4~10.2%: 주의
        return base_size * 0.6
    
    else:
        # DD > 10.2%: 진입 차단
        return 0.0
```

#### 8.2.3 최종 포지션 크기 계산

```python
def calculate_final_position_size(base_size, regime_info, df, portfolio, config):
    """
    모든 패널티를 통합한 최종 크기 계산
    """
    
    # 1. Tier 2 패널티 (ATR, Volume, Confidence)
    tier2_mult = calculate_position_penalty(df, regime_info, config)
    
    # 2. 연속 손실 패널티
    loss_mult = get_position_size_multiplier_by_loss(portfolio.consecutive_losses)
    
    # 3. DD 패널티
    dd_mult = get_position_size_multiplier_by_dd(portfolio.current_dd)
    
    # 4. 최종 크기 = 기본 × 모든 패널티
    final_size = base_size * tier2_mult * loss_mult * dd_mult
    
    # 5. 최소 크기 보장 (20%)
    final_size = max(final_size, base_size * 0.2)
    
    # 6. 0 시 진입 차단
    if final_size < base_size * 0.2:
        return 0.0
    
    return final_size
```

### 8.3 Guard 파라미터 조율

**V2 Guard 설정**:

| Guard Type | V1 설정 | V2 설정 | 변경 |
|------------|--------|--------|-|
| **min_rr_required** | 1.5 | **2.0** | RR 상향 |
| **cooldown_candles** | 2 (30분) | **1 (15봠6)** | 완화 |
| **max_drawdown** | 0.12 | 0.12 | 동일 |
| **max_consecutive_losses** | 10 | **11** | 약간 여유 |
| **min_atr_pct** | 0.0015 | **Tier 2 패널티** | 차단 → 크기 조정 |
| **min_volume_ratio** | 0.5 | **Tier 2 패널티** | 차단 → 크기 조정 |

**변경 이유**:
1. **RR 2.0**: V2 SL/TP 설계와 일치
2. **Cooldown 1**: 필터 강화로 초기 차단 빈도 감소 → 쿨다운 완화
3. **ATR/Volume**: 차단 대신 Tier 2 패널티로 처리 → 기회 보존

---

## 9. 파라미터 테이블

### 9.1 Regime Detection V2 파라미터

| 파라미터 | 기본값 | 튜닝 범위 | 비고 |
|----------|--------|----------|------|
| `higher_tf_weight` | 0.6 | 0.5~0.7 | Higher TF 비중 |
| `local_tf_weight` | 0.4 | 0.3~0.5 | Local TF 비중 |
| `min_confidence_trend` | 0.35 | 0.30~0.40 | Trend 최소 신뢰도 |
| `min_confidence_range` | 0.40 | 0.35~0.45 | Range 최소 신뢰도 |
| `hysteresis_candles` | 5 | 4~7 | Regime 전환 최소 캔들 |
| `adx_trend_threshold` | 25 | 20~30 | Trend ADX 기준 |
| `adx_range_threshold` | 20 | 15~25 | Range ADX 기준 |

### 9.2 Core AND V2 파라미터

#### Tier 1 (절대 조건)

| 파라미터 | 기본값 | 튜닝 범위 | 비고 |
|----------|--------|----------|------|
| `min_regime_confidence` | 0.35 | 0.30~0.40 | Regime 최소 신뢰도 |
| `max_dd_threshold` | 0.096 | 0.08~0.10 | DD 80% 진입 차단 |
| `consecutive_loss_limit` | 8 | 6~10 | 연속 손실 차단 |

#### Tier 2 (패널티 조건)

| 파라미터 | 기본값 | 튜닝 범위 | 패널티 |
|----------|--------|----------|--------|
| `min_atr_pct` | 0.0015 | 0.0012~0.0020 | < min: 0.7x, < 1.2x: 0.9x |
| `min_volume_ratio` | 0.5 | 0.4~0.7 | < min: 0.7x, < 1.2x: 0.9x |
| `confidence_threshold` | 0.40 | 0.35~0.45 | < 0.40: 0.8x, < 0.45: 0.9x |

### 9.3 SL/TP V2 파라미터

| Regime | SL Mult | TP1 RR | TP2 RR | TP1 Qty% | TP2 Qty% |
|--------|---------|--------|--------|----------|----------|
| **Trend** | 1.8 | 2.0 | 3.5 | 70% | 30% |
| **Range** | 1.5 | 2.0 | 3.0 | 70% | 30% |

**튜닝 범위**:
- `sl_mult_trend`: 1.5~2.0
- `rr_tp1`: 1.8~2.2
- `rr_tp2`: 3.0~4.0
- `tp1_qty_pct`: 0.6~0.8

### 9.4 Guard Integration V2 파라미터

| Guard Type | V2 설정 | 튜닝 범위 |
|------------|--------|----------|
| `min_rr_required` | 2.0 | 1.8~2.2 |
| `cooldown_candles` | 1 | 0~2 |
| `max_drawdown` | 0.12 | 0.10~0.15 |
| `max_consecutive_losses` | 11 | 9~12 |

### 9.5 튜닝 우선순위

**PHASE30-3 구현 후 튜닝 순서**:

1. **Regime Detection**: `min_confidence`, `higher_tf_weight`
2. **SL/TP RR**: `rr_tp1`, `tp1_qty_pct`
3. **Tier 2 패널티**: `min_atr_pct`, `min_volume_ratio`
4. **Guard**: `cooldown_candles`, `max_consecutive_losses`

---

## 10. PHASE30-3 Implementation Plan

### 10.1 개발 범위

**새로 만들 파일**:
1. `strategies/btc15m_core_v2.py` (전략 로직)
2. `configs/backtest/phase30_3_btc15m_core_v2_3m_baseline.yml` (기본 Config)
3. `tests/test_btc15m_core_v2.py` (단위 테스트)

**재사용할 모듈**:
1. `common/backtest_indicators.py` (지표 계산, 기존 확장)
2. `execution/engine.py`, `portfolio_manager.py` (변경 없음)
3. `common/registry/base_strategy.py` (상속)

**절대 금지**:
- 기존 Core V1 파일 수정 (별도 파일로 생성)
- 엔진/Portfolio 코어 로직 변경
- 중복 지표/유틸 함수 생성

### 10.2 구현 순서

#### Phase 1: Regime Detection V2 (1~2 일)

**작업**:
1. `_detect_regime_mtf()` 함수 구현
   - 1H/4H/15m 데이터 입력 받기
   - Higher TF + Local TF 신뢰도 계산
   - CHOP Regime 감지

2. `_check_hysteresis_v2()` 함수 구현
   - 5 캔들 조건 체크
   - Regime별 전환 조건

3. 테스트 작성
   - `test_regime_detection_mtf()`
   - `test_hysteresis_v2()`

#### Phase 2: Core AND V2 & Tier 2 Penalty (1 일)

**작업**:
1. `_check_absolute_conditions()` 구현
2. `_calculate_position_penalty()` 구현
3. 테스트: `test_2tier_core_and()`

#### Phase 3: Optional OR V2 (14 Scenarios) (2 일)

**작업**:
1. Trend-Up 5개 시나리오 구현
   - Breakout, Divergence 추가
2. Trend-Down 5개 시나리오 구현
3. Range 4개 시나리오 구현
   - Support/Resistance, Fakeout 추가
4. 우선순위 로직 구현
5. 테스트: `test_all_scenarios()`

#### Phase 4: SL/TP V2 & Multi-TP (1 일)

**작업**:
1. `_calculate_sl_tp_v2()` 구현
   - Regime별 RR 2.0~2.5
   - TP1 70%, TP2 30%
2. Break-Even Stop, Trailing Stop 구현
3. 테스트: `test_sl_tp_v2()`

#### Phase 5: Guard Integration & Final Position Size (1 일)

**작업**:
1. `_calculate_final_position_size()` 구현
2. 연속 손실/DD 패널티 통합
3. Guard 파라미터 조율
4. 테스트: `test_position_sizing_with_penalty()`

#### Phase 6: Integration & 3M Baseline Backtest (1 일)

**작업**:
1. 모든 모듈 통합
2. Config 파일 완성
3. 3M Baseline 백테스트 실행
4. AC3 평가

### 10.3 기대 성과

**목표 (3M Baseline)**:

| 지표 | V1 실제 | V2 목표 | Gap |
|------|---------|---------|-----|
| **거래 건수** | 48건 | 80~100건 | +67~108% |
| **월평균** | 16건 | 27~33건 | +69~106% |
| **Win Rate** | 31.25% | 38~42% | +6.75~10.75%p |
| **Profit Factor** | 0.77 | 1.15~1.25 | +49~62% |
| **Max DD** | 0.9% | ≤8% | OK |

**AC3 통과 기준**:
- 거래량 80~120건: ✅ PASS (예상)
- Win Rate 38~42%: ✅ PASS (예상)
- Profit Factor ≥1.15: ✅ PASS (예상)
- Max DD ≤12%: ✅ PASS (예상)

### 10.4 테스트 계획

**단위 테스트** (15개):
1. Regime Detection MTF (3개)
2. Hysteresis V2 (2개)
3. 2-Tier Core AND (3개)
4. 14 Scenarios (5개)
5. SL/TP V2 (2개)

**통합 테스트** (3개):
1. 7-Day Sanity Test (20~60건 목표)
2. 1M Gate Test (60~120건 목표)
3. 3M Baseline Test (AC3 평가)

**검증 기준**:
- 단위 테스트 100% PASS
- 7-Day 거래 20~60건
- 3M AC3 4개 기준 모두 PASS

### 10.5 문서화 계획

**생성할 문서**:
1. `PHASE30_3_BTC15M_CORE_V2_IMPLEMENTATION_STATUS_KR.md`
   - 구현 상태, 테스트 결과
2. `PHASE30_3_BTC15M_CORE_V2_3M_BASELINE_RESULT_KR.md`
   - 3M 백테스트 결과, AC3 평가
3. `PHASE_ROADMAP.md` 업데이트
   - PHASE30-3 섹션 추가

### 10.6 마일스톤

**총 예상 소요**: 7~9일

| Phase | 작업 | 소요 | 산출물 |
|-------|------|------|--------|
| Phase 1 | Regime V2 | 1~2일 | 코드 + 테스트 |
| Phase 2 | Core AND V2 | 1일 | 코드 + 테스트 |
| Phase 3 | OR V2 (14) | 2일 | 코드 + 테스트 |
| Phase 4 | SL/TP V2 | 1일 | 코드 + 테스트 |
| Phase 5 | Guard 통합 | 1일 | 코드 + 테스트 |
| Phase 6 | 3M Baseline | 1일 | 백테스트 + 리포트 |

**다음 단계**:
- PHASE30-3 완료 후 AC3 PASS 시 → PHASE30-4 (Light Tuning)
- AC3 FAIL 시 → PHASE30-3b (구조 보정) 또는 PHASE30-5 (30m Timeframe)

---

**문서 종료**

**작성일**: 2025-12-12  
**작성자**: Cascade AI (GPT-5.1 Thinking)  
**상태**: ✅ DESIGN COMPLETE  
**다음 단계**: PHASE30-3 Implementation
