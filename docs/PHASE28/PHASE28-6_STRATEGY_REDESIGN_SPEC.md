# PHASE28-6: btc5m_baseline_v2 전략 재설계 명세서

**Status**: ✅ **SPECIFICATION COMPLETE**  
**Date**: 2025-12-07  
**Phase**: PHASE28-6 (Strategy Logic Overhaul)  
**Author**: AI Development Agent

---

## 📋 Executive Summary

### 설계 목적
**btc5m_baseline_v1의 근본적 결함**을 해결하고, **생존 가능한 (Survivable) 전략**을 설계합니다.

### 핵심 변경 사항
1. **Regime Detection 강화**: ADX + ATR + Volume 기반 6-state 분류 (Bull/Bear/Range × High/Low Volatility)
2. **Dynamic Threshold 도입**: 고정 RSI/BB threshold → Rolling percentile + 변동성 조정
3. **Regime별 Threshold 분리**: Bull/Bear/Range 각각 다른 진입/청산 조건
4. **Long/Short Balance 조정**: Regime에 따라 포지션 bias 자동 조정
5. **ParamSpace 대폭 확장**: RSI 30-70, BB 0.5-2.5, RR 0.8-3.0

### 목표 성능 (Acceptance Criteria)
- **Trade Count**: 월 20개 이상 (현재 5개 → 4배 증가)
- **Sharpe Ratio**: 모든 Period에서 ≥ 0 (최소 생존 수준)
- **Win Rate**: 40% 이상 (현재 0% → 실질적 개선)
- **Multi-Period 성공**: Bull/Bear/Range 각각 독립적으로 Sharpe ≥ 0

---

## 🆚 Section 1: V1 vs V2 비교

### 1.1 전략 철학 변화

| 관점 | V1 (btc5m_baseline_v1) | V2 (btc5m_baseline_v2) |
|------|------------------------|------------------------|
| **핵심 철학** | Mean Reversion (단일 접근) | Regime-Adaptive (다중 접근) |
| **Regime 대응** | 분류만 수행 (적응 없음) | 분류 + 적응 (Threshold 변경) |
| **Threshold** | 고정값 (RSI 45/55, BB 1.0/1.5) | 동적 (Rolling percentile + Volatility 조정) |
| **시장 가정** | Range Market 전용 | Multi-Market (Bull/Bear/Range 모두 대응) |
| **포지션 Bias** | Neutral (50/50) | Adaptive (Regime에 따라 60/40 또는 40/60) |
| **진입 조건** | 3중 필터 (RSI/BB/ADX) | Regime별 2-3개 조건, 적응형 |
| **ParamSpace** | 협소 (RSI 40-48/52-58) | 확장 (RSI 30-70, Regime별 분리) |

### 1.2 구조적 차이

#### V1 구조
```python
# 고정 threshold
rsi_long_threshold = 45  # 모든 regime에서 동일
rsi_short_threshold = 55  # 모든 regime에서 동일

# Regime 분류만
if adx > 25:
    regime = "TREND"
else:
    regime = "RANGE"

# 하지만 threshold는 변경 안됨!
if rsi < rsi_long_threshold:  # 여전히 45
    signal = "LONG"
```

#### V2 구조
```python
# Regime Detection (6-state)
regime = detect_regime(adx, atr, volume)  # Bull/Bear/Range × High/Low Vol

# Regime별 Dynamic Threshold
if regime == "bull_high_vol":
    rsi_long_threshold = percentile(rsi, 30)  # 동적 계산
    rsi_short_threshold = percentile(rsi, 75)
    bb_mult_main = atr_adjusted_bb(atr, base=0.8)
elif regime == "bear_low_vol":
    rsi_long_threshold = percentile(rsi, 15)
    rsi_short_threshold = percentile(rsi, 70)
    bb_mult_main = atr_adjusted_bb(atr, base=0.6)
# ... (각 regime별로 다른 threshold)

# Regime-adaptive 신호
if rsi < rsi_long_threshold:  # threshold가 regime에 따라 다름
    signal = "LONG"
```

### 1.3 핵심 성능 목표 비교

| Metric | V1 실제 | V2 목표 (Minimum Viable) |
|--------|---------|---------------------------|
| **Trade Count** | 5 per month | **20+ per month** (4배 증가) |
| **Sharpe Ratio** | -1.0 ~ +0.75 (단일 lucky trial) | **≥ 0.0 (모든 Period)** |
| **Win Rate** | 0% (대부분) | **≥ 40%** |
| **Max Drawdown** | 200-400% | **≤ 20%** |
| **Multi-Period Pass** | 0/3 (Bull/Bear/Range) | **3/3 (모든 구간 Sharpe ≥ 0)** |

