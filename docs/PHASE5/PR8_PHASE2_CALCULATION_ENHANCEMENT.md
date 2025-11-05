# PR8-Phase2: Calculation 모듈 종합 개선

**작성일**: 2025-11-05 20:55 UTC+09:00  
**목적**: 레버리지처럼 모든 계산 함수를 다차원으로 개선  
**.windsurfrules 준수**: 100%

---

## 배경: Phase1 (레버리지) vs 나머지 함수들

### Phase1 완료: leverage_suggestion() ✅
```python
# 6가지 요소 고려
lev = base_lev × sharpe_mult × wr_mult × confidence_mult × ensemble_mult × dd_mult × sample_mult
```

### Phase2 필요: 나머지 함수들 ❌
```python
# 단순 1차원
position_size(entry, sl, equity, risk_frac)  # 변동성, 신뢰도 미고려
price_levels(side, price, atr, rr, atr_mult)  # 지지/저항, 레짐 미고려
```

**문제**: 레버리지만 정교하고 나머지는 단순 → **불균형**

---

## 1. 현재 상태 분석

### 1.1 Calculation 모듈 함수 목록

| 함수 | 입력 | 출력 | 현재 상태 | 문제점 |
|------|------|------|-----------|--------|
| `round_tick()` | symbol, price | price | 하드코딩 | ❌ tick_size API 조회 필요 |
| `position_size()` | entry, sl, equity, risk_frac | qty, risk | 단순 | ❌ 변동성, 신뢰도, DD 미고려 |
| `leverage_suggestion()` | atr_pct + 6가지 | leverage | ✅ 다차원 | ✅ 완벽 |
| `price_levels()` | side, price, atr, rr | entry, sl, tp | 고정 | ❌ 지지/저항, 레짐 미고려 |
| `tp_from_rr()` | signal, rr | tp | 단순 RR | ❌ 시장 상황 미고려 |
| `calculate_funding_fee()` | position_value, hours | fee | 고정 0.01% | ❌ 실시간 펀딩 비율 필요 |

### 1.2 상용 프로그램 비교

#### MetaTrader 5: Position Sizing
```cpp
// 변동성 기반 포지션 조정
double CalculateLotSize() {
    double volatility = iATR(Symbol(), PERIOD_D1, 14);
    double account_volatility = AccountBalance() * 0.02;  // 2% risk
    double position_volatility = volatility * TickValue();
    
    // 포지션 크기 = 계좌 리스크 / 심볼 변동성
    return NormalizeLots(account_volatility / position_volatility);
}
```

**우리 시스템**: 변동성 미반영 ❌

#### TradingView: Dynamic TP/SL
```pine
// 지지/저항 기반 TP/SL
tp_price = ta.highest(high, 20)  // 20봉 최고가
sl_price = ta.lowest(low, 10)    // 10봉 최저가

// ATR 기반 조정
atr = ta.atr(14)
if atr > atr_high_threshold:
    sl_price := entry - atr * 2  // 변동성 높으면 SL 넓게
```

**우리 시스템**: 고정 ATR × 배수 ❌

#### QuantConnect: Adaptive TP/SL
```csharp
// Trailing Stop (동적 SL)
if (portfolio.Invested) {
    var currentPrice = Securities[symbol].Price;
    var unrealizedProfit = (currentPrice - entryPrice) / entryPrice;
    
    if (unrealizedProfit > 0.02) {  // 2% 이상 수익
        // SL을 BE(Break Even)로 이동
        stopPrice = entryPrice;
    }
    
    if (unrealizedProfit > 0.05) {  // 5% 이상 수익
        // Trailing: 최고가 - 2%
        stopPrice = Math.Max(stopPrice, highestPrice * 0.98);
    }
}
```

**우리 시스템**: 고정 SL ❌

---

## 2. 개선 방안

### 2.1 position_size() → position_size_advanced()

