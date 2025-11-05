# 📊 데이터 플로우 아키텍처

**작성일**: 2025-10-19  
**버전**: v2.0

---

## 🎯 전체 흐름

```
[Binance API] 
    ↓
[Collector] ← REST API (초기) + WebSocket (실시간)
    ↓
[Memory Buffer] ← deque(maxlen=400)
    ↓
[Indicators] ← EMA, RSI, MACD, BB, ATR 계산
    ↓
[Signals] ← 6개 전략 신호 생성
    ↓
[Database] ← monitoring.signals 저장
    ↓
[Ensemble] ← 통합 및 최종 결정
    ↓
[Database] ← trading.decisions 저장
    ↓
[Execution] ← 매매 실행
    ↓
[Database] ← trading.trades 저장
```

---

## 1️⃣ 데이터 수집 (Collector)

### **초기화 단계 (REST API)**

```python
# collector/rest_collector.py

# Step 1: 심볼 조회
symbols = get_all_symbols("top50")  
# → 거래량 상위 50개 (REST API)

# Step 2: 초기 히스토리 로드
for symbol in symbols:
    candles = fetch_history(symbol, "5m", 400)
    # → 400개 캔들 (REST API)
    
    buffer[symbol] = deque(candles, maxlen=400)
    # → 메모리 버퍼에 저장
```

**REST API 엔드포인트:**
- **Exchange Info**: `https://fapi.binance.com/fapi/v1/exchangeInfo`
  - 전체 심볼, 거래 규칙
- **24h Ticker**: `https://fapi.binance.com/fapi/v1/ticker/24hr`
  - 거래량 기준 정렬
- **Klines**: `https://fapi.binance.com/fapi/v1/klines`
  - 과거 캔들 데이터

### **실시간 단계 (WebSocket)**

```python
# collector/websocket_collector.py

ws = WebSocketCollector(symbols, timeframe="5m")

ws.on_candle(lambda symbol, candle, is_closed:
    # 버퍼 업데이트
    buffer[symbol].append(candle)
    
    if is_closed:  # 캔들 확정 시
        # 전략 실행
        process_strategies(symbol, buffer[symbol])
)

ws.connect()  # WebSocket 시작
```

**WebSocket 엔드포인트:**
- **Stream**: `wss://fstream.binance.com/stream`
- **Streams**: `btcusdt@kline_5m / ethusdt@kline_5m ...`

---

## 2️⃣ 메모리 버퍼 관리

### **현재 구조 (메모리 전용)**

```python
from collections import deque

# 심볼별 버퍼
buffers = {
    'BTCUSDT': deque(maxlen=400),  # 최근 400개만 유지
    'ETHUSDT': deque(maxlen=400),
    # ... 50개 심볼
}

# 메모리 사용량 (대략):
# 50 symbols × 400 candles × 6 fields × 8 bytes = ~1MB
```

**장점:**
- ✅ 빠른 접근 (O(1))
- ✅ 구현 간단
- ✅ 별도 서버 불필요

**단점:**
- ❌ 재시작 시 데이터 손실
- ❌ 과거 데이터 조회 불가
- ❌ 멀티 프로세스 공유 어려움

### **향후 확장 (Redis 캐시)**

```python
import redis
import json

r = redis.Redis(host='localhost', port=6379)

# 저장
r.setex(
    f"candles:{symbol}:{timeframe}",
    3600,  # TTL 1시간
    json.dumps(candles)
)

# 조회
cached = r.get(f"candles:{symbol}:{timeframe}")
if cached:
    candles = json.loads(cached)
```

**장점:**
- ✅ 재시작 후에도 데이터 유지
- ✅ 멀티 프로세스 공유
- ✅ TTL로 자동 정리

---

## 3️⃣ 지표 계산 (Indicators)