---

## 🧠 Section 2: Regime Detection 설계

### 2.1 Regime 정의 (6-State Classification)

V2는 **2차원 분류**를 사용합니다:
- **차원 1**: 추세 방향 (Bull / Bear / Range)
- **차원 2**: 변동성 수준 (High Volatility / Low Volatility)

**결과**: 6개 상태 (3 × 2)
1. `bull_high_vol`: 상승 추세 + 높은 변동성
2. `bull_low_vol`: 상승 추세 + 낮은 변동성
3. `bear_high_vol`: 하락 추세 + 높은 변동성
4. `bear_low_vol`: 하락 추세 + 낮은 변동성
5. `range_high_vol`: 횡보 + 높은 변동성
6. `range_low_vol`: 횡보 + 낮은 변동성

### 2.2 Regime Detection 지표

#### 지표 1: ADX (Trend Strength)
```python
# ADX 기반 추세 강도 측정
adx_period = 14  # 고정
adx = calculate_adx(df, period=adx_period)

# Threshold (tunable)
adx_trend_threshold = config.get('adx_trend_threshold', 25)  # 기본 25

if adx >= adx_trend_threshold:
    trend_type = "TREND"  # 추세 강함
else:
    trend_type = "RANGE"  # 횡보
```

#### 지표 2: DI+ / DI- (Trend Direction)
```python
# ADX와 함께 계산되는 Directional Indicators
di_plus = df['di_plus_14']  # +DI
di_minus = df['di_minus_14']  # -DI

# 추세 방향 판정
if trend_type == "TREND":
    if di_plus > di_minus:
        trend_direction = "BULL"
    else:
        trend_direction = "BEAR"
else:
    # Range에서도 약한 bias 파악
    di_diff = di_plus - di_minus
    if di_diff > 5:  # Threshold tunable
        trend_direction = "BULL"
    elif di_diff < -5:
        trend_direction = "BEAR"
    else:
        trend_direction = "RANGE"
```

#### 지표 3: ATR (Volatility Level)
```python
# ATR 기반 변동성 측정
atr_period = 14  # 고정
atr = calculate_atr(df, period=atr_period)
atr_pct = atr / price  # 가격 대비 ATR 비율

# ATR percentile 기반 변동성 분류
atr_percentile = percentile_rank(atr_pct, lookback=100)  # 최근 100바 기준

# Threshold (tunable)
atr_high_threshold = config.get('atr_high_threshold', 70)  # 기본 70% (상위 30%)

if atr_percentile >= atr_high_threshold:
    volatility = "HIGH"
else:
    volatility = "LOW"
```

#### 지표 4: Volume (확인용, Optional)
```python
# Volume 기반 추가 검증 (Optional)
volume_ma = df['volume'].rolling(20).mean()
volume_ratio = df['volume'] / volume_ma

volume_high_threshold = config.get('volume_high_threshold', 1.5)  # 기본 1.5x

if volume_ratio > volume_high_threshold:
    volume_confirmation = True  # 거래량 급증 확인
else:
    volume_confirmation = False
```

### 2.3 Regime 판정 로직

```python
def detect_regime(df: pd.DataFrame, config: dict) -> str:
    """
    6-state Regime Detection
    
    Returns:
        regime: 'bull_high_vol' | 'bull_low_vol' | 'bear_high_vol' | 
                'bear_low_vol' | 'range_high_vol' | 'range_low_vol'
    """
    # 1. Trend Direction (ADX + DI+/DI-)
    adx = float(df.iloc[-1]['adx_14'])
    di_plus = float(df.iloc[-1]['di_plus_14'])
    di_minus = float(df.iloc[-1]['di_minus_14'])
    
    adx_trend_threshold = config.get('adx_trend_threshold', 25)
    di_diff_threshold = config.get('di_diff_threshold', 5)
    
    if adx >= adx_trend_threshold:
        # Strong Trend
        if di_plus > di_minus:
            trend = "bull"
        else:
            trend = "bear"
    else:
        # Range or Weak Trend
        di_diff = di_plus - di_minus
        if di_diff > di_diff_threshold:
            trend = "bull"
        elif di_diff < -di_diff_threshold:
            trend = "bear"
        else:
            trend = "range"
    
    # 2. Volatility Level (ATR percentile)
    atr = float(df.iloc[-1]['atr_14'])
    price = float(df.iloc[-1]['close'])
    atr_pct = atr / price
    
    # ATR percentile (최근 100바 기준)
    atr_pct_series = df['atr_14'] / df['close']
    atr_percentile = percentile_rank(atr_pct_series.iloc[-100:], atr_pct)
    
    atr_high_threshold = config.get('atr_high_threshold', 70)
    
    if atr_percentile >= atr_high_threshold:
        volatility = "high_vol"
    else:
        volatility = "low_vol"
    
    # 3. Regime 조합
    regime = f"{trend}_{volatility}"
    
    return regime


def percentile_rank(series: pd.Series, value: float) -> float:
    """시리즈에서 value의 percentile 순위 계산"""
    return (series < value).sum() / len(series) * 100
```

