# ✅ 통합 플로우 (백테스트 = 실시간)

## 🎯 **핵심 원칙**

**하나의 공통 루프 + 모드별 어댑터만 교체**

```python
# 공통 루프 (모든 모드 동일)
for candle in feed.stream():  # ← Feed만 다름
    # 1. 지표 계산
    df = add_indicators(df)
    
    # 2. 6개 전략 신호 생성
    for strategy in [trend, reversion, breakout, scalping, daytrade, swing]:
        signal = strategy.signal_logic(df, config)
        signals.append(signal)
    
    # 3. Ensemble 통합 (디폴트)
    decision = ensemble.combine(signals)
    
    # 4. PositionSizer
    qty, meta = position_sizer.compute(decision, equity)
    
    # 5. Broker 실행
    fill = broker.execute(decision, qty)  # ← Broker만 다름
    
    # 6. Portfolio 업데이트
    portfolio.apply(fill)
```

---

## 📋 **모드별 차이점 (어댑터만)**

### **1. Feed (데이터 소스)**

```python
# Backtest
feed = HistoricalFeed('data/BTCUSDT_5m.csv')

# Paper/Live
feed = LiveFeed(websocket=True, symbols=['BTCUSDT'])
```

### **2. Broker (실행)**

```python
# Backtest
broker = SimBroker(slippage=0.0001, fee=0.0004)

# Paper
broker = PaperBroker(mode='paper')  # 가상 체결

# Live
broker = ExchangeBroker(api_key=..., api_secret=...)
```

### **3. Clock (시간)**

```python
# Backtest
clock = SimClock(candle.timestamp)  # 고스트 시계

# Paper/Live
clock = LiveClock()  # 실시간 시계
```

---

## 🔧 **즉시 수정 사항**

### **execution/engine.py 수정**

현재:
```python
# run_backtest()에서 각 전략 개별 실행
for strategy in strategies:
    trades, metrics = engine.run_backtest(strategy, config)
```

수정 후:
```python
# 실시간과 동일한 흐름
def run_backtest(config):
    feed = HistoricalFeed(csv_path)
    broker = SimBroker()
    
    # ✅ 공통 루프
    for candle in feed:
        signals = process_strategies(candle)  # 6개 전략
        decision = ensemble.combine(signals)  # Ensemble
        qty = position_sizer.compute(decision)
        fill = broker.execute(decision, qty)
        portfolio.apply(fill)
```

### **main.py 수정**

```python
def main():
    mode = CFG['trading_mode']  # 'backtest', 'paper', 'live'
    
    # ✅ 어댑터만 교체
    if mode == 'backtest':
        feed = HistoricalFeed(csv_path)
        broker = SimBroker()
        clock = SimClock()
    elif mode == 'paper':
        feed = LiveFeed(websocket=True)
        broker = PaperBroker()
        clock = LiveClock()
    elif mode == 'live':
        feed = LiveFeed(websocket=True)
        broker = ExchangeBroker(api_key, api_secret)
        clock = LiveClock()
    
    # ✅ 공통 루프 실행
    trading_loop(feed, broker, clock, strategies, ensemble, position_sizer, risk_manager)
```

---

## 📁 **현재 구조 유지**

```
collectors/
  websocket.py       # LiveFeed
  historical.py      # HistoricalFeed (새로 추가)
  
execution/
  engine.py          # 공통 루프
  executors/
    sim.py           # SimBroker
    paper.py         # PaperBroker
    live.py          # ExchangeBroker (LiveExecutor)
  position_sizer.py  # PositionSizer (있음)
  risk_manager.py    # RiskManager (있음)

strategies/
  trend.py, reversion.py, ...
  ensemble.py        # Ensemble (디폴트)

signals/
  (실시간 DB 저장용, 백테스트는 메모리)
```

---

## ✅ **다음 단계**

1. HistoricalFeed 추가 (collectors/historical.py)
2. execution/engine.py 수정 (공통 루프)
3. main.py 수정 (어댑터 교체)
4. 백테스트 재실행