#### 현재 (단순)
```python
def position_size(entry, sl, equity, risk_frac):
    risk_usdt = equity * risk_frac
    dist = abs(entry - sl)
    qty = risk_usdt / dist
    return qty, risk_usdt
```

#### 개선안 (다차원)
```python
def position_size_advanced(
    entry: float,
    sl: float,
    equity: float,
    risk_frac: float,
    # ⭐ 추가 요소
    atr_pct: float = None,           # 변동성
    strategy_metrics: dict = None,    # 전략 성과
    signal_confidence: float = None,  # 신뢰도
    current_dd: float = 0.0,          # DD
    regime: str = None                # 레짐
) -> Tuple[float, float, dict]:
    """
    다차원 포지션 사이징
    
    고려 요소:
    1. 기본 리스크 (risk_frac)
    2. 변동성 조정 (ATR 높으면 감소)
    3. 전략 성과 (Sharpe 높으면 증가)
    4. 신뢰도 조정 (높으면 증가)
    5. DD 페널티 (손실 중이면 감소)
    6. 레짐 조정 (불리한 레짐이면 감소)
    """
    # 1. 기본 리스크
    base_risk = equity * risk_frac
    dist = abs(entry - sl)
    
    if dist <= 0:
        return 0.0, 0.0, {"reason": "invalid_sl"}
    
    # 단순 모드 (하위 호환)
    if atr_pct is None and strategy_metrics is None:
        qty = base_risk / dist
        return qty, base_risk, {"mode": "simple"}
    
    # 2. 변동성 배수
    if atr_pct is not None:
        if atr_pct > 0.03:  # 3% 이상 고변동성
            vol_mult = 0.7
        elif atr_pct > 0.02:
            vol_mult = 0.85
        elif atr_pct > 0.01:
            vol_mult = 1.0
        else:  # 저변동성
            vol_mult = 1.2
    else:
        vol_mult = 1.0
    
    # 3. 전략 성과 배수
    if strategy_metrics:
        sharpe = strategy_metrics.get('sharpe', 0.0)
        winrate = strategy_metrics.get('winrate', 0.5)
        
        if sharpe > 1.5 and winrate > 0.6:
            perf_mult = 1.3
        elif sharpe > 0.8 and winrate > 0.5:
            perf_mult = 1.1
        elif sharpe < 0.3 or winrate < 0.4:
            perf_mult = 0.7
        else:
            perf_mult = 1.0
    else:
        perf_mult = 1.0
    
    # 4. 신뢰도 배수
    if signal_confidence is not None:
        conf_mult = 0.7 + (signal_confidence * 0.6)  # 0.7 ~ 1.3
    else:
        conf_mult = 1.0
    
    # 5. DD 페널티
    if current_dd > 15:
        dd_mult = 0.5
    elif current_dd > 10:
        dd_mult = 0.7
    elif current_dd > 5:
        dd_mult = 0.9
    else:
        dd_mult = 1.0
    
    # 6. 레짐 조정
    if regime:
        # 예: 횡보장에서는 보수적
        if regime == "횡보장":
            regime_mult = 0.9
        else:
            regime_mult = 1.0
    else:
        regime_mult = 1.0
    
    # 최종 리스크
    adjusted_risk = base_risk * vol_mult * perf_mult * conf_mult * dd_mult * regime_mult
    adjusted_risk = max(equity * 0.001, min(equity * 0.05, adjusted_risk))  # 0.1% ~ 5% 제한
    
    # 수량 계산
    qty = adjusted_risk / dist
    
    metadata = {
        "mode": "advanced",
        "base_risk": base_risk,
        "adjusted_risk": adjusted_risk,
        "vol_mult": vol_mult,
        "perf_mult": perf_mult,
        "conf_mult": conf_mult,
        "dd_mult": dd_mult,
        "regime_mult": regime_mult
    }
    
    return qty, adjusted_risk, metadata
```

