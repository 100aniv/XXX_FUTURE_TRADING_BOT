# trading.trades 테이블 스키마

## 개요

백테스트, 페이퍼, 라이브 거래 내역을 저장하는 중앙 테이블.

## 스키마 (21개 컬럼)

| #  | Column Name   | Data Type                     | Nullable | Default       | 설명                                    |
|----|---------------|-------------------------------|----------|---------------|-----------------------------------------|
| 1  | trade_id      | text                          | NO ⚠️    | -             | 거래 고유 ID (UUID)                     |
| 2  | decision_id   | text                          | YES      | -             | 앙상블 결정 ID (선택)                   |
| 3  | symbol        | text                          | NO ⚠️    | -             | 심볼 (BTCUSDT 등)                       |
| 4  | side          | text                          | NO ⚠️    | -             | 방향 (LONG, SHORT)                      |
| 5  | entry_price   | numeric                       | NO ⚠️    | -             | 진입 가격                               |
| 6  | exit_price    | numeric                       | YES      | -             | 청산 가격 (OPEN 시 NULL)                |
| 7  | quantity      | numeric                       | NO ⚠️    | -             | 수량                                    |
| 8  | leverage      | integer                       | NO ⚠️    | -             | 레버리지                                |
| 9  | sl_price      | numeric                       | YES      | -             | 손절 가격                               |
| 10 | tp_price      | numeric                       | YES      | -             | 익절 가격                               |
| 11 | ts_open       | timestamp with time zone      | NO ⚠️    | -             | 진입 시간                               |
| 12 | ts_close      | timestamp with time zone      | YES      | -             | 청산 시간 (OPEN 시 NULL)                |
| 13 | pnl           | numeric                       | YES      | -             | 손익 (달러)                             |
| 14 | pnl_pct       | numeric                       | YES      | -             | 손익 (퍼센트)                           |
| 15 | fees          | numeric                       | YES      | 0             | 수수료                                  |
| 16 | status        | text                          | NO ⚠️    | -             | 상태 (OPEN, CLOSED)                     |
| 17 | strategy_id   | text                          | NO ⚠️    | -             | 전략 ID (scalping, daytrade 등)        |
| 18 | exit_reason   | text                          | YES      | -             | 청산 사유 (SL, TP, TIME 등)            |
| 19 | created_at    | timestamp with time zone      | NO ⚠️    | now()         | 레코드 생성 시간                        |
| 20 | trial_id      | character varying             | YES      | -             | 백테스트 시행 ID (선택)                |
| 21 | mode          | text                          | NO ⚠️    | 'paper'::text | 실행 모드 (backtest_clean, paper, live)|

## NOT NULL 제약 컬럼 (11개)

필수로 값이 채워져야 하는 컬럼들:

1. **trade_id** - 거래 고유 ID
2. **symbol** - 심볼
3. **side** - 방향 (LONG/SHORT)
4. **entry_price** - 진입 가격
5. **quantity** - 수량
6. **leverage** - 레버리지
7. **ts_open** - 진입 시간
8. **status** - 상태 (OPEN/CLOSED)
9. **strategy_id** - 전략 ID
10. **created_at** - 레코드 생성 시간 (자동)
11. **mode** - 실행 모드 (기본값: 'paper')

## PHASE8-2c 수정 내역

### 문제 1: INSERT 문 컬럼 누락

기존 INSERT 문에서 `decision_id` 컬럼이 빠져있어, 모든 값이 한 칸씩 밀려서 저장되었음.
결과적으로 NOT NULL 제약이 있는 `mode` 컬럼에 NULL이 들어가서 에러 발생.

### 문제 2: mode CHECK 제약

`trades_mode_check` 제약이 `['paper', 'live', 'backtest']`만 허용하고 `'backtest_clean'`을 불허함.

**에러 로그 예시:**
```
DETAIL: Failing row contains (dabacf96-973e-461b-ba4c-6dfc118d7d0e, null, BTCUSDT, SHORT, 63702.133, ...)
```

