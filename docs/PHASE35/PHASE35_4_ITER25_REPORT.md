# PHASE35-4 ITER25 REPORT: DB 스키마 문제 해결 완료

**작성일**: 2025-12-18  
**담당**: Cascade AI  
**결과**: ⚠️ **PARTIAL PASS** (DB 스키마 문제 100% 해결, E2E trades>0 미달성)

---

## 📋 Executive Summary

### ITER25 Goals vs Results

| Goal | 상태 | 비고 |
|------|------|------|
| G1: "relation 'trades' does not exist" 근본 원인 제거 | ✅ **PASS** | search_path 문제 확정 + qualified query 통일 |
| G2: L4_ultra_debug DB trades>0 | ❌ FAIL | 신호 생성 실패 (데이터/config 차이) |
| G3: Report 생성 | ❌ FAIL | trades=0으로 미생성 |
| G4: 실행 증거 저장 | ✅ **PASS** | iter25_results.json + db_introspection.json |

### 핵심 성과

**✅ DB 스키마 문제 100% 해결**:
- **근본 원인 확정**: search_path에 trading 미포함 → unqualified 쿼리 실패
- **수정 방안**: 모든 쿼리를 `trading.trades` (qualified)로 통일
- **재발 방지**: Contract Tests 10/10 PASS (qualified query 검증)

**❌ E2E trades>0 미달성**:
- DB 연결 성공, qualified query 정상 작동
- 신호 생성 단계에서 차단 (ITER24와 데이터 기간 차이)
- 이는 DB 스키마 문제가 아닌 **전략/데이터 문제**

---

## 🔍 근본 원인 분석 (ROOT SCAN)

### STEP 2: DB Introspection 결과

**DB 상태 (실행 전)**:
```json
{
  "current_database": "trading_db",
  "search_path": "\"$user\", public",
  "current_schema": "public",
  "trades_unqualified": null,
  "trades_trading_schema": "trading.trades",
  "all_schemas": ["monitoring", "public", "reporting", "trading", "tuning"],
  "trading_schema_tables": ["decisions", "executions", "portfolio_state", "positions", "risk_state", "trades"]
}
```

**핵심 발견**:
1. ✅ `trading.trades` 테이블은 **존재함**
2. ❌ `search_path`: `"$user", public` → **trading 미포함**
3. ❌ `to_regclass('trades')`: **null** (unqualified로는 못 찾음)

### 코드 분석

**ITER24 runner (수정 전)**:
```python
# Line 329, 336, 342
cur.execute("SELECT COUNT(*) FROM trades WHERE trial_id = %s", (trial_id,))
```
→ ❌ **unqualified query** + search_path에 trading 없음 = "relation 'trades' does not exist"

**execution/engine.py (정상)**:
```python
# Line 2933
INSERT INTO trading.trades (...)
```
→ ✅ **qualified query** (이미 정상)

### 근본 원인 (1줄)

```
코드가 "FROM trades" (unqualified)를 실행하지만 search_path에 trading이 없어서 찾지 못함
```

---

## 🔧 구현 내용 (STEP 3)

### 수정 전략: Option 1 (Qualified Query 통일)

**근거**:
- search_path 의존성 제거 (환경 독립적)
- 명시적 스키마 지정 (예측 가능성 ↑)
- 보안 및 유지보수성 향상

### 수정 사항

#### 1. ITER24 runner 수정 (`scripts/phase35/run_iter24_signal_diag_ultra_debug.py`)

**Before**:
```python
cur.execute("SELECT COUNT(*) FROM trades WHERE trial_id = %s", (trial_id,))
```

**After**:
```python
# ITER25: qualified query
cur.execute("SELECT COUNT(*) FROM trading.trades WHERE trial_id = %s", (trial_id,))
```

**영향 범위**: 총 4개 쿼리 (total, closed, long, short trades)

#### 2. ITER25 runner 생성 (`scripts/phase35/run_iter25_db_schema_e2e.py`)