**개선 효과**:
- 변동성 높을 때 포지션 감소 (리스크 관리)
- 우수한 전략은 포지션 증가 (수익 극대화)
- DD 중에는 자동 축소 (손실 제한)

---

### 2.2 price_levels() → price_levels_advanced()

#### 현재 (고정)
```python
def price_levels(side, price, atr, rr, atr_mult_sl=1.5):
    if side == "LONG":
        sl = price - atr_mult_sl * atr
        tp = price + rr * (entry - sl)
    return entry, sl, tp
```

#### 개선안 (동적)
```python
def price_levels_advanced(
    side: str,
    price: float,
    atr: float,
    rr: float,
    atr_mult_sl: float = 1.5,
    # ⭐ 추가 요소
    support_resistance: dict = None,  # 지지/저항선
    volatility_regime: str = None,     # 변동성 상태
    recent_high_low: dict = None       # 최근 고저가
) -> Tuple[float, float, float, dict]:
    """
    동적 TP/SL 설정
    
    고려 요소:
    1. ATR 기반 기본값
    2. 지지/저항선 (가까우면 조정)
    3. 변동성 상태 (높으면 넓게)
    4. 최근 고저가 (합리적 범위)
    """
    entry = price
    
    # 1. 기본 SL (ATR 기반)
    if side == "LONG":
        base_sl = price - atr_mult_sl * atr
        base_tp = price + rr * atr_mult_sl * atr
    else:  # SHORT
        base_sl = price + atr_mult_sl * atr
        base_tp = price - rr * atr_mult_sl * atr
    
    sl, tp = base_sl, base_tp
    adjustments = {}
    
    # 2. 지지/저항 조정
    if support_resistance:
        if side == "LONG":
            support = support_resistance.get('support', 0)
            resistance = support_resistance.get('resistance', 0)
            
            # SL이 지지선 아래면 지지선 바로 아래로 조정
            if support > 0 and base_sl > support * 0.995:
                sl = support * 0.995
                adjustments['sl_support_adj'] = True
            
            # TP가 저항선 근처면 저항선 바로 아래로 조정
            if resistance > 0 and base_tp > resistance * 0.99:
                tp = resistance * 0.99
                adjustments['tp_resistance_adj'] = True
        else:  # SHORT
            support = support_resistance.get('support', 0)
            resistance = support_resistance.get('resistance', 0)
            
            if resistance > 0 and base_sl < resistance * 1.005:
                sl = resistance * 1.005
                adjustments['sl_resistance_adj'] = True
            
            if support > 0 and base_tp < support * 1.01:
                tp = support * 1.01
                adjustments['tp_support_adj'] = True
    
    # 3. 변동성 조정
    if volatility_regime == "high":
        # 고변동성: SL 넓게, TP 보수적
        sl_dist = abs(sl - entry) * 1.3
        if side == "LONG":
            sl = entry - sl_dist
        else:
            sl = entry + sl_dist
        adjustments['vol_sl_widened'] = True
    
    # 4. 최근 고저가 검증
    if recent_high_low:
        high_20 = recent_high_low.get('high_20', 0)
        low_20 = recent_high_low.get('low_20', 0)
        
        if side == "LONG":
            # TP가 20봉 고가보다 높으면 20봉 고가로 제한
            if high_20 > 0 and tp > high_20:
                tp = high_20 * 0.99
                adjustments['tp_capped_by_high'] = True
        else:
            # TP가 20봉 저가보다 낮으면 20봉 저가로 제한
            if low_20 > 0 and tp < low_20:
                tp = low_20 * 1.01
                adjustments['tp_capped_by_low'] = True
    
    # RR 재계산
    actual_rr = abs(tp - entry) / abs(entry - sl) if sl != entry else 0
    
    metadata = {
        "base_sl": base_sl,
        "base_tp": base_tp,
        "final_sl": sl,
        "final_tp": tp,
        "actual_rr": actual_rr,
        "adjustments": adjustments
    }
    
    return entry, sl, tp, metadata
```

