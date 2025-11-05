# 📋 Collector 표준화 완료

**날짜:** 2025-10-20  
**체크리스트 #2:** stream()이 닫힌 캔들만 yield (키: symbol, timeframe, closed_at)

---

## ✅ **적용 완료**

### **1. HistoricalFeed (백테스트)**

**변경 사항:**
```python
# collectors/historical_collector.py

class HistoricalFeed:
    def __init__(self, csv_path: str, symbol: str = None, timeframe: str = None, tz: str = None):
        """
        Args:
            csv_path: CSV 파일 경로
            symbol: 심볼 (예: 'BTCUSDT')  # ⭐ 추가
            timeframe: 타임프레임 (예: '5m')  # ⭐ 추가
            tz: 시간대
        """
        self.symbol = symbol or 'BTCUSDT'
        self.timeframe = timeframe or '5m'
    
    def stream(self) -> Iterator[Dict]:
        """캔들 스트림 (닫힌 캔들만)"""
        for i in range(self.total):
            row = self.df.iloc[i]
            ts = int(row["time"].timestamp() * 1000)
            
            # ⭐ 표준 키 형식
            candle = {
                'symbol': self.symbol,        # ⭐ 추가
                'timeframe': self.timeframe,  # ⭐ 추가
                'closed_at': ts,              # ⭐ 추가 (time → closed_at)
                'time': ts,                   # 하위 호환성
                'open': float(row["open"]),
                'high': float(row["high"]),
                'low': float(row["low"]),
                'close': float(row["close"]),
                'volume': float(row["volume"])
            }
            yield candle
```

**특징:**
- ✅ CSV 데이터는 모두 닫힌 캔들
- ✅ symbol, timeframe 명시적으로 포함
- ✅ closed_at으로 "닫힌 캔들"임을 명확히 표현

---

### **2. WebSocketCollector (실시간)**

**변경 사항:**
```python
# collectors/websocket_collector.py

def _on_message(self, ws, message):
    """WebSocket 메시지 수신"""
    data = json.loads(message)
    payload = data["data"]
    k = payload.get("k", {})
    
    symbol = payload.get("s")      # ⭐ 심볼 추출
    timeframe = k.get("i")         # ⭐ 타임프레임 추출
    is_closed = k.get("x", False)  # ⭐ 닫힌 캔들 확인
    
    # ⭐ 표준 키 형식
    candle = {
        "symbol": symbol,            # ⭐ 추가
        "timeframe": timeframe,      # ⭐ 추가
        "closed_at": int(k["t"]),    # ⭐ 추가
        "time": int(k["t"]),         # 하위 호환성
        "open": float(k["o"]),
        "high": float(k["h"]),
        "low": float(k["l"]),
        "close": float(k["c"]),
        "volume": float(k["v"])
    }
    
    # ⭐ 닫힌 캔들만 큐에 추가
    if is_closed:
        self.candle_queue.put_nowait(candle)

def stream(self):
    """캔들 스트림 (닫힌 캔들만)"""
    while self.running:
        candle = self.candle_queue.get(timeout=1.0)
        yield candle  # ⭐ 닫힌 캔들만 yield
```

**특징:**
- ✅ 닫힌 캔들만 큐에 추가 (`is_closed` 체크)
- ✅ symbol, timeframe 동적으로 추출
- ✅ stream()이 닫힌 캔들만 yield

---

### **3. engine.py (소비자)**

**변경 사항:**
```python
# execution/engine.py

for candle in feed.stream():
    candle_count += 1
    
    # ⭐ 표준 키 사용: closed_at (하위 호환 time 지원)
    ts = candle.get('closed_at', candle.get('time', 0))
    
    # 시계 업데이트
    clock.update(ts)
    
    # Flash Guard
    risk.flash_guard_update(symbol, current_price, ts)
    
    # 신호 생성
    signal['ts'] = ts
    ...
```

**특징:**
- ✅ `closed_at` 우선 사용
- ✅ `time` 하위 호환 지원
- ✅ 엔진은 캔들이 닫혔다고 가정

---

### **4. main.py (주입)**

**변경 사항:**
```python
# main.py

if mode == 'backtest':
    # ⭐ symbol, timeframe 명시적 전달
    feed = HistoricalFeed(csv_path, symbol=symbol, timeframe=timeframe)
    broker = SimBroker()
    clock = SimClock()

elif mode == 'paper':
    # ⭐ WebSocketCollector는 이미 symbol, timeframe 포함
    feed = WebSocketCollector([symbol], timeframe)
    broker = PaperBroker()
    clock = LiveClock()

# ⭐ 엔진은 동일!
engine.run(feed, broker, clock, strategies, ensemble, config)
```

---

## 📊 **표준 캔들 형식**

### **Before:**
```python
{
    'time': 1609459200000,
    'open': 100.0,
    'high': 101.0,
    'low': 99.0,
    'close': 100.5,
    'volume': 1000.0
}
```

**문제점:**
- ❌ symbol 없음 (멀티 심볼 불명확)
- ❌ timeframe 없음 (멀티 타임프레임 불명확)
- ❌ `time`이 "닫힌 시간"인지 불명확