### 2.4 Regime별 특성 및 전략 방향

| Regime | 특성 | 전략 방향 | 진입 Bias |
|--------|------|-----------|-----------|
| **bull_high_vol** | 상승 추세 + 높은 변동성 | 추세 추종 + 돌파 | Long 70%, Short 30% |
| **bull_low_vol** | 상승 추세 + 낮은 변동성 | 조정 매수 + Mean Reversion | Long 60%, Short 40% |
| **bear_high_vol** | 하락 추세 + 높은 변동성 | 추세 추종 + 돌파 | Long 30%, Short 70% |
| **bear_low_vol** | 하락 추세 + 낮은 변동성 | 반등 매도 + Mean Reversion | Long 40%, Short 60% |
| **range_high_vol** | 횡보 + 높은 변동성 | 경계 거래 + 빠른 익절 | Long 50%, Short 50% |
| **range_low_vol** | 횡보 + 낮은 변동성 | Mean Reversion | Long 50%, Short 50% |

---

## 📊 Section 3: Dynamic Threshold 설계

### 3.1 RSI Dynamic Threshold

#### V1 문제점
```python
# 고정 threshold
rsi_long_threshold = 45  # 모든 상황에서 동일
rsi_short_threshold = 55
```

**문제**: Bull Trend에서는 RSI 평균 60+ → RSI < 45는 거의 발생 안함

#### V2 해결 방안
```python
def get_rsi_threshold(df: pd.DataFrame, config: dict, regime: str) -> tuple:
    """
    Regime별 Dynamic RSI Threshold 계산
    
    Returns:
        (long_threshold, short_threshold)
    """
    rsi = df['rsi'].iloc[-100:]  # 최근 100바
    
    # Regime별 Percentile 설정
    regime_percentiles = {
        'bull_high_vol': (30, 75),   # Long 30% / Short 75%
        'bull_low_vol': (25, 70),
        'bear_high_vol': (25, 70),
        'bear_low_vol': (30, 75),
        'range_high_vol': (20, 80),
        'range_low_vol': (20, 80),
    }
    
    long_pct, short_pct = regime_percentiles.get(regime, (20, 80))
    
    # Rolling Percentile 계산
    rsi_long_threshold = rsi.quantile(long_pct / 100.0)
    rsi_short_threshold = rsi.quantile(short_pct / 100.0)
    
    # Min/Max Clipping (극단값 방지)
    rsi_long_threshold = max(25, min(50, rsi_long_threshold))
    rsi_short_threshold = max(50, min(75, rsi_short_threshold))
    
    return rsi_long_threshold, rsi_short_threshold
```

**효과**:
- Bull Trend: RSI 평균 60+ → threshold 자동 상향 (예: 35/70)
- Bear Trend: RSI 평균 40- → threshold 자동 하향 (예: 30/55)
- Range: RSI 평균 50 → threshold 중립 (예: 45/55)

### 3.2 Bollinger Bands Dynamic Threshold

#### V1 문제점
```python
# 고정 std multiplier
bb_std_main = 1.0  # 모든 상황에서 동일
bb_std_strong = 1.5
```

**문제**: High Volatility에서는 BB 폭이 넓어져 1.0 std로도 닿지 않음