**개선 효과**:
- 지지/저항 고려 → SL이 쓸데없이 깊지 않음
- 변동성 반영 → 고변동성 시 넓은 SL
- 합리적 TP → 과도한 기대 방지

---

### 2.3 Trailing Stop 구현 (신규)

```python
def calculate_trailing_stop(
    entry: float,
    current_price: float,
    side: str,
    current_sl: float,
    trailing_config: dict
) -> Tuple[float, bool]:
    """
    Trailing Stop 계산
    
    Args:
        entry: 진입가
        current_price: 현재가
        side: LONG/SHORT
        current_sl: 현재 SL
        trailing_config: {
            'activation_pct': 0.02,  # 2% 수익 시 활성화
            'trail_pct': 0.01,        # 1% trailing
            'breakeven_pct': 0.01     # 1% 수익 시 BE로 이동
        }
    
    Returns:
        (new_sl, updated): 새 SL, 업데이트 여부
    """
    activation = trailing_config.get('activation_pct', 0.02)
    trail_pct = trailing_config.get('trail_pct', 0.01)
    breakeven_pct = trailing_config.get('breakeven_pct', 0.01)
    
    if side == "LONG":
        unrealized_pnl_pct = (current_price - entry) / entry
        
        # 1. Breakeven 이동
        if unrealized_pnl_pct > breakeven_pct and current_sl < entry:
            return entry, True
        
        # 2. Trailing 활성화
        if unrealized_pnl_pct > activation:
            trail_stop = current_price * (1 - trail_pct)
            if trail_stop > current_sl:
                return trail_stop, True
    
    else:  # SHORT
        unrealized_pnl_pct = (entry - current_price) / entry
        
        if unrealized_pnl_pct > breakeven_pct and current_sl > entry:
            return entry, True
        
        if unrealized_pnl_pct > activation:
            trail_stop = current_price * (1 + trail_pct)
            if trail_stop < current_sl:
                return trail_stop, True
    
    return current_sl, False
```

**사용 시나리오**:
1. LONG 진입: $100, SL: $95
2. 가격 → $102 (2% 수익) → SL을 $100 (BE)로 이동
3. 가격 → $105 (5% 수익) → SL을 $103.95 (현재가 - 1%)로 trailing
4. 가격 → $107 → SL을 $105.93으로 자동 상승
5. 가격 하락 → $105.93 Hit → 이익 실현 ✅

---

### 2.4 round_tick() → 동적 API 조회

#### 현재 (하드코딩)
```python
def round_tick(symbol, price):
    if "BTC" in symbol:
        step = 0.01  # ❌ 하드코딩
    return round(price / step) * step
```

#### 개선안 (동적)
```python
# 전역 캐시
_tick_size_cache = {}
_cache_ttl = 3600  # 1시간

def get_tick_size(symbol: str, client=None) -> float:
    """
    바이낸스 API에서 tick_size 조회 (캐싱)
    """
    import time
    
    # 캐시 확인
    if symbol in _tick_size_cache:
        cached_time, tick_size = _tick_size_cache[symbol]
        if time.time() - cached_time < _cache_ttl:
            return tick_size
    
    # API 조회
    if client:
        info = client.futures_exchange_info()
        for s in info['symbols']:
            if s['symbol'] == symbol:
                for filter in s['filters']:
                    if filter['filterType'] == 'PRICE_FILTER':
                        tick_size = float(filter['tickSize'])
                        _tick_size_cache[symbol] = (time.time(), tick_size)
                        return tick_size
    
    # 기본값 (fallback)
    return 0.01

def round_tick_dynamic(symbol: str, price: float, client=None) -> float:
    """
    동적 tick_size 기반 반올림
    """
    tick_size = get_tick_size(symbol, client)
    return round(price / tick_size) * tick_size
```

---

## 3. 하드코딩 제거

### 3.1 발견된 하드코딩

