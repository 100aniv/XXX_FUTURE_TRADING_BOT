# 📊 데이터베이스 스키마 가이드

**작성일**: 2025-10-14  
**버전**: v1.0

---

## 🗄️ 스키마 구조

```
trading_db
├── monitoring (모니터링 계층)
│   └── signals - 개별 전략 신호
├── trading (거래 실행 계층)
│   ├── decisions - 통합 결정 (앙상블)
│   ├── trades - 거래 기록
│   ├── positions - 현재 포지션
│   └── executions - 집행 로그
└── reporting (분석 계층)
    ├── strategy_performance - 전략별 성과
    └── daily_pnl - 일별 손익
```

---

## 📋 테이블 상세

### **1. monitoring.signals (모니터링 신호)**

개별 전략(scalping, daytrade, swing)에서 생성된 신호.

| 컬럼 | 타입 | 설명 | 제약 |
|------|------|------|------|
| `signal_id` | TEXT | 신호 고유 ID (UUID) | PRIMARY KEY |
| `strategy_id` | TEXT | 전략 ID | NOT NULL, 'scalping'\|'daytrade'\|'swing' |
| `bot_id` | TEXT | 봇 이름 | NOT NULL, 'SCALP'\|'INTRA'\|'SWING' |
| `symbol` | TEXT | 거래 심볼 | NOT NULL, 'BTCUSDT', 'ETHUSDT' 등 |
| `timeframe` | TEXT | 타임프레임 | NOT NULL, '1m', '5m', '15m' 등 |
| `candle_closed_at` | TIMESTAMPTZ | 캔들 종료 시각 | NOT NULL |
| `direction` | TEXT | 매매 방향 | NOT NULL, 'LONG'\|'SHORT'\|'FLAT' |
| `confidence` | NUMERIC | 신뢰도 (0~1) | 0 ≤ confidence ≤ 1 |
| `entry_price` | NUMERIC | 진입가 | |
| `sl_price` | NUMERIC | 손절가 | |
| `tp_price` | NUMERIC | 목표가 | |
| `atr` | NUMERIC | ATR 값 | |
| `leverage` | INTEGER | 레버리지 | |
| `features` | JSONB | 지표 (RSI, MACD 등) | |
| `created_at` | TIMESTAMPTZ | 생성 시각 | DEFAULT now() |

**멱등키 (중복 방지):**
```sql
UNIQUE(strategy_id, symbol, timeframe, candle_closed_at)
```
→ 동일 전략/심볼/타임프레임/캔들에 대해 **1건만** 저장

**인덱스:**
- `idx_signals_strategy_ts`: 전략별 시간순 조회
- `idx_signals_symbol_ts`: 심볼별 시간순 조회
- `idx_signals_created`: 최신 신호 조회

**예시:**
```sql
-- 최근 scalping 신호 조회
SELECT * FROM monitoring.signals 
WHERE strategy_id = 'scalping' 
ORDER BY created_at DESC 
LIMIT 10;

-- BTCUSDT의 최근 신호
SELECT strategy_id, direction, entry_price 
FROM monitoring.signals 
WHERE symbol = 'BTCUSDT' 
ORDER BY created_at DESC;
```

---

### **2. trading.decisions (통합 결정)**

앙상블 봇이 3개 전략 신호를 통합하여 생성한 최종 결정.

| 컬럼 | 타입 | 설명 | 제약 |
|------|------|------|------|
| `decision_id` | TEXT | 결정 고유 ID (UUID) | PRIMARY KEY |
| `symbol` | TEXT | 거래 심볼 | NOT NULL |
| `timeframe` | TEXT | 타임프레임 | NOT NULL |
| `candle_closed_at` | TIMESTAMPTZ | 캔들 종료 시각 | NOT NULL |
| `chosen_side` | TEXT | 최종 선택 방향 | NOT NULL, 'LONG'\|'SHORT'\|'FLAT' |
| `chosen_size` | NUMERIC | 포지션 크기 | NOT NULL |
| `score` | NUMERIC | 통합 점수 | NOT NULL |
| `weights` | JSONB | 전략별 가중치 | NOT NULL |
| `from_signals` | JSONB | 원천 신호 ID 목록 | NOT NULL |
| `reason` | TEXT | 결정 이유 | |
| `created_at` | TIMESTAMPTZ | 생성 시각 | DEFAULT now() |

**멱등키:**
```sql
UNIQUE(symbol, timeframe, candle_closed_at)
```
→ 동일 심볼/타임프레임/캔들에 대해 **1건만**

**예시:**
```sql
-- BTCUSDT 통합 결정 조회
SELECT decision_id, chosen_side, score, weights 
FROM trading.decisions 
WHERE symbol = 'BTCUSDT' 
ORDER BY created_at DESC;
```

---

### **3. trading.trades (거래 기록)**

실제 체결된 거래 내역.

| 컬럼 | 타입 | 설명 | 제약 |
|------|------|------|------|
| `trade_id` | TEXT | 거래 고유 ID | PRIMARY KEY |
| `decision_id` | TEXT | 결정 ID (FK) | REFERENCES decisions |
| `symbol` | TEXT | 거래 심볼 | NOT NULL |
| `side` | TEXT | 매매 방향 | 'LONG'\|'SHORT' |
| `entry_price` | NUMERIC | 진입가 | NOT NULL |
| `exit_price` | NUMERIC | 청산가 | |
| `quantity` | NUMERIC | 수량 | NOT NULL |
| `leverage` | INTEGER | 레버리지 | NOT NULL |
| `sl_price` | NUMERIC | 손절가 | |
| `tp_price` | NUMERIC | 목표가 | |
| `ts_open` | TIMESTAMPTZ | 진입 시각 | NOT NULL |
| `ts_close` | TIMESTAMPTZ | 청산 시각 | |
| `pnl` | NUMERIC | 손익 (USDT) | |
| `pnl_pct` | NUMERIC | 손익률 (%) | |
| `fees` | NUMERIC | 수수료 | DEFAULT 0 |
| `status` | TEXT | 상태 | 'OPEN'\|'CLOSED'\|'CANCELLED' |
| `strategy_id` | TEXT | 전략 ID | NOT NULL |
| `exit_reason` | TEXT | 청산 이유 | TP1/TP2/SL/MANUAL 등 |