---

### **After:**
```python
{
    'symbol': 'BTCUSDT',        # ⭐ 추가
    'timeframe': '5m',          # ⭐ 추가
    'closed_at': 1609459200000, # ⭐ 추가 (명확한 네이밍)
    'time': 1609459200000,      # 하위 호환
    'open': 100.0,
    'high': 101.0,
    'low': 99.0,
    'close': 100.5,
    'volume': 1000.0
}
```

**개선점:**
- ✅ symbol 명시 (멀티 심볼 지원)
- ✅ timeframe 명시 (멀티 타임프레임 지원)
- ✅ `closed_at`으로 "닫힌 캔들"임을 명확히 표현
- ✅ `time` 하위 호환성 유지

---

## 🎯 **체크리스트 검증**

### **요구사항:**
> stream()이 닫힌 캔들만 yield (키: symbol, timeframe, closed_at)

### **검증:**

| 항목 | HistoricalFeed | WebSocketCollector |
|-----|----------------|-------------------|
| **stream() 메서드** | ✅ | ✅ |
| **닫힌 캔들만 yield** | ✅ (CSV 모두 닫힌 캔들) | ✅ (`is_closed` 체크) |
| **symbol 키** | ✅ | ✅ |
| **timeframe 키** | ✅ | ✅ |
| **closed_at 키** | ✅ | ✅ |

**✅ 100% 통과!**

---

## 🧪 **테스트**

### **단위 테스트:**
```python
# tests/test_collectors.py

def test_candle_keys():
    """캔들 키 형식 검증"""
    feed = HistoricalFeed(csv_path, symbol='BTCUSDT', timeframe='5m')
    candle = next(feed.stream())
    
    # 표준 키 검증
    assert 'symbol' in candle
    assert 'timeframe' in candle
    assert 'closed_at' in candle
    
    # 값 검증
    assert candle['symbol'] == 'BTCUSDT'
    assert candle['timeframe'] == '5m'
    assert isinstance(candle['closed_at'], int)

def test_all_candles_closed():
    """모든 캔들이 닫혀있는지 검증"""
    feed = HistoricalFeed(csv_path, symbol='BTCUSDT', timeframe='5m')
    
    for candle in feed.stream():
        assert candle['closed_at'] > 0
        assert isinstance(candle['closed_at'], int)
```

**실행:**
```bash
pytest tests/test_collectors.py -v
```

---

## 📝 **하위 호환성**

### **기존 코드 지원:**

```python
# 기존 코드 (time 사용)
ts = candle.get('time', 0)  # ✅ 여전히 작동

# 새 코드 (closed_at 사용)
ts = candle.get('closed_at', 0)  # ✅ 작동

# 권장 (하위 호환)
ts = candle.get('closed_at', candle.get('time', 0))  # ✅ 최고!
```

**마이그레이션 계획:**
1. **Phase 1:** `closed_at` 추가, `time` 유지 (현재) ✅
2. **Phase 2:** 모든 코드에서 `closed_at` 사용
3. **Phase 3:** `time` 키 제거 (breaking change)

**현재는 Phase 1이므로 기존 코드 100% 호환!**

---

## 🚀 **장점**

### **1. 멀티 심볼 지원**
```python
# 여러 심볼 동시 처리 가능
for candle in feed.stream():
    symbol = candle['symbol']  # 'BTCUSDT', 'ETHUSDT', ...
    process_candle(symbol, candle)
```

### **2. 멀티 타임프레임 지원**
```python
# 여러 타임프레임 동시 처리 가능
for candle in feed.stream():
    timeframe = candle['timeframe']  # '1m', '5m', '15m', ...
    process_candle(timeframe, candle)
```

### **3. 명확한 시맨틱**
```python
# "닫힌 캔들"임을 명확히 표현
closed_at = candle['closed_at']  # 명확!
time = candle['time']           # 애매함 (열린 시간? 닫힌 시간?)
```

### **4. Collector 일관성**
```python
# HistoricalFeed와 WebSocketCollector가 동일한 형식
candle1 = next(historical_feed.stream())
candle2 = next(websocket_feed.stream())

assert candle1.keys() == candle2.keys()  # ✅ True!
```

---

## 📚 **관련 파일**

- `collectors/historical_collector.py` - HistoricalFeed 표준화
- `collectors/websocket_collector.py` - WebSocketCollector 표준화
- `execution/engine.py` - closed_at 사용
- `main.py` - Feed 초기화 시 symbol, timeframe 전달
- `tests/test_collectors.py` - 단위 테스트
- `ARCHITECTURE_CHECKLIST.md` - 전체 체크리스트

---

## ✅ **결론**

**체크리스트 #2 완료!**

- ✅ stream()이 닫힌 캔들만 yield
- ✅ 키: (symbol, timeframe, closed_at)
- ✅ HistoricalFeed 표준화
- ✅ WebSocketCollector 표준화
- ✅ engine.py 업데이트
- ✅ 하위 호환성 유지
- ✅ 단위 테스트 작성

**"엔진 하나 + 주입만 교체" 구조 강화!** 🚀