**기능**:
- `ensure_trading_schema()`: trading 스키마 및 trades 테이블 생성 보장
- `run_l4_backtest()`: L4_ultra_debug 백테스트 실행
- `collect_db_evidence_iter25()`: qualified query로 DB 증거 수집
- `check_ac()`: AC1~AC4 체크

**핵심 코드**:
```python
def ensure_trading_schema() -> bool:
    """trading 스키마 및 trades 테이블 존재 보장"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1. trading 스키마 생성
            cur.execute("CREATE SCHEMA IF NOT EXISTS trading;")
            
            # 2. trading.trades 테이블 생성 (init_db.sql 기준)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS trading.trades(
                  trade_id TEXT PRIMARY KEY,
                  symbol TEXT NOT NULL,
                  ...
                  trial_id TEXT,
                  mode TEXT DEFAULT 'paper'
                );
            """)
            
            # 3. 필수 인덱스 생성
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_trial_id 
                ON trading.trades (trial_id);
            """)
```

#### 3. DB Introspection 스크립트 (`scripts/phase35/db_introspect_iter25.py`)

**목적**: DB 상태를 정확히 파악하여 원인 확정

**체크 항목**:
- `current_database`, `search_path`, `current_schema`
- `to_regclass('trades')` (unqualified)
- `to_regclass('trading.trades')` (qualified)
- `information_schema.tables` (trades 테이블 검색)
- 각 스키마별 테이블 목록
- trading.trades count (존재 시)

**결과**: `artifacts/phase35/iter25/db_introspection.json`

#### 4. Contract Tests (`tests/test_phase35_iter25_db_schema_contract.py`)

**검증 항목** (10개 테스트):
1. `ensure_trading_schema()`가 "CREATE SCHEMA IF NOT EXISTS trading" 포함
2. `ensure_trading_schema()`가 "CREATE TABLE IF NOT EXISTS trading.trades" 포함
3. ITER25 runner의 `collect_db_evidence_iter25()`가 "FROM trading.trades" 사용
4. ITER24 runner (수정 후)의 `collect_db_evidence()`가 "FROM trading.trades" 사용
5. trades 테이블이 필수 컬럼 (trade_id, symbol, trial_id 등) 포함
6. trial_id 인덱스 존재
7. DB introspection이 `to_regclass('trading.trades')` 체크
8. ITER25 runner의 `check_ac()`가 AC1~AC4 체크
9. `init_db.sql`이 trading 스키마 정의
10. `execution/engine.py`의 `save_trade_to_db()`가 "INSERT INTO trading.trades" 사용

**결과**: **10/10 PASS** ✅

---

## 📊 실행 결과 (STEP 5)

### ITER25 Runner 실행

**환경**:
- Git commit: e19e9aef
- Artifacts: `C:\work\XXX_FUTURE_TRADING_BOT\artifacts\phase35\iter25`
- 실행 시간: 808.12초 (13.5분)

**실행 흐름**:
1. ✅ DB Introspection 완료
2. ✅ `ensure_trading_schema()` 실행 (스키마/테이블 확인)
3. ✅ L4_ultra_debug 백테스트 실행 (673 candles, 622 evaluated)
4. ❌ DB trades: 0 (신호 생성 실패)
5. ❌ Report 미생성 (trades=0)

**L4 DecisionTrace TopN**:
1. SUB_REVERSION_NO_EXTREME: 37,092회 (33.9%)
2. SUB_REVERSION_REGIME_CHOP: 26,002회 (23.8%)
3. ENSEMBLE_NO_CONSENSUS_L1_S0_F2: 14,505회 (13.3%)
4. ENSEMBLE_NO_CONSENSUS_L0_S1_F2: 12,477회 (11.4%)
5. SUB_BREAKOUT_NO_BREAKOUT: 8,990회 (8.2%)

→ reversion/breakout sub-model이 대부분 FLAT

### AC 체크 결과