### 해결

`execution/engine.py`의 `_save_trade_to_db()` 함수 수정:

1. **decision_id 컬럼 추가** (nullable이므로 NULL 삽입)
2. **모든 21개 컬럼 명시적 지정**
3. **각 NOT NULL 컬럼에 값 보장**:
   - `trade_id`: position_id (UUID)
   - `symbol`: 심볼
   - `side`: LONG/SHORT
   - `entry_price`: 진입 가격
   - `quantity`: 수량
   - `leverage`: 레버리지
   - `ts_open`: NOW() (자동)
   - `status`: "OPEN"
   - `strategy_id`: 전략 ID
   - `created_at`: NOW() (자동)
   - `mode`: backtest_clean / paper / live

### 수정 후 INSERT 문

```sql
INSERT INTO trading.trades (
    trade_id, decision_id, symbol, side,
    entry_price, exit_price, quantity, leverage,
    sl_price, tp_price, ts_open, ts_close,
    pnl, pnl_pct, fees, status,
    strategy_id, exit_reason, created_at, trial_id, mode
) VALUES (
    %s, %s, %s, %s,
    %s, %s, %s, %s,
    %s, %s, NOW(), %s,
    %s, %s, %s, %s,
    %s, %s, NOW(), %s, %s
)
```

### 주요 변경점

**코드 수정 (execution/engine.py):**
| Before | After | 설명 |
|--------|-------|------|
| 컬럼 12개 명시 | **컬럼 21개 명시** | 모든 컬럼 명시적 지정 |
| decision_id 누락 | **decision_id 추가 (NULL)** | 컬럼 순서 정렬 |
| nullable 컬럼 생략 | **nullable 컬럼도 명시 (NULL)** | 명확성 향상 |
| 로그 없음 | **성공/실패 로그 추가** | 디버깅 편의성 |

**DB 제약 수정 (trading.trades):**

```sql
-- Before
ALTER TABLE trading.trades 
ADD CONSTRAINT trades_mode_check 
CHECK (mode = ANY (ARRAY['paper'::text, 'live'::text, 'backtest'::text]));

-- After
ALTER TABLE trading.trades 
ADD CONSTRAINT trades_mode_check 
CHECK (mode = ANY (ARRAY['paper'::text, 'live'::text, 'backtest'::text, 'backtest_clean'::text]));
```

**변경 이유**: backtest_clean 모드 지원 추가

## 사용 예시

### 백테스트 거래 저장

```python
_save_trade_to_db(
    position_id="uuid-1234",
    symbol="BTCUSDT",
    side="LONG",
    entry_price=63000,
    qty=0.1,
    sl_price=62500,
    tp_price=64000,
    strategy_id="scalping",
    mode="backtest_clean",  # ⭐ 백테스트 모드
    leverage=10,
    trial_id=None
)
```

### 조회 예시

```sql
-- 백테스트 거래만 조회
SELECT * FROM trading.trades 
WHERE mode = 'backtest_clean' 
ORDER BY ts_open DESC;

-- 특정 run_id의 거래 조회 (trial_id 활용)
SELECT * FROM trading.trades 
WHERE mode = 'backtest_clean' 
AND trial_id = '20251114_173326_3mto'
ORDER BY ts_open DESC;

-- OPEN 포지션 조회
SELECT * FROM trading.trades 
WHERE status = 'OPEN' 
AND mode = 'paper'
ORDER BY ts_open DESC;
```

## 참고

- 모든 NOT NULL 제약 컬럼은 반드시 값이 있어야 INSERT 성공
- `ts_open`, `created_at`은 NOW()로 자동 채워짐
- `mode`는 기본값 'paper'이지만 명시적 지정 권장
- OPEN 상태 거래는 `exit_price`, `ts_close`, `exit_reason`이 NULL
- CLOSED 상태 거래는 UPDATE로 위 필드들이 채워짐

---

*Updated: 2025-11-14 (PHASE8-2c)*
