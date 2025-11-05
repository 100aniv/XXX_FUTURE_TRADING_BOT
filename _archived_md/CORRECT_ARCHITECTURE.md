# ✅ 올바른 시스템 아키텍처

## 🎯 **핵심 원칙**

**백테스트와 실시간은 동일한 흐름을 따른다!**

```
데이터 → indicators → strategies → signals (DB) → ensemble (DB) → execution (DB)
```

---

## 📋 **전체 플로우 (백테스트 & 실시간 공통)**

### **Step 1: 데이터 수집**

```python
# 백테스트
data = BacktestDataSource(csv_file)
candle = data.get_next_candle()

# 실시간
websocket = WebSocketCollector()
candle = websocket.on_candle_closed()
```

### **Step 2: 지표 계산**

```python
from indicators import add_indicators

df = add_indicators(df)
# → EMA, RSI, MACD, BB, ATR, Stochastic, ADX...
```

### **Step 3: 신호 생성 (6개 전략 독립 실행)**

```python
from signals import SignalGenerator
from strategies import trend, reversion, breakout, scalping, daytrade, swing

# SignalGenerator가 각 전략 실행 + 검증
for strategy in [trend, reversion, breakout, scalping, daytrade, swing]:
    signal = signal_generator.process_candle(candle, strategy)
    
    # ✅ DB 저장 (monitoring.signals)
    save_signal_to_db(
        strategy_id=strategy.name,
        symbol=candle['symbol'],
        direction=signal['side'],
        entry_price=signal['entry'],
        sl=signal['sl'],
        tp=signal['tp'],
        confidence=signal['confidence']
    )
```

**DB 스키마:**
```sql
CREATE TABLE monitoring.signals (
    signal_id UUID,
    strategy_id VARCHAR,  -- 'trend', 'scalping', etc.
    symbol VARCHAR,
    timeframe VARCHAR,
    direction VARCHAR,    -- 'LONG', 'SHORT'
    entry_price DECIMAL,
    sl_price DECIMAL,
    tp_price DECIMAL,
    confidence DECIMAL,
    created_at TIMESTAMP
);
```

### **Step 4: Ensemble 통합**

```python
from strategies.ensemble import process_pending_signals

# ✅ DB에서 신호 읽기
signals = db.query("SELECT * FROM monitoring.signals WHERE processed = false")

# 성과 기반 가중치 계산
weights = calculate_weights_from_performance(signals)

# 통합 점수
score = ensemble_score(signals, weights)

# 최종 결정
if score > threshold:
    decision = "LONG"
elif score < -threshold:
    decision = "SHORT"
else:
    decision = "FLAT"

# ✅ DB 저장 (trading.decisions)
save_decision_to_db(
    decision_id=uuid4(),
    symbol=symbol,
    decision=decision,
    score=score,
    signal_count=len(signals)
)
```

**DB 스키마:**
```sql
CREATE TABLE trading.decisions (
    decision_id UUID,
    symbol VARCHAR,
    decision VARCHAR,  -- 'LONG', 'SHORT', 'FLAT'
    ensemble_score DECIMAL,
    signal_count INT,
    created_at TIMESTAMP
);
```

### **Step 5: 매매 실행**

```python
from execution import manager, TradingExecutor

# ✅ DB에서 결정 읽기
decisions = db.query("SELECT * FROM trading.decisions WHERE executed = false")

for decision in decisions:
    if decision['decision'] in ['LONG', 'SHORT']:
        # RiskManager 체크
        allowed, reason = risk_manager.check_order(signal, qty)
        
        if allowed:
            # 포지션 크기 계산
            qty = position_sizer.calculate(signal)
            
            # 주문 실행
            result = executor.execute(decision['decision'], price, qty)
            
            # ✅ DB 저장 (trading.trades)
            save_trade_to_db(
                trade_id=uuid4(),
                decision_id=decision['decision_id'],
                side=decision['decision'],
                entry_price=result['price'],
                qty=qty,
                status='OPEN'
            )
```

**DB 스키마:**
```sql
CREATE TABLE trading.trades (
    trade_id UUID,
    decision_id UUID,
    side VARCHAR,
    entry_price DECIMAL,
    exit_price DECIMAL,
    qty DECIMAL,
    pnl DECIMAL,
    status VARCHAR,  -- 'OPEN', 'CLOSED'
    created_at TIMESTAMP,
    closed_at TIMESTAMP
);
```

