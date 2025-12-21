# ROOT SCAN: 실제 DB Insert 함수 확정

## 결론
**실제 INSERT 함수**: `execution.engine.save_trade_to_db` (line 2921)

## 증거
1. **함수 정의**: `execution/engine.py:2921-2990`
   - `def save_trade_to_db(position_id, symbol, side, ...)`
   - `INSERT INTO trading.trades` 쿼리 실행 (line 2957)

2. **호출 위치**: `execution/engine.py:1679`
   - `save_trade_to_db(...)` 호출 (포지션 청산 후)

3. **Import 경로**: `execution.engine`
   - 다른 모듈에서 `from execution.engine import save_trade_to_db` 사용

## SSOT 계측 위치
- **Target**: `execution.engine.save_trade_to_db` 함수
- **Method**: Monkey-patch로 try/except 래핑
- **Fields**: `db_persist_called`, `db_insert_success`, `db_insert_fail`, `last_exception`
