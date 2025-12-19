# PHASE35-4 ITER27 REPORT: E2E Trades DB Persist Fix

**작성일**: 2025-12-19  
**담당**: Cascade AI  
**결과**: ✅ **PASS** (trades=88, AC 100% 달성)

---

## 📋 Executive Summary

### ITER27 Goals vs Results

| Goal | 상태 | 비고 |
|------|------|------|
| G1: trade DB persist 파이프라인 근본 원인 확정 | ✅ **PASS** | numpy 타입 변환 문제 |
| G2: trading.trades > 0 | ✅ **PASS** | **88건** |
| G3: persist_trace 계측 | ✅ **PASS** | db_persist_called=88, db_insert_success=88 |
| G4: Report 생성 | ✅ **PASS** | backtest_20251219_130931.json |

---

## 🔍 ROOT SCAN 결과

### 근본 원인: numpy 타입이 SQL에 문자열로 전달됨

```
psycopg2.errors.InvalidSchemaName: schema "np" does not exist
LINE 11: np.float64(94884.12285714287), np.fl...
```

**문제 지점**: `save_trade_to_db` 함수에서 `sl_price`, `tp_price` 등이 `numpy.float64` 타입으로 전달됨

**원인 체인**:
1. 전략에서 sl/tp 계산 시 numpy 연산 사용
2. `decision.get("sl")`, `decision.get("tp")`가 numpy.float64 반환
3. psycopg2가 numpy 타입을 Python native로 변환하지 못함
4. SQL에 `np.float64(...)` 문자열이 그대로 삽입됨
5. PostgreSQL이 "np" 스키마를 찾지 못해 에러

### DB Persist 경로 분석

| 지점 | 파일/라인 | 조건 | 호출 여부 |
|------|-----------|------|-----------|
| 신호 생성 | engine.py:1400+ | 전략 평가 | ✅ |
| risk.check_order | engine.py:2266 | in_cooldown=False | ✅ |
| broker.execute | engine.py:2381 | 위 조건 통과 | ✅ |
| save_trade_to_db | engine.py:2421 | broker.execute 성공 | ✅ (수정 후) |

---

## 🔧 구현 내용 (FIX)

### ITER27 FIX: numpy 타입을 Python native로 변환

`@/execution/engine.py:2928-2941`
```python
def save_trade_to_db(...):
    try:
        # ⭐ ITER27 FIX: numpy 타입을 Python native 타입으로 변환
        def to_native(val):
            if val is None:
                return None
            if hasattr(val, 'item'):  # numpy scalar
                return val.item()
            return float(val) if isinstance(val, (int, float)) else val
        
        entry_price = to_native(entry_price)
        qty = to_native(qty)
        sl_price = to_native(sl_price)
        tp_price = to_native(tp_price)
        leverage = int(leverage) if leverage is not None else 1
```

### persist_trace 계측

ITER27 runner에서 save_trade_to_db 호출을 계측:

```python
PERSIST_TRACE = defaultdict(int)

def instrumented_save_trade_to_db(*args, **kwargs):
    inc_trace("db_persist_called")
    result = _original_save_trade_to_db(*args, **kwargs)
    inc_trace("db_insert_success")
    return result
```

---

## 📊 실행 결과

### persist_trace

```json
{
  "db_persist_called": 88,
  "db_insert_success": 88
}
```

### DB 증거

```
trading.trades: 88 ✅
trading.executions: 0 (미사용)
trading.decisions: 0 (미사용)
```

### 최근 trades 샘플

| trade_id | symbol | side | entry_price | status |
|----------|--------|------|-------------|--------|
| 3b659de7... | BTCUSDT | LONG | 94316.40 | CLOSED |
| 74da54f0... | BTCUSDT | LONG | 94727.36 | CLOSED |
| c6880488... | BTCUSDT | LONG | 95428.54 | CLOSED |
| b183350b... | BTCUSDT | LONG | 94947.46 | CLOSED |
| bb340ea6... | BTCUSDT | SHORT | 95539.65 | CLOSED |

---

## 🔒 AC 체크리스트

| AC | 내용 | 상태 | 값 |
|---|---|---|---|
| AC1 | DB 스키마 존재 | ✅ PASS | trading.trades 존재 |
| AC2 | trades > 0 | ✅ PASS | **88건** |
| AC3 | persist_trace 유효 | ✅ PASS | called=88, success=88 |
| AC4 | Report 생성 | ✅ PASS | backtest_20251219_130931.json |

---

## 📁 산출물

1. `execution/engine.py` - numpy 타입 변환 수정 (Line 2928-2941)
2. `scripts/phase35/run_iter27_persist_trace.py` - persist_trace 계측 runner
3. `tests/test_phase35_iter27_persist_contract.py` - 재발 방지 계약 테스트 (8개)
4. `artifacts/phase35/iter27/iter27_results.json` - 실행 결과
5. `artifacts/phase35/iter27/persist_trace.json` - 계측 결과

---

## 🧪 테스트 결과

| 테스트 | 결과 |
|--------|------|
| ITER26 Contract Tests | 9/9 PASS |
| ITER27 Contract Tests | 8/8 PASS |
| **Total** | **17/17 PASS** |

---

## 📝 결론

### 판정: ✅ **PASS**

**ITER24~26에서 지속된 trades=0 문제 해결!**

**근본 원인**: numpy.float64 타입이 PostgreSQL에 전달될 때 문자열로 변환되어 SQL 에러 발생

**수정**: `save_trade_to_db`에서 모든 숫자 파라미터를 Python native 타입으로 변환

**재발 방지**: 계약 테스트 8개 추가 (numpy 타입 변환 검증)

### ITER24 → ITER27 진전

| 항목 | ITER24 | ITER25 | ITER26 | ITER27 |
|------|--------|--------|--------|--------|
| DB 에러 | UndefinedTable | ✅ 해결 | ✅ | ✅ |
| 캔들 구간 SSOT | ❌ | ❌ | ✅ 통합 | ✅ |
| numpy 변환 | ❌ 미인지 | ❌ 미인지 | ❌ 미인지 | ✅ 해결 |
| trades>0 | ❌ (0) | ❌ (0) | ❌ (0) | ✅ **(88)** |

---

## 🚀 NEXT

ITER27 완료로 E2E trades DB persist 문제 종결.

다음 단계:
- PHASE35-4 후속: 성능 최적화, 더 많은 심볼/전략 테스트
- 또는 새로운 PHASE 진행