---

## 🔄 **백테스트 vs 실시간 차이**

### **유일한 차이점: 데이터 소스**

```python
# main.py

if mode == 'backtest':
    # CSV 데이터
    data_source = BacktestDataSource('data.csv')
    
    for candle in data_source:
        process_candle(candle)  # 동일한 함수!
        
elif mode == 'paper' or mode == 'live':
    # WebSocket 데이터
    websocket = WebSocketCollector()
    
    @websocket.on_candle_closed
    def handle_candle(candle):
        process_candle(candle)  # 동일한 함수!
```

**process_candle() 함수는 완전히 동일:**
```python
def process_candle(candle):
    # 1. 지표 계산
    df = add_indicators(df)
    
    # 2. 신호 생성 (6개 전략)
    for strategy in strategies:
        signal = signal_generator.process(candle, strategy)
        save_signal_to_db(signal)  # ✅ DB
    
    # 3. Ensemble (주기적)
    if should_run_ensemble():
        ensemble.process_pending_signals()  # ✅ DB
    
    # 4. Execution (주기적)
    if should_execute():
        execution_manager.process_trades()  # ✅ DB
```

---

## 🌐 **REST API**

### **필수 엔드포인트**

```python
# api/routes.py

from fastapi import FastAPI
app = FastAPI()

# 신호 조회
@app.get("/api/signals")
def get_signals(strategy: str = None, limit: int = 100):
    """최근 신호 조회"""
    return db.query("SELECT * FROM monitoring.signals LIMIT ?", limit)

# 결정 조회
@app.get("/api/decisions")
def get_decisions(limit: int = 100):
    """최근 Ensemble 결정 조회"""
    return db.query("SELECT * FROM trading.decisions LIMIT ?", limit)

# 포지션 조회
@app.get("/api/positions")
def get_positions():
    """현재 오픈 포지션"""
    return db.query("SELECT * FROM trading.trades WHERE status='OPEN'")

# 성능 조회
@app.get("/api/performance")
def get_performance(strategy: str = None):
    """전략별 성능"""
    return calculate_performance_from_db(strategy)

# 거래 내역
@app.get("/api/trades")
def get_trades(limit: int = 100):
    """최근 거래 내역"""
    return db.query("SELECT * FROM trading.trades LIMIT ?", limit)
```

---

## 📊 **리포트 생성**

### **모든 데이터는 DB에서**

```python
# reports/performance_reporter.py

def generate_report(mode='backtest'):
    # ✅ DB에서 데이터 로드
    signals = db.query("SELECT * FROM monitoring.signals")
    decisions = db.query("SELECT * FROM trading.decisions")
    trades = db.query("SELECT * FROM trading.trades")
    
    # 전략별 성과
    for strategy in strategies:
        strategy_trades = [t for t in trades if t['strategy'] == strategy]
        metrics = calculate_metrics(strategy_trades)
        
        print(f"{strategy}: {metrics['win_rate']}, {metrics['pnl']}")
    
    # HTML 생성
    html = generate_html(signals, decisions, trades)
    save_html(html)
```

---

## 🎯 **승률 문제 해결**

### **현재 문제: 진입 조건이 잘못됨**

```python
# 잘못된 예시 (SCALPING)
if close > ema_fast and rsi > 50:
    signal = "LONG"  # ❌ 너무 단순!
```

### **올바른 방식 (REVERSION 참고)**

```python
# strategies/reversion.py 분석
# → 100% 승률의 비밀

def signal_logic(df, config):
    # 1. 강한 추세 확인
    if not (adx > 25 and trending):
        return None
    
    # 2. 과매수/과매도 + 반전 신호
    if rsi < 30 and macd_cross_up:
        # 3. 볼륨 확인
        if volume > volume_ma * 1.5:
            # 4. 지지선 근처
            if close near support:
                return "LONG"  # ✅ 여러 조건 충족!
```

---

## 📝 **구현 우선순위**

1. **DB 통합** - 모든 흐름이 DB 통과
2. **백테스트 수정** - 실시간과 동일한 흐름
3. **REST API** - 모니터링/제어
4. **진입 조건 개선** - REVERSION 로직을 다른 전략에 적용
5. **리포트 수정** - DB 기반, 모든 전략 표시