#### V2 해결 방안
```python
def get_bb_threshold(df: pd.DataFrame, config: dict, regime: str) -> tuple:
    """
    Regime + Volatility 기반 Dynamic BB Threshold 계산
    
    Returns:
        (bb_mult_main, bb_mult_strong)
    """
    atr = df['atr_14'].iloc[-1]
    price = df['close'].iloc[-1]
    atr_pct = atr / price
    
    # Regime별 Base Multiplier
    regime_bb_base = {
        'bull_high_vol': (0.7, 1.3),   # 변동성 높음 → 낮은 std
        'bull_low_vol': (0.9, 1.5),
        'bear_high_vol': (0.7, 1.3),
        'bear_low_vol': (0.9, 1.5),
        'range_high_vol': (0.8, 1.4),
        'range_low_vol': (1.0, 1.7),   # 변동성 낮음 → 높은 std
    }
    
    base_main, base_strong = regime_bb_base.get(regime, (1.0, 1.5))
    
    # ATR 기반 조정 (Optional)
    # 변동성이 극단적으로 높으면 더 낮은 std 사용
    atr_adjustment = max(0.8, min(1.2, 0.002 / atr_pct))  # 0.2% 기준
    
    bb_mult_main = base_main * atr_adjustment
    bb_mult_strong = base_strong * atr_adjustment
    
    # Min/Max Clipping
    bb_mult_main = max(0.5, min(1.5, bb_mult_main))
    bb_mult_strong = max(1.0, min(2.5, bb_mult_strong))
    
    return bb_mult_main, bb_mult_strong
```

**효과**:
- High Volatility: BB std 낮춤 (0.7-1.3) → 진입 기회 증가
- Low Volatility: BB std 높임 (1.0-1.7) → 극단적 조건에만 진입
- ATR 기반 추가 조정 → 시장 상태 변화에 즉시 대응

### 3.3 Momentum Threshold (Optional)

```python
def get_momentum_threshold(df: pd.DataFrame, config: dict, regime: str) -> float:
    """
    Regime별 Dynamic Momentum Threshold
    
    Returns:
        momentum_threshold (변화율 %)
    """
    # Regime별 Base Threshold
    regime_momentum = {
        'bull_high_vol': 0.002,   # 0.2% (높은 변동성 → 높은 threshold)
        'bull_low_vol': 0.001,    # 0.1%
        'bear_high_vol': 0.002,
        'bear_low_vol': 0.001,
        'range_high_vol': 0.0015,
        'range_low_vol': 0.0008,  # 0.08% (낮은 변동성 → 낮은 threshold)
    }
    
    return regime_momentum.get(regime, 0.001)
```

---

## 🎯 Section 4: Regime별 신호 로직 (V2)

### 4.1 Bull Trend 신호 로직

#### 4.1.1 bull_high_vol (상승 추세 + 높은 변동성)
**전략 방향**: 추세 추종 + 돌파  
**포지션 Bias**: Long 70%, Short 30%

```python
# LONG 진입 (공격적)
LONG 조건 (OR 로직):
  1. Price < BB Lower (0.7 std) AND RSI < percentile(30)
     # 급격한 조정 후 반등 포착
  
  2. (Price < BB Middle) AND (RSI < percentile(30)) AND (최근 3바 상승 모멘텀)
     # 중간선 근처 조정 + 반등 모멘텀
  
  3. DI+ > DI- + 10 AND Volume > 1.5x MA
     # 강한 상승 신호 + 거래량 확인

# SHORT 진입 (매우 보수적)
SHORT 조건 (OR 로직):
  1. Price > BB Upper (1.3 std) AND RSI > percentile(90)
     # 극단적 과열만 진입 (조정 대기)
  
  2. (DI+ < DI-) AND (ADX > 30) AND (RSI > percentile(80))
     # 추세 반전 초기 신호 (매우 드묾)
```

#### 4.1.2 bull_low_vol (상승 추세 + 낮은 변동성)
**전략 방향**: 조정 매수 + Mean Reversion  
**포지션 Bias**: Long 60%, Short 40%

```python
# LONG 진입 (중립)
LONG 조건 (OR 로직):
  1. RSI < percentile(25) OR Price < BB Lower (0.9 std)
     # 조정 구간 매수
  
  2. (Price < BB Middle) AND (최근 5바 -0.1% 이상 하락)
     # 중간선 근처 조정 매수
  
  3. (RSI 45-50) AND (Price 매도벽 돌파 + Volume 1.2x)
     # 지지선 돌파 매수 (추세 지속 기대)

# SHORT 진입 (보수적)
SHORT 조건 (OR 로직):
  1. RSI > percentile(75) AND Price > BB Upper (1.5 std)
     # 과열 구간 조정 대기
  
  2. (DI+ 약화) AND (RSI > 65)
     # 추세 약화 신호
```

### 4.2 Bear Trend 신호 로직

#### 4.2.1 bear_high_vol (하락 추세 + 높은 변동성)
**전략 방향**: 추세 추종 + 돌파  
**포지션 Bias**: Long 30%, Short 70%

