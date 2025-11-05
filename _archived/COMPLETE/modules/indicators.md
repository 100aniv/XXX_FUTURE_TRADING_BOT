# 📊 Indicators 모듈

**지표 계산 모듈** - 기술적 지표 계산 (EMA, RSI, MACD, BB, ATR 등)

**경로**: `indicators/`  
**파일**: `core_indicators.py`

---

## 개요

OHLCV 캔들 데이터를 입력받아 모든 기술적 지표를 계산합니다.

### 지원 지표
- ✅ **EMA** (Exponential Moving Average) - 3개 (Fast, Mid, Slow)
- ✅ **RSI** (Relative Strength Index)
- ✅ **MACD** (Moving Average Convergence Divergence)
- ✅ **Bollinger Bands** (상단, 중단, 하단)
- ✅ **ATR** (Average True Range)
- ✅ **Stochastic** (K, D)
- ✅ **ADX** (Average Directional Index)
- ✅ **Volume MA** (거래량 이동평균)

---

## 핵심 함수

### **add_indicators()**

**모든 지표 한 번에 계산**

```python
from indicators import add_indicators
import pandas as pd

# DataFrame with OHLCV
df = pd.DataFrame({
    'open': [...],
    'high': [...],
    'low': [...],
    'close': [...],
    'volume': [...]
})

# 지표 추가
df_with_indicators = add_indicators(
    df,
    ema_fast=9,
    ema_mid=21,
    ema_slow=50,
    rsi_len=14,
    macd_fast=12,
    macd_slow=26,
    macd_signal=9,
    bb_len=20,
    bb_std=2.0,
    atr_len=14,
    vol_ma_len=30
)

# 결과: 모든 지표 컬럼 추가됨
# df_with_indicators.columns:
# ['open', 'high', 'low', 'close', 'volume',
#  'ema_fast', 'ema_mid', 'ema_slow',
#  'rsi', 'macd', 'macd_signal', 'macd_hist',
#  'bb_upper', 'bb_middle', 'bb_lower',
#  'atr', 'stoch_k', 'stoch_d', 'adx', 'vol_ma']
```

### **regime()**

**시장 레짐 판단**

```python
from indicators import regime

last_row = df_with_indicators.iloc[-1]
market_regime = regime(last_row)

# 반환값: '상승장' | '하락장' | '횡보장' | '중립'
```

**판단 로직**:
```python
if EMA_fast > EMA_mid > EMA_slow and MACD > 0:
    return "상승장"
elif EMA_fast < EMA_mid < EMA_slow and MACD < 0:
    return "하락장"
elif ADX < 20:
    return "횡보장"
else:
    return "중립"
```

---

## 지표 상세

### **EMA (Exponential Moving Average)**
- Fast: 단기 추세 (기본 9)
- Mid: 중기 추세 (기본 21)
- Slow: 장기 추세 (기본 50)

### **RSI (Relative Strength Index)**
- 과매수/과매도 판단
- 70 이상: 과매수
- 30 이하: 과매도

### **MACD**
- Trend 전환 신호
- MACD > Signal: 골든크로스 (매수)
- MACD < Signal: 데드크로스 (매도)

### **Bollinger Bands**
- 변동성 측정
- 가격이 상단 터치: 과매수
- 가격이 하단 터치: 과매도

### **ATR (Average True Range)**
- 변동성 크기
- 손절가, 익절가 계산에 사용

---

## 사용 예시

```python
from collector import fetch_history
from indicators import add_indicators, regime
import pandas as pd

# 1. 데이터 로드
candles = fetch_history("BTCUSDT", "5m", limit=500)
df = pd.DataFrame(candles)

# 2. 지표 계산
df = add_indicators(df, ema_fast=9, ema_mid=21, ema_slow=50)

# 3. 최근 지표 확인
last = df.iloc[-1]
print(f"RSI: {last['rsi']:.2f}")
print(f"MACD: {last['macd']:.4f}")
print(f"ATR: {last['atr']:.4f}")
print(f"레짐: {regime(last)}")

# 4. 전략에 사용
if last['rsi'] < 30 and last['macd'] > last['macd_signal']:
    print("매수 신호!")
```

---

**최종 업데이트**: 2025-10-19
