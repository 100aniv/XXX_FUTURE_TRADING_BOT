# 📡 Collector 모듈

**데이터 수집 모듈** - 바이낸스에서 실시간/과거 데이터 수집

**경로**: `collector/`  
**최종 업데이트**: 2025-10-19

---

## 📋 목차

1. [개요](#개요)
2. [모듈 구조](#모듈-구조)
3. [WebSocketCollector](#websocketcollector)
4. [REST API 함수들](#rest-api-함수들)
5. [사용 예시](#사용-예시)
6. [API 레퍼런스](#api-레퍼런스)

---

## 개요

Collector 모듈은 바이낸스 선물 거래소에서 데이터를 수집하는 역할을 합니다.

### **핵심 기능**
- ✅ **실시간 데이터**: WebSocket을 통한 캔들 스트리밍
- ✅ **히스토리 데이터**: REST API를 통한 과거 데이터 로드
- ✅ **자동 재연결**: 연결 끊김 시 자동 재시도
- ✅ **멀티 심볼**: 여러 종목 동시 수집
- ✅ **멀티 타임프레임**: 5m, 15m, 1h 등 동시 수집

### **데이터 플로우**
```
Binance Futures API
  ↓
WebSocket / REST
  ↓
collector/
  ↓
캔들 데이터 (OHLCV)
  ↓
signals/ (다음 모듈)
```

---

## 모듈 구조

```
collector/
├── __init__.py              # 모듈 진입점
├── websocket_collector.py   # WebSocket 실시간 수집
└── rest_collector.py        # REST API 히스토리 수집
```

### **파일 설명**

| 파일 | 역할 | 핵심 클래스/함수 |
|------|------|------------------|
| `websocket_collector.py` | 실시간 데이터 | `WebSocketCollector` |
| `rest_collector.py` | 과거 데이터 | `fetch_history()`, `bootstrap_history()` |

---

## WebSocketCollector

**실시간 캔들 데이터 수집 클래스**

### **특징**
- ✅ 바이낸스 WebSocket 연결
- ✅ 캔들 종료 시 콜백 호출
- ✅ 자동 재연결
- ✅ 멀티 심볼/타임프레임

### **초기화**

```python
from collector import WebSocketCollector

# 초기화
collector = WebSocketCollector(
    symbols=["BTCUSDT", "ETHUSDT"],  # 수집할 심볼 리스트
    timeframe="5m"                    # 주 타임프레임
)
```

### **콜백 등록**

```python
# 1. 캔들 닫힘 콜백
def on_candle_closed(symbol, candle, is_closed, timeframe):
    if is_closed:
        print(f"{symbol} {timeframe} 캔들 종료: {candle['close']}")

collector.on_candle(on_candle_closed)

# 2. 연결 성공 콜백
def on_connect():
    print("✅ WebSocket 연결 성공")

collector.on_connect(on_connect)

# 3. 에러 콜백
def on_error(error):
    print(f"❌ 에러: {error}")

collector.on_error(on_error)

# 4. 재연결 콜백
def on_reconnect():
    print("🔌 재연결 중...")

collector.on_close_reconnect(on_reconnect)
```

### **시작**

```python
# WebSocket 연결 시작 (blocking)
collector.start()
```

### **캔들 데이터 구조**

```python
{
    "time": 1698264600000,      # 캔들 시작 시간 (timestamp ms)
    "open": 34250.5,            # 시가
    "high": 34300.0,            # 고가
    "low": 34200.0,             # 저가
    "close": 34280.0,           # 종가
    "volume": 123.45,           # 거래량
    "close_time": 1698264899999 # 캔들 종료 시간
}
```

---

## REST API 함수들

### **1. fetch_history()**

**과거 캔들 데이터 다운로드**

```python
from collector import fetch_history

# 사용법
candles = fetch_history(
    symbol="BTCUSDT",      # 심볼
    interval="5m",         # 타임프레임
    limit=500              # 캔들 개수 (최대 1500)
)

# 결과: List[Dict]
# [
#   {"time": ..., "open": ..., "high": ..., "low": ..., "close": ..., "volume": ...},
#   ...
# ]
```

**파라미터**:
- `symbol` (str): 거래 심볼 (예: "BTCUSDT")
- `interval` (str): 타임프레임 (1m, 5m, 15m, 1h, 4h, 1d)
- `limit` (int): 가져올 캔들 개수 (기본: 500, 최대: 1500)

**반환**: `List[Dict]` - 캔들 데이터 리스트

### **2. bootstrap_history()**

**초기 버퍼 채우기**

```python
from collector import bootstrap_history
from collections import deque

# 심볼별 버퍼 생성
buffers = {
    "BTCUSDT": deque(maxlen=400),
    "ETHUSDT": deque(maxlen=400)
}

# 히스토리 로드 및 버퍼 채우기
bootstrap_history(
    symbol="BTCUSDT",
    timeframe="5m",
    lookback=400,
    buffers=buffers
)

# 결과: buffers["BTCUSDT"]에 400개 캔들 저장됨
```

**파라미터**:
- `symbol` (str): 심볼
- `timeframe` (str): 타임프레임
- `lookback` (int): 로드할 캔들 개수
- `buffers` (Dict[str, deque]): 심볼별 버퍼 딕셔너리

### **3. fetch_all_symbols()**

**거래 가능한 모든 심볼 조회**

```python
from collector import fetch_all_symbols

symbols = fetch_all_symbols()
# ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', ...]
```

**반환**: `List[str]` - 심볼 리스트

### **4. fetch_top_volume_symbols()**

**거래량 상위 종목 조회**

```python
from collector import fetch_top_volume_symbols

# 상위 20개 종목
top_symbols = fetch_top_volume_symbols(limit=20)
# [
#   {"symbol": "BTCUSDT", "volume": 123456789.0, "price": 34250.5},
#   ...
# ]
```

**파라미터**:
- `limit` (int): 조회할 개수 (기본: 20)

**반환**: `List[Dict]` - 심볼, 거래량, 가격 포함

### **5. fetch_ticker_24h()**

**24시간 가격 통계**

```python
from collector import fetch_ticker_24h

# 특정 심볼
ticker = fetch_ticker_24h("BTCUSDT")
# {
#   "symbol": "BTCUSDT",
#   "priceChange": "500.5",
#   "priceChangePercent": "1.48",
#   "lastPrice": "34250.5",
#   "volume": "123456.78",
#   "quoteVolume": "4234567890.12",
#   "highPrice": "34500.0",
#   "lowPrice": "33800.0"
# }

# 전체 심볼
all_tickers = fetch_ticker_24h()  # symbol 파라미터 없음
```

**파라미터**:
- `symbol` (str, optional): 특정 심볼. 없으면 전체 조회

**반환**: `Dict` 또는 `List[Dict]`

### **6. fetch_exchange_info()**

**거래소 정보 조회**

```python
from collector import fetch_exchange_info

info = fetch_exchange_info()
# {
#   "timezone": "UTC",
#   "serverTime": 1698264600000,
#   "symbols": [
#     {
#       "symbol": "BTCUSDT",
#       "status": "TRADING",
#       "baseAsset": "BTC",
#       "quoteAsset": "USDT",
#       "pricePrecision": 2,
#       "quantityPrecision": 3,
#       ...
#     },
#     ...
#   ]
# }
```

**반환**: `Dict` - 거래소 전체 정보

---

## 사용 예시

### **예시 1: 실시간 캔들 수집**

```python
from collector import WebSocketCollector

def main():
    # Collector 초기화
    collector = WebSocketCollector(
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe="5m"
    )
    
    # 캔들 콜백 등록
    def on_candle(symbol, candle, is_closed, timeframe):
        if is_closed and timeframe != "1m":
            print(f"✅ {symbol} {timeframe} 종료")
            print(f"   종가: {candle['close']}")
            print(f"   거래량: {candle['volume']}")
    
    collector.on_candle(on_candle)
    collector.on_connect(lambda: print("🔗 연결 성공"))
    
    # 시작
    collector.start()

if __name__ == "__main__":
    main()
```

### **예시 2: 히스토리 로드**

```python
from collector import fetch_history
import pandas as pd

# 과거 500개 캔들 다운로드
candles = fetch_history("BTCUSDT", "1h", limit=500)

# DataFrame 변환
df = pd.DataFrame(candles)
df['time'] = pd.to_datetime(df['time'], unit='ms')
df.set_index('time', inplace=True)

print(df.tail())
#                      open     high      low    close    volume
# time
# 2025-10-19 12:00  34200.0  34300.0  34150.0  34250.5  1234.56
# 2025-10-19 13:00  34250.5  34400.0  34200.0  34380.0  2345.67
# ...
```

### **예시 3: 초기 버퍼 설정**

```python
from collector import WebSocketCollector, bootstrap_history
from collections import deque

# 설정
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
TIMEFRAME = "5m"
LOOKBACK = 400

# 버퍼 생성
buffers = {symbol: deque(maxlen=LOOKBACK) for symbol in SYMBOLS}

# 초기 히스토리 로드
for symbol in SYMBOLS:
    print(f"📥 {symbol} 히스토리 로딩...")
    bootstrap_history(symbol, TIMEFRAME, LOOKBACK, buffers)
    print(f"✅ {len(buffers[symbol])}개 캔들 로드 완료")

# WebSocket 시작
collector = WebSocketCollector(SYMBOLS, TIMEFRAME)

def on_candle(symbol, candle, is_closed, timeframe):
    if is_closed:
        # 버퍼에 추가 (자동으로 가장 오래된 것 제거)
        buffers[symbol].append(candle)
        print(f"📊 {symbol} 버퍼: {len(buffers[symbol])}개")

collector.on_candle(on_candle)
collector.start()
```

---

## API 레퍼런스

### **WebSocketCollector**

#### **생성자**

```python
WebSocketCollector(symbols: List[str], timeframe: str)
```

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `symbols` | `List[str]` | 수집할 심볼 리스트 |
| `timeframe` | `str` | 주 타임프레임 (5m, 15m, 1h 등) |

#### **메서드**

| 메서드 | 설명 | 파라미터 |
|--------|------|----------|
| `on_candle(callback)` | 캔들 콜백 등록 | `callback(symbol, candle, is_closed, timeframe)` |
| `on_connect(callback)` | 연결 콜백 등록 | `callback()` |
| `on_error(callback)` | 에러 콜백 등록 | `callback(error)` |
| `on_close_reconnect(callback)` | 재연결 콜백 등록 | `callback()` |
| `start()` | WebSocket 시작 | 없음 (blocking) |

### **REST API 함수들**

| 함수 | 파라미터 | 반환 |
|------|----------|------|
| `fetch_history()` | `symbol, interval, limit` | `List[Dict]` |
| `bootstrap_history()` | `symbol, timeframe, lookback, buffers` | `None` |
| `fetch_all_symbols()` | 없음 | `List[str]` |
| `fetch_top_volume_symbols()` | `limit` | `List[Dict]` |
| `fetch_ticker_24h()` | `symbol?` | `Dict` or `List[Dict]` |
| `fetch_exchange_info()` | 없음 | `Dict` |

---

## 주의사항

### **1. Rate Limit**
- 바이낸스 API는 요청 제한이 있습니다
- REST API: 1200 요청/분
- WebSocket: 연결 제한 없음 (권장)

### **2. WebSocket 연결**
- `start()`는 blocking 함수입니다
- 별도 스레드에서 실행하거나 메인 루프로 사용하세요

```python
# ❌ 잘못된 예
collector.start()
print("이 코드는 실행되지 않습니다")

# ✅ 올바른 예 1: 메인 루프
if __name__ == "__main__":
    collector.start()  # 프로그램 종료 시까지 실행

# ✅ 올바른 예 2: 별도 스레드
import threading
thread = threading.Thread(target=collector.start, daemon=True)
thread.start()
```

### **3. 메모리 관리**
- `deque(maxlen=N)`을 사용하여 버퍼 크기 제한
- 장기 실행 시 메모리 누수 주의

---

## 트러블슈팅

### **Q: WebSocket 연결이 끊어집니다**
A: 자동 재연결 기능이 있습니다. `on_close_reconnect()` 콜백으로 모니터링하세요.

### **Q: 히스토리 로드가 느립니다**
A: `limit`를 줄이거나 여러 번 나누어 로드하세요.

### **Q: 특정 심볼이 없다고 합니다**
A: `fetch_all_symbols()`로 사용 가능한 심볼을 확인하세요.

---

**작성자**: AI Assistant  
**최종 업데이트**: 2025-10-19  
**버전**: v2.0