```python
# LONG 진입 (매우 보수적)
LONG 조건 (OR 로직):
  1. Price < BB Lower (1.3 std) AND RSI < percentile(10)
     # 극단적 과매도만 진입 (반등 대기)
  
  2. (DI+ > DI-) AND (ADX > 30) AND (RSI < percentile(20))
     # 추세 반전 초기 신호 (매우 드묾)

# SHORT 진입 (공격적)
SHORT 조건 (OR 로직):
  1. Price > BB Upper (0.7 std) AND RSI > percentile(70)
     # 급격한 반등 후 조정 포착
  
  2. (Price > BB Middle) AND (RSI > percentile(70)) AND (최근 3바 하락 모멘텀)
     # 중간선 근처 반등 + 하락 모멘텀
  
  3. DI- > DI+ + 10 AND Volume > 1.5x MA
     # 강한 하락 신호 + 거래량 확인
```

#### 4.2.2 bear_low_vol (하락 추세 + 낮은 변동성)
**전략 방향**: 반등 매도 + Mean Reversion  
**포지션 Bias**: Long 40%, Short 60%

```python
# LONG 진입 (보수적)
LONG 조건 (OR 로직):
  1. RSI < percentile(25) AND Price < BB Lower (1.5 std)
     # 극단적 과매도 + 반등 대기
  
  2. (DI+ > DI-) AND (RSI < 35)
     # 추세 약화 신호

# SHORT 진입 (중립)
SHORT 조건 (OR 로직):
  1. RSI > percentile(75) OR Price > BB Upper (0.9 std)
     # 반등 구간 매도
  
  2. (Price > BB Middle) AND (최근 5바 +0.1% 이상 상승)
     # 중간선 근처 반등 매도
  
  3. (RSI 50-55) AND (Price 저항선 돌파 실패 + Volume 1.2x)
     # 저항선 실패 매도 (추세 지속 기대)
```

### 4.3 Range 신호 로직

#### 4.3.1 range_high_vol (횡보 + 높은 변동성)
**전략 방향**: 경계 거래 + 빠른 익절  
**포지션 Bias**: Long 50%, Short 50%

```python
# LONG 진입
LONG 조건 (OR 로직):
  1. Price < BB Lower (0.8 std) AND RSI < percentile(20)
     # 하단 경계 매수
  
  2. (Price 상승 전환) AND (RSI < 45) AND (Volume > 1.3x)
     # 하단 반등 확인 매수

# SHORT 진입
SHORT 조건 (OR 로직):
  1. Price > BB Upper (0.8 std) AND RSI > percentile(80)
     # 상단 경계 매도
  
  2. (Price 하락 전환) AND (RSI > 55) AND (Volume > 1.3x)
     # 상단 조정 확인 매도
```

#### 4.3.2 range_low_vol (횡보 + 낮은 변동성)
**전략 방향**: Mean Reversion (V1 로직 유사)  
**포지션 Bias**: Long 50%, Short 50%

```python
# LONG 진입 (V1과 유사, 하지만 Dynamic Threshold)
LONG 조건 (OR 로직):
  1. RSI < percentile(20) OR Price < BB Lower (1.0 std)
  
  2. (Price < BB Lower (0.8 std)) AND (최근 5바 -0.05% 이상 하락)
  
  3. Price < BB Lower (1.7 std)  # 극단적 조건

# SHORT 진입 (대칭)
SHORT 조건 (OR 로직):
  1. RSI > percentile(80) OR Price > BB Upper (1.0 std)
  
  2. (Price > BB Upper (0.8 std)) AND (최근 5바 +0.05% 이상 상승)
  
  3. Price > BB Upper (1.7 std)  # 극단적 조건
```

### 4.4 공통 필터 (모든 Regime)

```python
# 진입 전 공통 검증
def validate_entry(signal, df, config):
    """
    모든 진입 신호에 공통 적용되는 필터
    """
    # 1. ATR 최소 조건 (변동성 너무 낮으면 진입 금지)
    atr_pct = df['atr_14'].iloc[-1] / df['close'].iloc[-1]
    if atr_pct < 0.0005:  # 0.05% 미만
        return False
    
    # 2. 최근 N바 내 동일 방향 신호 중복 방지 (Optional)
    # (구현 생략)
    
    # 3. Risk Manager 검증 (기존 시스템 재사용)
    if not risk_manager.check_entry_allowed(signal):
        return False
    
    return True
```

---

## 🔧 Section 5: ParamSpace V2 설계

### 5.1 V1 ParamSpace 문제점

```yaml
# V1 ParamSpace (너무 협소)
rsi_long_threshold: 40-48   # 범위: 8
rsi_short_threshold: 52-58  # 범위: 6
bb_std_main: 0.9-1.2        # 범위: 0.3
bb_std_strong: 1.3-1.6      # 범위: 0.3
```

