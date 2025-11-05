# 🎯 Strategies 모듈

**전략 로직** - 6개 전략 + Ensemble 통합

**경로**: `strategies/`

---

## 개요

### 6개 전략

| 전략 | 파일 | 타임프레임 | 특징 |
|------|------|-----------|------|
| **Trend** | `trend.py` | 1h | EMA 크로스 + MACD |
| **Reversion** | `reversion.py` | 5m | RSI 극단 + BB |
| **Breakout** | `breakout.py` | 15m | Donchian 돌파 |
| **Scalping** | `scalping.py` | 1m | BB 터치 + EMA |
| **Daytrade** | `daytrade.py` | 5m | 레짐 기반 |
| **Swing** | `swing.py` | 15m | 추세장 |

### Ensemble
**파일**: `ensemble.py`  
**역할**: 6개 전략 신호를 가중치 기반으로 통합

---

## 전략 구조

### signal_logic() 함수

**모든 전략은 동일한 인터페이스**:

```python
def signal_logic(df: pd.DataFrame, config: dict) -> Dict[str, Any]:
    """
    전략 로직 실행
    
    Args:
        df: 지표가 계산된 DataFrame
        config: 설정 딕셔너리
    
    Returns:
        {
            "side": "LONG" | "SHORT" | None,
            "entry": float,
            "sl": float,
            "tp": float,
            "lev": int,
            "atr": float,
            "confidence": float,
            "reason": List[str],
            # 기타 지표 값들...
        }
    """
```

---

## 전략 상세

### **1. Trend (추세 추종)**

**조건**:
- LONG: EMA 상승 정렬 + MACD 골든크로스 + RSI 40~70
- SHORT: EMA 하락 정렬 + MACD 데드크로스 + RSI 30~60

**강점**: 강한 추세 구간

### **2. Reversion (평균 회귀)**

**조건**:
- LONG: RSI < 30 + BB 하단 터치
- SHORT: RSI > 70 + BB 상단 터치

**강점**: 횡보장

### **3. Breakout (돌파)**

**조건**:
- LONG: Donchian 상단 돌파 + 거래량 증가
- SHORT: Donchian 하단 돌파 + 거래량 증가

**강점**: 변동성 구간

### **4. Scalping (스캘핑)**

**조건**:
- LONG: BB 하단 터치 + EMA 상승 정렬
- SHORT: BB 상단 터치 + EMA 하락 정렬

**강점**: 단기 수익

### **5. Daytrade (데이트레이딩)**

**조건**:
- 레짐 기반 (상승장/하락장 판단)
- EMA 정렬 + MACD 확인

**강점**: 균형잡힌 전략

### **6. Swing (스윙)**

**조건**:
- 추세장 확인
- EMA 정렬 + RSI 필터

**강점**: 안정적 수익

---

## Ensemble 통합

### process_pending_signals()

**6개 신호를 가중치 기반으로 통합**

```python
from strategies import ensemble

# DB 연결 필요
with get_db_connection() as conn:
    ensemble.process_pending_signals(conn, logger)
```

**동작**:
1. `monitoring.signals`에서 최근 신호 조회
2. 성과 메트릭 로드 (`reporting.strategy_performance`)
3. 가중치 계산
   ```python
   weight = α*승률 + β*RR + γ*샤프 + δ*신뢰도 + ε*레짐
   ```
4. 통합 점수 산출
   ```python
   LONG_score = Σ(weight * confidence) for LONG
   SHORT_score = Σ(weight * confidence) for SHORT
   final_score = LONG_score - SHORT_score
   ```
5. 의사결정
   - `score > 0.15` → LONG
   - `score < -0.15` → SHORT
   - `else` → FLAT
6. `trading.decisions`에 저장

---

## 사용 예시

### 단일 전략 사용

```python
from strategies import trend
import pandas as pd

# DataFrame with indicators
df = add_indicators(df, ...)

# 전략 실행
signal = trend.signal_logic(df, config)

if signal and signal['side']:
    print(f"{signal['side']} @ {signal['entry']}")
```

### 6개 전략 모두 실행

```python
from strategies import trend, reversion, breakout, scalping, daytrade, swing

STRATEGIES = {
    "trend": trend,
    "reversion": reversion,
    "breakout": breakout,
    "scalping": scalping,
    "daytrade": daytrade,
    "swing": swing,
}

for strategy_id, strategy_module in STRATEGIES.items():
    signal = strategy_module.signal_logic(df, config)
    if signal and signal['side']:
        signal['strategy_id'] = strategy_id
        save_to_db(signal)
```

### Ensemble 통합

```python
from strategies import ensemble

# 주기적으로 실행 (5초마다)
while True:
    with get_db_connection() as conn:
        ensemble.process_pending_signals(conn, logger)
    time.sleep(5)
```

---

## 전략 추가 방법

1. 새로운 파일 생성 (예: `strategies/momentum.py`)
2. `signal_logic()` 함수 구현
3. `strategies/__init__.py`에 추가
4. `main.py`의 `STRATEGIES` dict에 추가

---

**최종 업데이트**: 2025-10-19
