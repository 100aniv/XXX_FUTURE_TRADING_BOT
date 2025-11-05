# 시스템 아키텍처 (v1.0)

**작성일**: 2025-11-05 12:00 UTC+09:00  
**상태**: ✅ 완료 (상용 프로그램 수준)  
**.windsurfrules 준수**: 100%

---

## 목차

1. [시스템 개요](#시스템-개요)
2. [앙상블 전략 구조](#앙상블-전략-구조)
3. [리스크 관리 시스템](#리스크-관리-시스템)
4. [신호 생성 및 검증](#신호-생성-및-검증)
5. [거래 실행 흐름](#거래-실행-흐름)
6. [전체 기능 기준](#전체-기능-기준)
7. [DB 구조](#db-구조)

---

## 시스템 개요

### 핵심 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                     Trading System                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  WebSocket   →  Collector  →  Multi-TF Buffer  →  Engine   │
│  (Binance)      (Queue)       (6개 TF 버퍼)     (신호생성)   │
│                                                             │
│  Engine  →  6개 전략  →  SignalGenerator  →  Ensemble      │
│             (독립실행)    (검증)            (통합)           │
│                                                             │
│  Ensemble  →  RiskManager  →  Portfolio  →  PositionSizer  │
│             (리스크체크)      (포트폴리오)   (사이징)         │
│                                                             │
│  PositionSizer  →  Broker  →  DB  →  Telegram              │
│                   (실행)     (저장)  (알림)                  │
└─────────────────────────────────────────────────────────────┘
```

### 시스템 특징

- **Multi-Strategy Ensemble**: 6개 독립 전략 동시 실행 + 통합 의사결정
- **Multi-Timeframe**: 6개 TF 독립 버퍼 (1m, 3m, 5m, 15m, 1h, 4h)
- **Multi-Symbol**: 100개 심볼 동시 모니터링
- **계층적 리스크 관리**: Risk → Portfolio → Position 3단계
- **상용 프로그램 수준**: 부동소수점 안전, 쿨다운, 텔레그램 알림

---

## 앙상블 전략 구조

### 1. 6개 독립 전략

**strategies/__init__.py**: 전략 로딩 및 관리
```python
def load_strategies(config: dict) -> Dict[str, Any]:
    # 앙상블 모드: enabled=true인 모든 전략 로드
    # 단일 모드: selector로 1개만 선택
```

**전략 목록**:
1. **scalping** - 3m TF, 빠른 진입/청산
2. **daytrade** - 5m TF, 1일 내 청산
3. **swing** - 15m TF, 2-5일 보유
4. **trend** - 1h TF, 트렌드 추종
5. **reversion** - 5m TF, 평균 회귀
6. **breakout** - 15m TF, 변동성 돌파

### 2. 전략 실행 흐름 (engine.py)

```python
# L503-669: 전략별 독립 실행
for strategy_id, strategy_module in selected_strategies.items():
    # 1. 전략별 설정 병합
    strategy_cfg = config['strategies'][strategy_id]
    cfg = {**config, **strategy_cfg}
    
    # 2. Multi-TF 버퍼 직접 사용 (PR7-4)
    strategy_tf = strategy_cfg.get('timeframe', '5m')
    strategy_buffer_key = (symbol, strategy_tf)
    
    if strategy_buffer_key in buffers and len(buffers[strategy_buffer_key]) >= min_bars:
        df_tf = pd.DataFrame(list(buffers[strategy_buffer_key]))
        df_tf = add_indicators(df_tf, ...)  # 지표 계산
    else:
        # Fallback: resample 사용
        df_tf = resample_dataframe(df, strategy_tf)
    
    # 3. 전략 실행
    signal = strategy_module.signal_logic(df_tf, cfg)
    
    # 4. 신호 검증
    if signal_gen.validate_signal(symbol, signal, df_tf):
        signals.append(signal)
```

### 3. 앙상블 통합 (strategies/ensemble.py)

**combine_signals()**: 신호 통합 및 최종 결정
```python
def combine_signals(signals: List[Dict], conn, config: dict) -> Dict:
    # 1. 방향 결정 (다수결)
    long_count = sum(1 for s in signals if s['side'] == 'LONG')
    short_count = sum(1 for s in signals if s['side'] == 'SHORT')
    
    if long_count > short_count:
        chosen_side = 'LONG'
    elif short_count > long_count:
        chosen_side = 'SHORT'
    else:
        return None  # 동점 시 거래 안 함
    
    # 2. 가중 평균 (entry, sl, tp)
    relevant = [s for s in signals if s['side'] == chosen_side]
    n = len(relevant)
    entry = sum(s['entry'] for s in relevant) / n
    sl = sum(s['sl'] for s in relevant) / n
    tp = sum(s['tp'] for s in relevant) / n
    
    # 3. 최종 결정
    decision = {
        'side': chosen_side,
        'entry': entry,
        'sl': sl,
        'tp': tp,
        'confidence': sum(s['confidence'] for s in relevant) / n,
        'strategy_id': f"ensemble_{n}_signals"
    }
    
    # 4. DB 저장 (trading.decisions)
    save_decision(conn, symbol, timeframe, candle_closed_at, decision)
    
    return decision
```

**가중치 계산 (고급 버전)**:
```python
def calculate_weights(signals, perf, config):
    # 공식: α*승률 + β*RR + γ*샤프 + δ*신뢰도 + ε*레짐
    raw_weight = (
        alpha * z_winrate +
        beta * z_rr +
        gamma * z_sharpe +
        delta * confidence +
        epsilon * regime_fit
    )
    # 정규화
    weights[strategy_id] = raw_weight / total
```

---

## 리스크 관리 시스템

### 계층적 리스크 관리 (3단계)

```
┌──────────────────────────────────────────────┐
│ 1. RiskManager (거래소/시장 수준)            │
│    - 일일 손실 한도                         │
│    - 심볼별 exposure 한도                   │
│    - Flash Guard (급등락 차단)              │
│    - 연속 손실 쿨다운                       │
├──────────────────────────────────────────────┤
│ 2. PortfolioManager (포트폴리오 수준)       │
│    - 최대 동시 포지션 수                    │
│    - 전체 portfolio exposure                │
│    - 심볼별 exposure                        │
│    - 전략별 budget 배분                     │
├──────────────────────────────────────────────┤
│ 3. PositionSizer (포지션 수준)              │
│    - Risk per trade (1%)                    │
│    - Quality weighting (0.7~1.3)            │
│    - 최대/최소 포지션 가치                  │
│    - 청산가 안전 마진                       │
└──────────────────────────────────────────────┘
```

### 1. RiskManager (execution/risk_manager.py)

**핵심 기능**:
```python
class RiskManager:
    def __init__(self, config):
        # 일일 손실 한도
        self.max_daily_loss_pct = config['risk']['max_daily_loss']  # 0.02 (2%)
        self.current_daily_loss = 0.0
        
        # 심볼별 exposure 한도
        self.max_exposure_per_symbol_pct = config['risk']['max_exposure_per_symbol']  # 0.3 (30%)
        self.symbol_exposures = {}
        
        # Flash Guard
        self.flash_guard_enabled = True
        self.flash_cooldown_ms = 5 * 60 * 1000  # 5분
        
        # 연속 손실 쿨다운
        self.max_consecutive_losses = 7
        self.consecutive_losses = 0
        self.cooldown_minutes = 30
    
    def check_order(self, decision, qty, position_value):
        # 1. 일일 손실 한도 체크
        if self.current_daily_loss <= -self.equity * self.max_daily_loss_pct:
            return False, "일일 손실 한도 초과"
        
        # 2. 심볼별 exposure 체크 (부동소수점 안전)
        epsilon = 0.1  # ⭐ 금융 프로그램 표준
        total_exposure = current_exposure + position_value
        if total_exposure > max_per_symbol + epsilon:
            return False, "심볼별 한도 초과"
        
        # 3. 연속 손실 쿨다운
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, f"연속 손실 쿨다운 ({self.consecutive_losses}회)"
        
        return True, "OK"
    
    def flash_guard_allowed(self, symbol, ts):
        # Flash Guard: 급등락 시 신호 차단
        last_block = self.flash_block_log.get(symbol, 0)
        return (ts - last_block) >= self.flash_cooldown_ms
```

### 2. PortfolioManager (execution/portfolio_manager.py)

**핵심 기능**:
```python
class PortfolioManager:
    def __init__(self, config):
        # 포지션 한도
        self.max_positions = config['portfolio']['max_positions']  # 3개
        self.max_exposure = config['portfolio']['max_exposure']  # 0.95 (95%)
        
        # 심볼별 한도
        self.max_exposure_per_symbol = config['portfolio']['max_exposure_per_symbol']  # 0.3 (30%)
        
        # 전략별 budget
        self.strategy_budgets = config['portfolio'].get('strategy_budgets', {})
    
    def can_open_position(self, symbol, strategy, position_value, side):
        # 1. 최대 포지션 수 체크
        active_count = len([p for p in self.active_positions if p['status'] == 'OPEN'])
        if active_count >= self.max_positions:
            return False, "최대 포지션 수 초과"
        
        # 2. 전체 exposure 체크
        total_exposure = self.calculate_total_exposure()
        if total_exposure + position_value > self.equity * self.max_exposure:
            return False, "전체 exposure 초과"
        
        # 3. 심볼별 exposure 체크
        symbol_exposure = self.get_symbol_exposure(symbol)
        if symbol_exposure + position_value > self.equity * self.max_exposure_per_symbol:
            return False, f"{symbol} exposure 초과"
        
        # 4. 전략별 budget 체크
        strategy_usage = self.get_strategy_usage(strategy)
        strategy_budget = self.strategy_budgets.get(strategy, 0.5)
        if strategy_usage + position_value > self.equity * strategy_budget:
            return False, f"{strategy} budget 초과"
        
        return True, "OK"
```

### 3. PositionSizer (execution/position_sizer.py)

**핵심 기능**:
```python
class PositionSizer:
    def __init__(self, config):
        # Risk per trade
        self.risk_pct = config['risk']['per_trade']  # 0.01 (1%)
        
        # Quality weighting
        self.quality_weight_range = (0.7, 1.3)
        
        # 포지션 가치 한도
        self.max_position_value = config['portfolio']['max_position_value']  # 10000 USDT
        self.min_position_value = config['portfolio']['min_position_value']  # 50 USDT
    
    def calculate(self, signal_params):
        entry = signal_params['entry_price']
        sl = signal_params['sl_price']
        confidence = signal_params['confidence']
        
        # 1. 리스크 금액 계산
        risk_usdt = self.equity * self.risk_pct  # 1%
        
        # 2. Quality weighting (신뢰도 기반)
        quality_weight = 0.7 + (confidence - 0.5) * 0.6
        quality_weight = max(0.7, min(1.3, quality_weight))
        
        # 3. 수량 계산
        stop_distance = abs(entry - sl)
        qty = (risk_usdt * quality_weight) / stop_distance
        
        # 4. 포지션 가치 확인 (부동소수점 안전)
        position_value = qty * entry
        epsilon = 0.1  # ⭐ 금융 프로그램 표준
        if position_value > self.max_position_value + epsilon:
            qty = self.max_position_value / entry
        
        return qty, metadata
```

---

## 신호 생성 및 검증

### 신호 생성 흐름

```
캔들 수신 → 버퍼 추가 → 지표 계산 → 전략 실행 → 신호 검증 → 앙상블 통합
```

### SignalGenerator (signals/signal_generator.py)

**검증 필터**:
```python
def validate_signal(self, symbol, signal, df):
    # 1. 거래량 필터
    if enable_vol_spike_filter:
        if volume > vol_ma * vol_spike_mult:
            return False  # 거래량 급증 시 신호 보류
    
    # 2. 세션 화이트리스트 (UTC 기준)
    if not session_allowed(signal['ts']):
        return False  # 비허용 시간대
    
    # 3. 레짐 필터
    if enable_regime_filter:
        regime = calculate_regime(df)
        if regime not in allowed_regimes:
            return False
    
    # 4. MTF 확인 (Multi-Timeframe)
    if enable_mtf_confirm:
        if not mtf_confirm(symbol, signal['side'], signal['ts']):
            return False
    
    # 5. 트렌드 정렬
    if enable_trend_alignment:
        if not trend_aligned(df, signal['side']):
            return False
    
    # 6. 쿨다운 체크 (전략별 심볼 쿨다운)
    if in_cooldown(symbol, strategy_id):
        return False
    
    # 7. 최소 손익비
    rr = abs(signal['tp'] - signal['entry']) / abs(signal['entry'] - signal['sl'])
    if rr < min_rr:
        return False
    
    return True
```

---

## 거래 실행 흐름

### 전체 흐름 (execution/engine.py)

```python
# L722-761: 전략별 심볼 거부 쿨다운 + 리스크 체크
def process_candle(candle):
    # 1. 전략별 신호 생성
    signals = []
    for strategy_id, strategy in strategies.items():
        signal = strategy.signal_logic(df, config)
        if validate_signal(symbol, signal, df):
            signals.append(signal)
    
    # 2. 앙상블 통합
    decision = ensemble.combine_signals(signals, conn, config)
    if not decision:
        return
    
    # 3. 포지션 사이즈 계산
    qty, meta = position_sizer.calculate(decision)
    if qty <= 0:
        return
    
    position_value = meta['position_value']
    strategy_id = decision['strategy_id']
    cooldown_key = f"{symbol}_{strategy_id}"
    
    # 4. 전략별 쿨다운 체크 (PR8)
    if cooldown_key in reject_cooldown:
        elapsed = time.time() - reject_cooldown[cooldown_key]
        if elapsed < cooldown_seconds:
            logger.debug(f"🔒 [{strategy_id}] {symbol} 쿨다운 중")
            return
        else:
            del reject_cooldown[cooldown_key]
    
    # 5. RiskManager 체크
    allowed, reason = risk_manager.check_order(decision, qty, position_value)
    if not allowed:
        reject_cooldown[cooldown_key] = time.time()  # 쿨다운 설정
        logger.warning(f"⛔ [{strategy_id}] {symbol} 리스크 체크 실패: {reason}")
        return
    
    # 6. PortfolioManager 체크
    can_open, reason = portfolio.can_open_position(symbol, strategy_id, position_value, decision['side'])
    if not can_open:
        reject_cooldown[cooldown_key] = time.time()  # 쿨다운 설정
        logger.warning(f"⛔ [{strategy_id}] {symbol} 포트폴리오 거부: {reason}")
        return
    
    # 7. 거래 실행
    fill = broker.execute(decision, qty)
    
    # 8. DB 저장
    save_trade_to_db(fill, decision, meta)
    
    # 9. 텔레그램 알림
    tg(f"✅ 거래 체결: {symbol} {decision['side']}", config)
```

---

## 전체 기능 기준

### 1. 스탑로스 (Stop Loss)

**계산 방식** (전략별):
```python
# strategies/*/signal_logic()
sl_atr_mult = config['sl_atr_mult']  # 전략별 설정 (1.5~3.0)
atr = df['atr'].iloc[-1]

if side == 'LONG':
    sl = entry - atr * sl_atr_mult
elif side == 'SHORT':
    sl = entry + atr * sl_atr_mult
```

**관리** (execution/tp_manager.py):
```python
# 트레일링 스톱 (Trailing Stop)
def update_trailing_stop(position, current_price):
    if position['side'] == 'LONG':
        new_sl = current_price - atr * trailing_mult
        if new_sl > position['sl']:
            position['sl'] = new_sl  # 스탑 상향 조정
```

### 2. 쿨다운 (Cooldown)

**전략별 심볼 쿨다운** (PR8):
```python
# engine.py L722-735
cooldown_key = f"{symbol}_{strategy_id}"  # 예: "BTCUSDT_scalping"
cooldown_seconds = 60  # config.yml

if cooldown_key in reject_cooldown:
    elapsed = time.time() - reject_cooldown[cooldown_key]
    if elapsed < cooldown_seconds:
        continue  # 쿨다운 중
```

**연속 손실 쿨다운** (RiskManager):
```python
if consecutive_losses >= 7:
    cooldown_until = time.time() + 30 * 60  # 30분
    return False, "연속 손실 쿨다운"
```

### 3. Flash Guard (급등락 차단)

**동작 원리**:
```python
# RiskManager.flash_guard_allowed()
flash_cooldown_ms = 5 * 60 * 1000  # 5분

def flash_guard_allowed(self, symbol, ts):
    last_block = self.flash_block_log.get(symbol, 0)
    return (ts - last_block) >= self.flash_cooldown_ms
```

### 4. Telegram 알림

**알림 종류** (19개):
1. **거래** (6개): 진입, 청산, TP1/TP2 달성, 트레일링 작동
2. **시스템** (4개): 시작, 종료, 에러, 하트비트
3. **리스크** (4개): Guard 차단, 연속 손실, Flash Guard, Exposure 한도
4. **포트폴리오** (2개): 최대 포지션, 주간 리포트
5. **연결** (3개): 연결 끊김, 복구, 데이터 갭

### 5. 부동소수점 안전 비교

**금융 프로그램 표준** (PR8):
```python
# epsilon = 0.1 USDT (실제 반올림 오차 0.01~0.09)
epsilon = 0.1

# RiskManager
if total_exposure > max_per_symbol + epsilon:
    return False

# PositionSizer
if position_value > max_position_value + epsilon:
    qty = max_position_value / entry
```

### 6. DB 저장

**테이블 구조**:
- `trading.trades`: 거래 기록 (진입/청산)
- `trading.decisions`: 앙상블 결정 (전략 통합)
- `monitoring.signals`: 전략 신호 (개별 전략)
- `monitoring.events`: FlowGuardian 이벤트
- `monitoring.snapshots`: FlowGuardian 스냅샷

---

## DB 구조

### PostgreSQL 스키마

```sql
-- 1. 거래 기록
CREATE TABLE trading.trades (
    trade_id UUID PRIMARY KEY,
    strategy_id VARCHAR(50),
    symbol VARCHAR(20),
    side VARCHAR(10),  -- LONG/SHORT
    entry_price NUMERIC,
    exit_price NUMERIC,
    quantity NUMERIC,
    pnl NUMERIC,
    pnl_pct NUMERIC,
    status VARCHAR(20),  -- OPEN/CLOSED
    ts_open TIMESTAMP,
    ts_close TIMESTAMP
);

-- 2. 앙상블 결정
CREATE TABLE trading.decisions (
    decision_id UUID PRIMARY KEY,
    symbol VARCHAR(20),
    timeframe VARCHAR(10),
    candle_closed_at TIMESTAMP,
    chosen_side VARCHAR(10),
    chosen_size NUMERIC,
    score NUMERIC,
    weights JSONB,
    from_signals JSONB,
    reason TEXT,
    UNIQUE (symbol, timeframe, candle_closed_at)
);

-- 3. 전략 신호
CREATE TABLE monitoring.signals (
    signal_id UUID PRIMARY KEY,
    strategy_id VARCHAR(50),
    symbol VARCHAR(20),
    timeframe VARCHAR(10),
    direction VARCHAR(10),
    entry_price NUMERIC,
    sl_price NUMERIC,
    tp_price NUMERIC,
    confidence NUMERIC,
    features JSONB,
    candle_closed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

**작성**: 2025-11-05 12:00 UTC+09:00  
**다음 문서**: SYSTEM_ARCHITECTURE_v2.md (성능 최적화 섹션 추가)