**문제**: 
- Bull Trend에서는 RSI 평균 60+ → ParamSpace 밖
- 공격적 진입 옵션 없음 (BB 0.5-0.8 탐색 안됨)

### 5.2 V2 ParamSpace 설계

#### 전체 ParamSpace (Regime-Independent)
```yaml
# ========================================
# btc5m_baseline_v2 Tuning Parameter Space
# ========================================

param_space:
  # ===== Regime Detection =====
  adx_period:
    type: categorical
    values: [14]  # 고정 (표준 ADX)
    description: "ADX 계산 기간"
  
  adx_trend_threshold:
    type: int
    min: 20
    max: 30
    description: "Trend vs Range 분류 ADX threshold"
    baseline: 25
  
  di_diff_threshold:
    type: int
    min: 3
    max: 10
    description: "DI+/DI- 차이 threshold (방향 판정)"
    baseline: 5
  
  atr_high_threshold:
    type: int
    min: 60
    max: 80
    description: "High Volatility percentile threshold"
    baseline: 70
  
  # ===== Dynamic Threshold Base (Regime별로 곱해질 Base 값) =====
  
  # RSI Percentile (Regime별로 다르게 적용)
  rsi_long_percentile_base:
    type: int
    min: 15
    max: 35
    description: "LONG RSI percentile base (Regime에 따라 조정)"
    baseline: 25
  
  rsi_short_percentile_base:
    type: int
    min: 65
    max: 85
    description: "SHORT RSI percentile base (Regime에 따라 조정)"
    baseline: 75
  
  # BB Multiplier Base
  bb_mult_main_base:
    type: float
    min: 0.5
    max: 1.2
    description: "BB Main 진입 multiplier base"
    baseline: 0.8
  
  bb_mult_strong_base:
    type: float
    min: 1.0
    max: 2.0
    description: "BB Strong 진입 multiplier base"
    baseline: 1.5
  
  # ===== Regime Adjustment Factors =====
  # (각 Regime별로 Base 값에 곱해질 Factor)
  
  bull_rsi_adjustment:
    type: float
    min: 1.0
    max: 1.5
    description: "Bull Trend에서 RSI threshold 조정 비율"
    baseline: 1.2  # 20% 상향
  
  bear_rsi_adjustment:
    type: float
    min: 0.7
    max: 1.0
    description: "Bear Trend에서 RSI threshold 조정 비율"
    baseline: 0.85  # 15% 하향
  
  high_vol_bb_adjustment:
    type: float
    min: 0.7
    max: 1.0
    description: "High Volatility에서 BB multiplier 조정 비율"
    baseline: 0.85  # 15% 낮춤 (진입 쉽게)
  
  low_vol_bb_adjustment:
    type: float
    min: 1.0
    max: 1.3
    description: "Low Volatility에서 BB multiplier 조정 비율"
    baseline: 1.15  # 15% 높임 (진입 어렵게)
  
  # ===== Momentum =====
  momentum_lookback:
    type: categorical
    values: [3, 5, 7, 10]
    description: "Momentum 계산 lookback 캔들 수"
    baseline: 5
  
  momentum_threshold_base:
    type: float
    min: 0.0003
    max: 0.003
    description: "Momentum 변화율 threshold base (Regime 조정 전)"
    baseline: 0.001
  
  # ===== Risk Management =====
  atr_mult_sl:
    type: float
    min: 1.0
    max: 2.5
    description: "Stop Loss 배수 (ATR 기준)"
    baseline: 1.5
  
  rr:
    type: float
    min: 0.8
    max: 3.0
    description: "Risk-Reward ratio"
    baseline: 1.5
  
  # ===== Time Exit =====
  max_hold_minutes:
    type: categorical
    values: [30, 45, 60, 90, 120]
    description: "최대 보유 시간 (분)"
    baseline: 60
  
  # ===== Position Bias (Regime별 Long/Short 비율) =====
  bull_long_bias:
    type: float
    min: 0.55
    max: 0.75
    description: "Bull Trend에서 LONG 포지션 비율"
    baseline: 0.65  # 65% LONG, 35% SHORT
  
  bear_short_bias:
    type: float
    min: 0.55
    max: 0.75
    description: "Bear Trend에서 SHORT 포지션 비율"
    baseline: 0.65
```

**ParamSpace 크기**:
- V1: ~10 parameters, 범위 협소
- V2: ~20 parameters, 범위 2-3배 확장
- 탐색 공간: 10^8 → 10^12 (약 10,000배 증가)

### 5.3 Regime별 실제 Threshold 계산 예시