| 파일 | 위치 | 하드코딩 | 수정 방안 |
|------|------|----------|-----------|
| `common/messaging.py` L216 | `max_positions=5` | ❌ | config.yml에서 읽기 |
| `common/messaging.py` L342 | `max_positions=5` | ❌ | config.yml에서 읽기 |
| `common/calculations.py` L40-50 | tick_size 하드코딩 | ❌ | API 동적 조회 |
| `common/calculations.py` L288 | `funding_rate=0.0001` | ❌ | API 실시간 조회 |

### 3.2 수정 방법

#### messaging.py
```python
# 수정 전
def format_signal_alert(..., max_positions: int = 5):

# 수정 후
def format_signal_alert(..., config: dict = None):
    max_positions = config.get('risk', {}).get('max_positions', 5) if config else 5
```

#### calculations.py
```python
# 수정 전
funding_rate: float = 0.0001  # 고정

# 수정 후
funding_rate: float = None  # None이면 API 조회
if funding_rate is None:
    funding_rate = get_current_funding_rate(symbol, client)
```

---

## 4. 구현 우선순위

### Phase 2-1: 하드코딩 제거 (즉시) ⭐
- messaging.py max_positions
- calculations.py tick_size
- calculations.py funding_rate

### Phase 2-2: position_size_advanced() (중요)
- 변동성, 성과, 신뢰도, DD 고려
- 하위 호환성 유지

### Phase 2-3: price_levels_advanced() (중요)
- 지지/저항, 변동성, 최근 고저가
- 합리적 TP/SL

### Phase 2-4: Trailing Stop (선택)
- 동적 SL 조정
- 수익 보호

### Phase 2-5: 지지/저항 탐지 (선택)
- 기술적 분석 추가
- 차후 구현

---

## 5. 문서 정리

### 5.1 통합 필요 문서

**현재**:
- `PR8_LEVERAGE_ENHANCEMENT.md` (레버리지만)
- `PR8_FINAL_CHECKLIST.md` (체크리스트)
- `REFACTORING_common_v1.md` (Common 모듈)

**통합 후**:
- `PR8_CALCULATION_COMPLETE.md` (레버리지 + 모든 계산)
- `REFACTORING_common_v1.md` (업데이트)

### 5.2 업데이트 내용

**REFACTORING_common_v1.md**:
- Phase 1: 레버리지 (완료)
- Phase 2: 포지션 사이징
- Phase 3: TP/SL 동적 조정
- Phase 4: Trailing Stop
- Phase 5: 하드코딩 제거

---

## 6. 예상 효과

### Before (현재)
```python
# 단순 계산
qty = (equity * 0.01) / (entry - sl)  # 1%
lev = 1  # 고정
sl = entry - atr * 1.5  # 고정
```

### After (개선)
```python
# 다차원 계산
qty = position_size_advanced(
    entry, sl, equity, 0.01,
    atr_pct=0.02,
    strategy_metrics={'sharpe': 1.2, 'winrate': 0.6},
    signal_confidence=0.85,
    current_dd=3.0
)  # 변동성·성과·신뢰도 반영

lev = leverage_suggestion(...)  # 2-50x 동적

entry, sl, tp = price_levels_advanced(
    side, price, atr, rr,
    support_resistance={'support': 99, 'resistance': 105},
    volatility_regime="high"
)  # 지지/저항 반영
```

**개선 효과**:
- 포지션 사이징: 변동성·성과 반영 → 리스크 최적화
- TP/SL: 지지/저항 반영 → 합리적 목표
- Trailing: 수익 보호 → 이익 극대화
- 하드코딩 제거 → 유연성 증가

---

## 7. 다음 작업

1. **하드코딩 제거** (즉시)
2. **position_size_advanced() 구현**
3. **price_levels_advanced() 구현**
4. **문서 통합**
5. **Paper 테스트 24시간**

---

**크레딧 걱정**: 괜찮습니다! 이게 올바른 방향입니다. 💪