```python
# indicators/__init__.py

df = pd.DataFrame(buffer)  # deque → DataFrame

# 지표 계산
df = add_indicators(df, 
    ema_fast=9, 
    ema_mid=21, 
    ema_slow=50
)

# 결과:
# df['ema_9'], df['ema_21'], df['ema_50']
# df['rsi'], df['macd'], df['bb_upper'], df['atr']
```

---

## 4️⃣ 신호 생성 (Signals)

```python
# 6개 전략 실행
for strategy_id in ['trend', 'reversion', 'breakout', 'scalping', 'daytrade', 'swing']:
    signal = strategies[strategy_id].signal_logic(df, config)
    
    if signal:
        save_signal_to_db(
            symbol=symbol,
            strategy_id=strategy_id,
            side=signal['side'],
            entry_price=signal['entry'],
            sl=signal['sl'],
            tp=signal['tp'],
            confidence=signal['confidence']
        )
```

**DB 저장:**
```sql
INSERT INTO monitoring.signals 
(symbol, strategy_id, side, entry_price, sl, tp, confidence)
VALUES (?, ?, ?, ?, ?, ?, ?)
```

---

## 5️⃣ 앙상블 통합 (Ensemble)

```python
# 주기적 실행 (5초마다)

# Step 1: 대기 중인 신호 조회
signals = fetch_pending_signals()  # monitoring.signals

# Step 2: 가중치 계산
for signal in signals:
    weight = calculate_weight(
        strategy_id=signal.strategy_id,
        confidence=signal.confidence,
        performance=get_strategy_performance(signal.strategy_id)
    )

# Step 3: 최종 결정
final_score = sum(weights)

if final_score > 0.15:  # LONG
    create_decision(symbol, 'LONG', ...)
elif final_score < -0.15:  # SHORT
    create_decision(symbol, 'SHORT', ...)
```

**DB 저장:**
```sql
INSERT INTO trading.decisions 
(symbol, side, entry_price, sl, tp, size, ensemble_score)
VALUES (?, ?, ?, ?, ?, ?, ?)
```

---

## 6️⃣ 매매 실행 (Execution)

```python
# 주기적 실행 (5초마다)

# Step 1: 대기 중인 결정 조회
decisions = fetch_pending_decisions()  # trading.decisions

# Step 2: 리스크 검증
for decision in decisions:
    if risk_manager.can_trade(decision):
        # 포지션 사이징
        size = position_sizer.calculate_size(decision)
        
        # 주문 실행
        if mode == "live":
            order = executor.place_order(symbol, side, size, ...)
        elif mode == "paper":
            order = executor.simulate_order(symbol, side, size, ...)
        
        # 거래 기록
        save_trade_to_db(order)
```

**DB 저장:**
```sql
INSERT INTO trading.trades 
(symbol, side, entry_price, size, sl, tp, pnl, status)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
```

---

## 🔄 주기적 태스크

### **main.py 실행 흐름**

```python
# Thread 1: WebSocket 수신
# - 실시간 캔들 데이터
# - 캔들 종료 시 → 전략 실행

# Thread 2: Periodic Processor (5초)
# - Ensemble 통합
# - Execution 실행
```

---

## 📊 데이터 저장 위치

| 데이터 | 저장 위치 | 용도 |
|--------|----------|------|
| **실시간 캔들** | 메모리 버퍼 | 전략 실행 |
| **신호** | monitoring.signals | 전략별 신호 |
| **결정** | trading.decisions | Ensemble 결정 |
| **거래** | trading.trades | 매매 기록 |
| **포지션** | trading.positions | 현재 포지션 |

---

## 🚀 성능 최적화

### **현재 (v2.0)**
- 메모리 버퍼 (~1MB)
- 단일 프로세스
- WebSocket 50개 심볼

### **향후 (v3.0)**
```
- Redis 캐시 추가
- PostgreSQL 과거 데이터 저장
- 멀티 프로세스 (symbol 분산)
- gRPC 서비스 간 통신
```

---

**작성자**: AI Assistant  
**최종 업데이트**: 2025-10-19