```python
# 예시: Bull High Vol에서 RSI Long Threshold 계산
rsi_long_percentile_base = 25  # ParamSpace에서 샘플링
bull_rsi_adjustment = 1.2  # ParamSpace에서 샘플링

# Bull Trend 조정
rsi_long_percentile = rsi_long_percentile_base * bull_rsi_adjustment
# = 25 * 1.2 = 30

# Rolling Percentile 계산
rsi_series = df['rsi'].iloc[-100:]
rsi_long_threshold = rsi_series.quantile(0.30)  # 30% percentile

# 예: Bull 구간에서 RSI 평균이 60이면
# → 30% percentile ≈ 54
# → 기존 V1 (45)보다 높은 threshold → 진입 기회 증가
```

---

## 🧪 Section 6: Implementation Plan

### 6.1 파일 구조

```
strategies/
  btc5m_baseline_v2.py          # 메인 전략 코드
  
  utils/
    regime_detector.py          # Regime Detection 모듈
    dynamic_threshold.py        # Dynamic Threshold 계산 모듈

configs/tuning/
  phase28_6_btc5m_baseline_v2_paramspace.yml  # ParamSpace V2

tests/strategies/
  test_btc5m_baseline_v2.py     # 단위 테스트
  test_regime_detector.py
  test_dynamic_threshold.py
```

### 6.2 구현 순서

#### Phase 1: Core Modules (PHASE28-7)
1. ✅ `strategies/utils/regime_detector.py`:
   - `detect_regime(df, config)` 구현
   - 6-state 분류 로직
   - ADX/DI+/DI-/ATR 계산 통합

2. ✅ `strategies/utils/dynamic_threshold.py`:
   - `get_rsi_threshold(df, config, regime)` 구현
   - `get_bb_threshold(df, config, regime)` 구현
   - `get_momentum_threshold(df, config, regime)` 구현

3. ✅ `strategies/btc5m_baseline_v2.py`:
   - `signal_logic(df, config)` 재설계
   - Regime Detection → Dynamic Threshold → 신호 판정 흐름
   - V1 인터페이스 호환 유지 (BaseStrategy)

#### Phase 2: Testing (PHASE28-7)
4. ✅ Unit Tests:
   - `test_regime_detector.py`: 6-state 분류 정확도 검증
   - `test_dynamic_threshold.py`: Threshold 계산 검증
   - `test_btc5m_baseline_v2.py`: 전체 signal_logic 검증

5. ✅ Integration Test:
   - Smoke Test: Base 파라미터로 30일 백테스트 (Trade Count ≥ 10 확인)
   - ParamSpace Boundary Test: 경계값에서도 정상 작동 확인

#### Phase 3: Multi-Period Validation (PHASE28-8)
6. ✅ Period별 Baseline 검증:
   - Bull (2024-10): Baseline 파라미터로 백테스트 → Sharpe ≥ 0 확인
   - Bear (2024-08): 동일
   - Range (2024-11): 동일

7. ✅ Light Tuning (Optional):
   - Random Search 10-20 trials per period
   - 각 구간별 "생존 가능 파라미터 대역" 도출
   - 앙상블 프레임워크에서 Regime별 파라미터 전환에 활용

---

## 📝 Section 7: Acceptance Criteria (PHASE28-7)

### AC1: Code Implementation
- ✅ `strategies/btc5m_baseline_v2.py` 구현 완료
- ✅ `strategies/utils/regime_detector.py` 구현 완료
- ✅ `strategies/utils/dynamic_threshold.py` 구현 완료
- ✅ `configs/tuning/phase28_6_btc5m_baseline_v2_paramspace.yml` 작성 완료

### AC2: Unit Tests Pass
- ✅ `pytest tests/strategies/test_btc5m_baseline_v2.py` 통과
- ✅ `pytest tests/strategies/test_regime_detector.py` 통과
- ✅ `pytest tests/strategies/test_dynamic_threshold.py` 통과
- ✅ 테스트 커버리지 ≥ 80%

### AC3: Smoke Test Pass
- ✅ Baseline 파라미터로 30일 백테스트 실행
- ✅ Trade Count ≥ 20 (현재 5개 대비 4배 증가)
- ✅ No ERROR/CRITICAL logs
- ✅ DB 정상 연동 (trades/decisions 저장)

### AC4: Regime Detection Validation
- ✅ 6-state 분류가 실제 데이터에서 의미있게 작동
- ✅ 각 Regime별로 최소 10% 이상 발생 (모든 상태 커버)
- ✅ Regime 전환 시점이 육안으로 합리적