**예시:**
```sql
-- 승률 계산
SELECT 
  strategy_id,
  COUNT(CASE WHEN pnl > 0 THEN 1 END) * 100.0 / COUNT(*) as win_rate,
  AVG(pnl) as avg_pnl,
  SUM(pnl) as total_pnl
FROM trading.trades 
WHERE status = 'CLOSED'
GROUP BY strategy_id;
```

---

### **4. trading.executions (집행 로그)**

결정이 실제로 집행된 기록 (멱등성 보장).

| 컬럼 | 타입 | 설명 | 제약 |
|------|------|------|------|
| `execution_id` | TEXT | 집행 ID | PRIMARY KEY |
| `decision_id` | TEXT | 결정 ID | |
| `signal_id` | TEXT | 신호 ID | |
| `ts_executed` | TIMESTAMPTZ | 집행 시각 | NOT NULL |
| `trade_id` | TEXT | 거래 ID | |
| `status` | TEXT | 상태 | 'SUCCESS'\|'FAILED'\|'SKIPPED' |
| `error_msg` | TEXT | 에러 메시지 | |

**멱등키:**
```sql
UNIQUE(decision_id, ts_executed)
```
→ 동일 결정을 중복 집행 방지

---

## 🔐 멱등성 (Idempotency) 전략

### **레벨 1: 신호 생성**
```sql
UNIQUE(strategy_id, symbol, timeframe, candle_closed_at)
```
- 재시작 시 같은 캔들 신호 중복 방지

### **레벨 2: 통합 결정**
```sql
UNIQUE(symbol, timeframe, candle_closed_at)
```
- 동일 캔들에 대해 결정 1건만

### **레벨 3: 집행**
```sql
UNIQUE(decision_id, ts_executed)
```
- 동일 결정 중복 집행 방지

---

## 📈 성능 최적화

### **인덱스 전략**
```sql
-- 시간 범위 조회 (최신순)
CREATE INDEX idx_signals_created ON monitoring.signals (created_at DESC);
CREATE INDEX idx_trades_ts_open ON trading.trades (ts_open DESC);

-- 전략별 조회
CREATE INDEX idx_signals_strategy_ts ON monitoring.signals (strategy_id, created_at DESC);
CREATE INDEX idx_trades_strategy ON trading.trades (strategy_id, ts_open DESC);

-- 심볼별 조회
CREATE INDEX idx_signals_symbol_ts ON monitoring.signals (symbol, created_at DESC);
CREATE INDEX idx_trades_symbol_ts ON trading.trades (symbol, ts_open DESC);

-- 상태 조회
CREATE INDEX idx_trades_status ON trading.trades (status, ts_open DESC);
```

### **JSONB 인덱스 (선택적)**
```sql
-- features 내부 특정 필드 조회 시
CREATE INDEX idx_signals_features_rsi ON monitoring.signals 
USING gin ((features->'rsi'));
```

---

## 🔧 유지보수

### **오래된 데이터 정리**
```sql
-- 90일 이전 신호 삭제
DELETE FROM monitoring.signals 
WHERE created_at < NOW() - INTERVAL '90 days';

-- 1년 이전 종료된 거래 아카이브
CREATE TABLE trading.trades_archive AS 
SELECT * FROM trading.trades 
WHERE status = 'CLOSED' AND ts_close < NOW() - INTERVAL '1 year';

DELETE FROM trading.trades 
WHERE status = 'CLOSED' AND ts_close < NOW() - INTERVAL '1 year';
```

### **백업**
```bash
# 전체 백업
docker exec future_alarm_bot_postgres pg_dump -U trading_user trading_db > backup.sql

# 복원
docker exec -i future_alarm_bot_postgres psql -U trading_user trading_db < backup.sql
```

---

## 📊 유용한 쿼리

### **오늘 신호 통계**
```sql
SELECT 
  strategy_id,
  COUNT(*) as total_signals,
  COUNT(CASE WHEN direction = 'LONG' THEN 1 END) as long_signals,
  COUNT(CASE WHEN direction = 'SHORT' THEN 1 END) as short_signals
FROM monitoring.signals 
WHERE DATE(created_at) = CURRENT_DATE
GROUP BY strategy_id;
```

### **전략별 승률**
```sql
SELECT 
  strategy_id,
  COUNT(*) as total_trades,
  ROUND(AVG(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 100, 2) as win_rate,
  ROUND(AVG(pnl), 2) as avg_pnl,
  ROUND(SUM(pnl), 2) as total_pnl
FROM trading.trades 
WHERE status = 'CLOSED'
GROUP BY strategy_id;
```

### **최근 1시간 활동**
```sql
SELECT 
  'signals' as type, 
  COUNT(*) as count 
FROM monitoring.signals 
WHERE created_at > NOW() - INTERVAL '1 hour'
UNION ALL
SELECT 
  'decisions', 
  COUNT(*) 
FROM trading.decisions 
WHERE created_at > NOW() - INTERVAL '1 hour'
UNION ALL
SELECT 
  'trades', 
  COUNT(*) 
FROM trading.trades 
WHERE ts_open > NOW() - INTERVAL '1 hour';
```

---

**작성자**: AI Assistant  
**마지막 업데이트**: 2025-10-14