| AC | 설명 | 상태 | 비고 |
|----|------|------|------|
| AC1 | trading.trades 테이블 존재 | ✅ **PASS** | introspection 확인 |
| AC2 | L4 DB trades>0 | ❌ FAIL | 신호 생성 실패 |
| AC3 | Report 파일 생성 | ❌ FAIL | trades=0으로 미생성 |
| AC4 | 실행 증거 저장 | ✅ **PASS** | iter25_results.json |

---

## 📁 산출물

1. path: `scripts/phase35/run_iter24_signal_diag_ultra_debug.py` (수정)
   raw: https://raw.githubusercontent.com/100aniv/XXX_FUTURE_TRADING_BOT/HEAD/scripts/phase35/run_iter24_signal_diag_ultra_debug.py

2. path: `scripts/phase35/run_iter25_db_schema_e2e.py` (신규)
   raw: https://raw.githubusercontent.com/100aniv/XXX_FUTURE_TRADING_BOT/HEAD/scripts/phase35/run_iter25_db_schema_e2e.py

3. path: `scripts/phase35/db_introspect_iter25.py` (신규)
   raw: https://raw.githubusercontent.com/100aniv/XXX_FUTURE_TRADING_BOT/HEAD/scripts/phase35/db_introspect_iter25.py

4. path: `tests/test_phase35_iter25_db_schema_contract.py` (신규)
   raw: https://raw.githubusercontent.com/100aniv/XXX_FUTURE_TRADING_BOT/HEAD/tests/test_phase35_iter25_db_schema_contract.py

5. path: `artifacts/phase35/iter25/db_introspection.json`
6. path: `artifacts/phase35/iter25/iter25_results.json`

---

## 📝 결론

### 판정: ⚠️ **PARTIAL PASS**

**성공 (DB 스키마 문제 100% 해결)**:
1. ✅ **근본 원인 확정**: search_path에 trading 미포함 → unqualified 쿼리 실패
2. ✅ **수정 완료**: 모든 쿼리를 `trading.trades` (qualified)로 통일
3. ✅ **재발 방지**: Contract Tests 10/10 PASS
4. ✅ **DB 연결 성공**: "relation 'trades' does not exist" 에러 0건

**실패 (E2E trades>0 미달성)**:
- ❌ L4_ultra_debug 백테스트에서 trades=0
- 원인: 신호 생성 단계에서 차단 (DecisionTrace TopN 참고)
- 분석: ITER24 SignalProbe (특정 기간)와 ITER25 백테스트 (최근 7일)의 데이터 기간 차이

### ITER24 vs ITER25 비교

| 항목 | ITER24 | ITER25 |
|------|--------|--------|
| 목표 | trades=0 근본원인 확정 | DB 스키마 문제 해결 |
| DB 에러 | "relation 'trades' does not exist" | **에러 0건** ✅ |
| search_path | 무관 | trading 미포함 확인 |
| 쿼리 방식 | unqualified (일부) | **qualified 통일** ✅ |
| L4 SignalProbe | LONG=372, SHORT=251 | (미실행) |
| L4 Backtest | DB 에러로 미확인 | **DB 정상, trades=0** |

### 재발 방지 포인트

**SSOT 원칙**:
1. 모든 SQL 쿼리는 **qualified (schema.table)** 사용
2. search_path 의존 금지
3. init_db.sql 스키마 정의를 SSOT로 사용

**검증 체계**:
- Contract Tests: qualified query 검증
- DB Introspection: 실행 전 상태 확인
- 문서화: 근본 원인 및 수정 방안 명시

---

## 🚀 NEXT: ITER26 (E2E trades>0 달성)

**단일 액션**: ITER24 SignalProbe와 동일한 데이터 구간으로 백테스트 재실행

**목표**:
- ITER24에서 확인한 신호 생성 능력 (LONG=372, SHORT=251) 활용
- 동일 기간 (특정 7일)으로 백테스트 실행
- AC2 ✅ 달성: DB trades>0 (E2E 완료)

**예상 결과**:
- AC1 ✅ (이미 PASS)
- AC2 ✅ (데이터 기간 일치)
- AC3 ✅ (trades>0이면 report 생성)
- AC4 ✅ (이미 PASS)