### AC5: Documentation
- ✅ `PHASE28-6_STRATEGY_REDESIGN_SPEC.md` (이 문서) 작성 완료
- ✅ `PHASE28-7_IMPLEMENTATION_REPORT.md` 작성 (구현 후)
- ✅ 코드 주석 작성 (docstring, inline comments)

---

## 🎯 Section 8: Success Metrics (PHASE28-8 목표)

### Minimum Viable Performance (최소 생존 수준)

| Metric | V1 실제 | V2 Target (MVP) |
|--------|---------|-----------------|
| **Trade Count** | 5 per month | **≥ 20 per month** |
| **Sharpe Ratio (Bull)** | -1.0 | **≥ 0.0** |
| **Sharpe Ratio (Bear)** | N/A (미검증) | **≥ 0.0** |
| **Sharpe Ratio (Range)** | +0.75 (1 trial) | **≥ 0.0 (일관성)** |
| **Win Rate** | 0% (대부분) | **≥ 40%** |
| **Max Drawdown** | 200-400% | **≤ 20%** |

### Stretch Goals (이상적 수준, PHASE28-8 이후)

| Metric | Target |
|--------|--------|
| **Sharpe Ratio (All Periods)** | ≥ 0.5 |
| **Win Rate** | ≥ 50% |
| **Trade Count** | 30-50 per month |
| **Max Drawdown** | ≤ 15% |
| **Profit Factor** | ≥ 1.2 |

---

## 🚀 Section 9: Next Steps

### Immediate (PHASE28-7)
1. ✅ Skeleton Code 작성 (`btc5m_baseline_v2.py` + utils)
2. ✅ Unit Tests 작성
3. ✅ Smoke Test 실행 (Baseline 파라미터)
4. ✅ 문서화 (`PHASE28-7_IMPLEMENTATION_REPORT.md`)

### Short-term (PHASE28-8)
5. ✅ Multi-Period Validation (Bull/Bear/Range 독립 백테스트)
6. ✅ Light Tuning (Random Search 10-20 trials per period)
7. ✅ "생존 가능 파라미터 대역" 도출
8. ✅ 문서화 (`PHASE28-8_VALIDATION_REPORT.md`)

### Medium-term (PHASE29+)
9. 앙상블 프레임워크 복구 (PHASE19)
10. Regime별 파라미터 동적 전환
11. 멀티 심볼 확장 (Top N symbols)
12. Live Trading 준비

---

## 📚 References

### 설계 근거 문서
- `docs/PHASE28/PHASE28-6_POSTMORTEM_ANALYSIS.md` (V1 실패 원인 분석)
- `docs/PHASE28/PHASE28-3_RESULTS.md` (Random Search 결과)
- `docs/PHASE28/PHASE28-4_BAYESIAN_SEARCH_ROUND1_RESULTS.md` (Bayesian 결과)
- `docs/PHASE28/PHASE28-5_LOCAL_GRID_SEARCH_ROUND1_RESULTS.md` (Local Grid 결과)

### 기존 코드
- `strategies/btc5m_baseline_v1.py` (V1 전략 코드)
- `configs/tuning/phase28_2_btc5m_baseline_paramspace.yml` (V1 ParamSpace)

### 튜닝 인프라
- `tuning/algorithms/random_search.py`
- `tuning/algorithms/bayesian_search.py`
- `tuning/algorithms/local_grid_search.py`

---

## 🏁 Final Statement

**btc5m_baseline_v2는 V1의 근본적 결함을 해결하기 위한 전면 재설계입니다.**

**핵심 변경**:
1. ✅ Regime Detection 강화 (6-state: Bull/Bear/Range × High/Low Vol)
2. ✅ Dynamic Threshold 도입 (고정값 → Rolling percentile + Volatility 조정)
3. ✅ Regime별 Threshold 분리 (Bull/Bear/Range 각각 다른 진입 조건)
4. ✅ ParamSpace 대폭 확장 (탐색 공간 10,000배 증가)

**목표**:
- **최소 생존 수준 (MVP)**: Sharpe ≥ 0 (모든 Period), Trade Count ≥ 20
- **이상적 수준**: Sharpe ≥ 0.5, Win Rate ≥ 50%, Trade Count 30-50

**다음 단계**:
- PHASE28-7: 구현 + 단위 테스트 + Smoke Test
- PHASE28-8: Multi-Period Validation + Light Tuning

**이 설계가 실패하면**: 전략 패밀리 자체를 변경 (Mean Reversion → Trend Following / Breakout)

---

**End of Strategy Redesign Specification**

*이 문서는 2025-12-07 AI Development Agent에 의해 작성되었습니다.*
*V2 설계: PHASE28-6*
