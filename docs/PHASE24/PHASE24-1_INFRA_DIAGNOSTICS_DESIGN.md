# PHASE24-1: Full Infra Diagnostics - 설계 문서

**Date**: 2025-12-02  
**Status**: 🔄 IN PROGRESS  
**Phase**: PHASE24-1 – Full Infra Diagnostics (DB + Redis + FlowGuardian)  
**Purpose**: DB cleanup 안정성 확보 및 통합 인프라 진단 체계 확립

---

## 1. 목적 (Purpose)

### 1.1 주요 목표
- **DB Cleanup 안정성 확보**: Postgres DELETE 후 trades 재등장 현상 근본 해결
- **통합 인프라 진단 스크립트**: DB/Redis/FlowGuardian 상태를 한 번에 점검하는 pre-flight check 도구 추가
- **1H PAPER 인프라 검증**: Ensemble V2 기반 PAPER 실행으로 전체 인프라 레벨 안정성 확인

### 1.2 배경
**PHASE24-0 완료 사항:**
- Redis 연결 안정화 ✅ (환경변수 추가, 재시도 로직, 2H PAPER에서 Redis ERROR 0건)
- Config 파일 템플릿 제거 ✅
- clean_state_complete.py Redis 재시도 로직 ✅

**미해결 이슈 (PHASE24-0 범위 밖):**
- **Postgres DELETE 후 trades 재등장**: `clean_state_complete.py` 실행 후 새 연결로 재확인 시 DELETE된 trades가 다시 나타남
  - 예: "After DELETE: 0 trades" → commit → "After COMMIT (new connection): 63 trades"
  - 추정 원인: Transaction isolation level, connection pooling, 또는 미완료 트랜잭션

- **통합 인프라 진단 도구 부재**: 현재는 개별 스크립트(Redis 에러 카운터, PAPER 결과 분석)만 존재, pre-flight check 없음

### 1.3 PHASE24-1 vs PHASE24-0 차이점
| 항목 | PHASE24-0 | PHASE24-1 |
|------|-----------|-----------|
| 초점 | Redis 연결/초기화 안정화 | DB cleanup + 전체 인프라 진단 |
| 범위 | Redis 관련 에러 0건 달성 | DB + Redis + FlowGuardian 통합 점검 |
| 산출물 | Redis hardening 코드 + 2H PAPER | DB cleanup 헬퍼 + 인프라 진단 스크립트 + 1H PAPER |
| Out-of-Scope | DB cleanup 문제 | 전략 튜닝, 멀티 심볼, 성능 최적화 (PHASE25+) |

---

## 2. AS-IS 이슈 분석

### 2.1 Postgres DELETE 후 재등장 현상

#### 증상
**파일**: `scripts/clean_state_complete.py`  
**로그 예시** (PHASE24-0 실행 중):
```
[DEBUG] Before DELETE: 63 paper trades
[OK] trading.trades (paper): 63 deleted
[DEBUG] After DELETE (before commit): 0 paper trades
[OK] Postgres cleanup complete
[DEBUG] After COMMIT (new connection): 63 paper trades  <--- 재등장!
```

#### 현재 코드 흐름
```python
# Line 35-94: clean_postgres()
conn = psycopg2.connect(...)
cursor = conn.cursor()

# 1. Before count
cursor.execute("SELECT COUNT(*) FROM trading.trades WHERE mode = 'paper';")
before_count = cursor.fetchone()[0]  # 예: 63

# 2. DELETE
cursor.execute("DELETE FROM trading.trades WHERE mode = 'paper';")
deleted_trades = cursor.rowcount  # 63

# 3. After DELETE (same conn)
cursor.execute("SELECT COUNT(*) FROM trading.trades WHERE mode = 'paper';")
after_count = cursor.fetchone()[0]  # 0

# 4. COMMIT
conn.commit()
cursor.close()
conn.close()

# 5. NEW connection으로 재확인
verify_conn = psycopg2.connect(...)
verify_cur = verify_conn.cursor()
verify_cur.execute("SELECT COUNT(*) FROM trading.trades WHERE mode = 'paper';")
final_count = verify_cur.fetchone()[0]  # 63 <--- WHY?
```

#### 가능한 원인
1. **Wrong WHERE condition**: `mode = 'paper'`가 실제 데이터와 매칭되지 않음
   - 실제 컬럼명이 `mode`가 아닐 수 있음
   - 또는 실제 값이 `'paper'`가 아니라 `'Paper'`, `'PAPER'` 등일 수 있음

2. **Run ID 없음**: 현재 WHERE 조건이 `mode`만 사용
   - `run_id` 컬럼이 있다면 특정 run만 삭제해야 하는데 전체 paper mode 삭제 시도
   - 다른 프로세스가 동시에 paper trades를 생성하고 있을 가능성

3. **Transaction isolation 문제**: `READ COMMITTED` 레벨에서 commit 후 다른 트랜잭션의 변경사항이 보임
   - 하지만 이 경우 "증가"는 있어도 "재등장"은 이상함

4. **Connection pool 캐싱**: verify_conn이 실제로는 이전 트랜잭션의 캐시된 뷰를 보고 있을 가능성
   - 하지만 psycopg2.connect()는 새 연결을 생성하므로 이 가능성은 낮음

5. **Schema mismatch**: `trading.trades` 테이블 스키마가 예상과 다를 수 있음
   - 예: `mode` 컬럼이 없거나, 다른 이름
   - DELETE가 실제로는 실행 안 됨 (rowcount는 믿을 수 없음)

#### 우선 조사 사항
- [ ] `trading.trades` 테이블의 실제 스키마 확인 (컬럼명, 데이터 타입)
- [ ] 실제 `mode` 컬럼의 값 분포 확인 (대소문자, 공백, NULL)
- [ ] `run_id` 또는 `environment` 같은 추가 필터 컬럼 존재 여부 확인
- [ ] clean_state 실행 중 다른 프로세스가 paper trades를 생성하는지 확인

### 2.2 통합 인프라 진단 도구 부재

#### 현재 상태
- **개별 스크립트만 존재**:
  - `scripts/check_redis_errors.py`: 로그 파일에서 Redis 에러 카운트
  - `scripts/analyze_phase24_0_paper.py`: PAPER 결과 분석
- **Pre-flight check 없음**:
  - PAPER 실행 전 DB/Redis/FlowGuardian 상태를 사전에 점검하는 도구 없음
  - 문제 발생 시 사후 로그 분석으로만 진단 가능

#### 필요 기능
1. **DB Check**:
   - Postgres 연결 가능 여부
   - 주요 테이블 존재 여부 (trading.trades, monitoring.signals, etc.)
   - 최근 trades 건수 확인

2. **Redis Check**:
   - Redis 연결 가능 여부 (PING)
   - 주요 키 패턴 존재 확인 (candle:seen, cooldown, guard, etc.)
   - 키 공간 요약 (총 키 개수, TTL 분포 등)

3. **FlowGuardian Readiness**:
   - FlowGuardian self-test (인스턴스 생성 및 기본 동작 확인)
   - Guard 상태 초기화 여부 확인

4. **Exit Code & Logging**:
   - 모든 체크 PASS → exit(0), "INFRA OK" 로그
   - 하나라도 FAIL → exit(1), 실패한 subsystem 명시

---

## 3. TO-BE 설계

### 3.1 DB Cleanup Flow 개선

#### 목표
- DELETE 후 trades 재등장 현상 완전 해결
- 특정 run_id 또는 environment 기준 정리 가능
- 트랜잭션 경계 명확화

#### 설계

##### 3.1.1 DB 스키마 조사 (사전 작업)
**스크립트**: `scripts/infra/inspect_db_schema.py`
- `trading.trades` 테이블의 실제 컬럼 리스트 출력
- `mode`, `run_id`, `environment`, `created_at` 등 주요 컬럼 확인
- 샘플 데이터 10건 출력 (실제 값 확인)

##### 3.1.2 DB Cleanup 헬퍼 모듈
**파일**: `database/cleanup.py`

**함수**:
```python
def delete_trades_for_run(
    run_id: str = None,
    mode: str = "paper",
    environment: str = None
) -> int:
    """
    특정 run/mode/environment의 trades 삭제
    
    Args:
        run_id: 특정 run ID (없으면 mode/environment로만 필터)
        mode: 'paper' | 'backtest' | 'live'
        environment: 추가 필터 (있으면 사용)
    
    Returns:
        int: 삭제된 row 수
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Dynamic WHERE clause
            conditions = []
            params = []
            
            if run_id:
                conditions.append("run_id = %s")
                params.append(run_id)
            if mode:
                conditions.append("mode = %s")
                params.append(mode)
            if environment:
                conditions.append("environment = %s")
                params.append(environment)
            
            where_clause = " AND ".join(conditions)
            sql = f"DELETE FROM trading.trades WHERE {where_clause}"
            
            cur.execute(sql, params)
            deleted = cur.rowcount
            
            # Explicit commit via context manager
            # (get_db_connection auto-commits on success)
    
    return deleted

def delete_signals_for_run(run_id: str = None, mode: str = "paper") -> int:
    """monitoring.signals 삭제"""
    ...

def delete_metrics_for_run(environment: str = "paper") -> int:
    """monitoring.metrics 삭제"""
    ...

def verify_cleanup(mode: str = "paper", run_id: str = None) -> dict:
    """
    Cleanup 후 검증
    
    Returns:
        dict: {
            'trades': count,
            'signals': count,
            'metrics': count
        }
    """
    ...
```

**핵심 원칙**:
- `database/postgres.py`의 `get_db_connection()` context manager 사용 → 자동 commit/rollback
- WHERE 조건을 명시적으로 구성 (SQL injection 방지)
- 삭제 후 즉시 `verify_cleanup()`으로 재확인
- 로깅 강화 (어떤 조건으로 몇 개 삭제했는지 명시)

##### 3.1.3 `clean_state_complete.py` 업데이트
```python
def clean_postgres():
    """Postgres paper mode data cleanup (PHASE24-1 개선)"""
    from database.cleanup import delete_trades_for_run, delete_signals_for_run, delete_metrics_for_run, verify_cleanup
    
    safe_print("\n[1/2] Postgres Clean-State...")
    
    try:
        # 1. Trades 삭제
        deleted_trades = delete_trades_for_run(mode="paper")
        safe_print(f"  [OK] trading.trades (paper): {deleted_trades} deleted")
        
        # 2. Signals 삭제
        deleted_signals = delete_signals_for_run(mode="paper")
        safe_print(f"  [OK] monitoring.signals (paper): {deleted_signals} deleted")
        
        # 3. Metrics 삭제
        deleted_metrics = delete_metrics_for_run(environment="paper")
        safe_print(f"  [OK] monitoring.metrics (paper): {deleted_metrics} deleted")
        
        # 4. 검증
        verify_result = verify_cleanup(mode="paper")
        safe_print(f"  [VERIFY] After cleanup: {verify_result}")
        
        if verify_result['trades'] > 0:
            safe_print(f"  [WARN] {verify_result['trades']} trades still remain after cleanup!")
        
        safe_print("  [OK] Postgres cleanup complete\n")
        return True
        
    except Exception as e:
        safe_print(f"  [ERROR] Postgres cleanup failed: {e}\n")
        return False
```

#### 테스트
**파일**: `tests/test_phase24_1_db_cleanup.py`

```python
def test_db_cleanup_no_reappear():
    """DELETE 후 trades 재등장 없음을 검증"""
    from database.cleanup import delete_trades_for_run, verify_cleanup
    from database.postgres import get_db_connection
    
    # 1. 테스트 데이터 삽입
    test_run_id = "TEST_PHASE24_1"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO trading.trades (trade_id, run_id, mode, symbol, side, entry_price, quantity)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                ("TEST_TRADE_1", test_run_id, "paper", "BTCUSDT", "LONG", 50000.0, 0.1)
            )
    
    # 2. 삭제
    deleted = delete_trades_for_run(run_id=test_run_id, mode="paper")
    assert deleted == 1, f"Expected 1 deleted, got {deleted}"
    
    # 3. 검증 (새 연결로 재확인)
    verify_result = verify_cleanup(mode="paper", run_id=test_run_id)
    assert verify_result['trades'] == 0, f"Trades reappeared: {verify_result['trades']}"
```

### 3.2 통합 인프라 진단 스크립트

#### 설계
**파일**: `scripts/infra/phase24_1_infra_diagnostics.py`

**구조**:
```python
#!/usr/bin/env python3
"""
PHASE24-1: Unified Infra Diagnostics
=====================================
DB + Redis + FlowGuardian Pre-flight Check
"""

def check_db() -> dict:
    """
    DB 상태 점검
    
    Returns:
        dict: {
            'status': 'ok' | 'fail',
            'message': str,
            'details': {
                'total_trades': int,
                'recent_trades_1h': int,
                'tables_exist': bool
            }
        }
    """
    try:
        from database.postgres import get_db_connection
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 테이블 존재 확인
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'trading' AND table_name = 'trades'
                    );
                    """
                )
                tables_exist = cur.fetchone()[0]
                
                if not tables_exist:
                    return {
                        'status': 'fail',
                        'message': 'trading.trades table does not exist',
                        'details': {}
                    }
                
                # Trades 카운트
                cur.execute("SELECT COUNT(*) FROM trading.trades;")
                total_trades = cur.fetchone()[0]
                
                # 최근 1시간 trades
                cur.execute(
                    """
                    SELECT COUNT(*) FROM trading.trades
                    WHERE ts_open > NOW() - INTERVAL '1 hour';
                    """
                )
                recent_trades = cur.fetchone()[0]
        
        return {
            'status': 'ok',
            'message': 'DB connection and tables OK',
            'details': {
                'total_trades': total_trades,
                'recent_trades_1h': recent_trades,
                'tables_exist': tables_exist
            }
        }
    
    except Exception as e:
        return {
            'status': 'fail',
            'message': f'DB check failed: {e}',
            'details': {}
        }


def check_redis() -> dict:
    """
    Redis 상태 점검
    
    Returns:
        dict: {
            'status': 'ok' | 'fail',
            'message': str,
            'details': {
                'ping': bool,
                'total_keys': int,
                'paper_keys': int
            }
        }
    """
    try:
        import redis
        import os
        
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))
        
        r = redis.Redis(host=host, port=port, db=db, decode_responses=True, socket_connect_timeout=5)
        
        # PING
        ping_ok = r.ping()
        
        # 키 카운트
        total_keys = r.dbsize()
        
        # paper 관련 키
        paper_keys = len(r.keys("*:paper:*"))
        
        return {
            'status': 'ok',
            'message': f'Redis OK ({host}:{port})',
            'details': {
                'ping': ping_ok,
                'total_keys': total_keys,
                'paper_keys': paper_keys
            }
        }
    
    except Exception as e:
        return {
            'status': 'fail',
            'message': f'Redis check failed: {e}',
            'details': {}
        }


def check_flow_guardian() -> dict:
    """
    FlowGuardian readiness 점검
    
    Returns:
        dict: {
            'status': 'ok' | 'fail',
            'message': str,
            'details': {}
        }
    """
    try:
        # FlowGuardian 인스턴스 생성 가능 여부 확인
        # (실제 FlowGuardian 코드 구조에 맞게 조정 필요)
        from execution.flow_guardian import FlowGuardian
        
        # Minimal config
        config = {
            'mode': 'paper',
            'symbol': 'BTCUSDT'
        }
        
        guardian = FlowGuardian(config)
        
        # Readiness check (예: self_test 메서드가 있다면 호출)
        # guardian.self_test()
        
        return {
            'status': 'ok',
            'message': 'FlowGuardian instantiation OK',
            'details': {}
        }
    
    except Exception as e:
        return {
            'status': 'fail',
            'message': f'FlowGuardian check failed: {e}',
            'details': {}
        }


def main():
    """Main diagnostics entry point"""
    print("=" * 80)
    print("PHASE24-1: Infra Diagnostics")
    print("=" * 80)
    
    all_ok = True
    
    # 1. DB Check
    print("\n[1/3] DB Check...")
    db_result = check_db()
    print(f"  Status: {db_result['status'].upper()}")
    print(f"  Message: {db_result['message']}")
    if db_result['details']:
        print(f"  Details: {db_result['details']}")
    if db_result['status'] != 'ok':
        all_ok = False
    
    # 2. Redis Check
    print("\n[2/3] Redis Check...")
    redis_result = check_redis()
    print(f"  Status: {redis_result['status'].upper()}")
    print(f"  Message: {redis_result['message']}")
    if redis_result['details']:
        print(f"  Details: {redis_result['details']}")
    if redis_result['status'] != 'ok':
        all_ok = False
    
    # 3. FlowGuardian Check
    print("\n[3/3] FlowGuardian Check...")
    guardian_result = check_flow_guardian()
    print(f"  Status: {guardian_result['status'].upper()}")
    print(f"  Message: {guardian_result['message']}")
    if guardian_result['details']:
        print(f"  Details: {guardian_result['details']}")
    if guardian_result['status'] != 'ok':
        all_ok = False
    
    # Summary
    print("\n" + "=" * 80)
    if all_ok:
        print("✅ INFRA OK - All subsystems ready")
        print("=" * 80)
        return 0
    else:
        print("❌ INFRA FAIL - One or more subsystems failed")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

#### Integration
- `scripts/run_v2.py` 또는 별도 실행 스크립트에서 PAPER 시작 전 호출
- Exit code가 0이 아니면 PAPER 실행 중단

### 3.3 1H PAPER 인프라 테스트

#### 목표
- 전체 인프라 (DB + Redis + FlowGuardian + Engine) 1시간 안정성 검증
- Ensemble V2 로직은 PHASE23-4/PHASE24-0과 동일 (변경 없음)
- Redis/DB/FlowGuardian ERROR/CRITICAL 0건 확인

#### 절차
1. **사전 준비** (자동화):
   - Docker 컨테이너 상태 확인 (`docker ps`)
   - 기존 Python 프로세스 종료
   - `python scripts/clean_state_complete.py` 실행 (개선된 버전)
   - `python scripts/infra/phase24_1_infra_diagnostics.py` 실행
     - Exit code != 0이면 중단

2. **Config 선택**:
   - 기존 `configs/paper/phase23_4_ensemble_v2_3h.yml` 복사
   - 새 파일: `configs/paper/phase24_1_infra_ensemble_1h.yml`
   - 변경사항: `duration_hours: 1.0` (1시간)

3. **실행** (자동화):
   ```bash
   cd c:\Users\bback\OneDrive\Documents\future_alarm_bot
   trading_bot_env\Scripts\activate
   python scripts\run_v2.py --mode paper --config configs\paper\phase24_1_infra_ensemble_1h.yml --clean-state
   ```

4. **모니터링** (자동화):
   - 10분마다 `logs/application.log` tail
   - `ERROR|CRITICAL` 검색
   - Redis/DB/FlowGuardian 관련 에러 추적

5. **사후 분석**:
   - `scripts/analyze_phase24_1_paper.py` (새로 작성 또는 기존 스크립트 재사용)
   - Aggregate 카운트, Trades 카운트
   - Redis/DB/FlowGuardian 에러 카운트

#### Acceptance Criteria
- **실행 완료**: 1H duration 정상 종료 (±2% 허용)
- **Redis ERROR**: 0건
- **DB ERROR**: 0건
- **FlowGuardian ERROR**: 0건
- **Trades**: ≥ 1건 (정상 작동 확인, 수익률은 무관)
- **Ensemble V2**: Aggregate 평가 정상 (Tier1/Tier2/Skip 분포 확인)

---

## 4. Out-of-Scope (PHASE24-1 범위 밖)

### 4.1 명시적 제외 사항
- **전략 추가/수정**: scalping_v3, volatility_breakout_v2 등 기존 전략만 사용
- **Ensemble 로직 변경**: ScoreEngineV2, EnsembleAggregatorV2 그대로 유지
- **튜닝**: 파라미터 탐색, 가중치 조정 (PHASE25)
- **멀티 심볼**: BTCUSDT 단일 심볼만 사용 (PHASE26)
- **성능 최적화**: CPU/Memory 프로파일링 (PHASE27)
- **UI/Dashboard**: 모니터링 대시보드 (PHASE28~30)

### 4.2 향후 PHASE로 미룰 사항
- **환경변수 관리 자동화**: PHASE24-2 (Jinja2 템플릿, Config validation)
- **Docker Compose health check 강화**: 필요 시 PHASE24-2 또는 PHASE25

---

## 5. Dependencies

### 5.1 사전 조건
- **PHASE23 완료**: Ensemble V2 (Score V2, Aggregator V2) 구현 및 검증
- **PHASE24-0 완료**: Redis 안정화 (환경변수, 재시도 로직, 2H PAPER)

### 5.2 필요 인프라
- Docker Compose: Postgres (trading_db_postgres), Redis (trading_redis)
- Python 가상환경: trading_bot_env
- Config: `configs/paper/phase23_4_ensemble_v2_3h.yml` (복사 후 1H로 수정)

### 5.3 코드 레벨 변경 예상
- **신규 파일**:
  - `database/cleanup.py` (DB cleanup 헬퍼)
  - `scripts/infra/inspect_db_schema.py` (스키마 조사)
  - `scripts/infra/phase24_1_infra_diagnostics.py` (통합 진단)
  - `scripts/analyze_phase24_1_paper.py` (결과 분석)
  - `configs/paper/phase24_1_infra_ensemble_1h.yml` (1H PAPER 설정)
  - `tests/test_phase24_1_db_cleanup.py` (DB cleanup 테스트)
  - `tests/test_phase24_1_infra_diagnostics.py` (인프라 진단 테스트)

- **수정 파일**:
  - `scripts/clean_state_complete.py` (cleanup 헬퍼 사용하도록 수정)

- **DO-NOT-TOUCH**:
  - `execution/engine.py` (엔진 로직 변경 금지)
  - `common/ensemble/score_engine_v2.py`
  - `common/ensemble/aggregator_v2.py`
  - `strategies/core/*`, `strategies/research/*` (전략 코드 변경 금지)

---

## 6. Acceptance Criteria (PHASE24-1 완료 조건)

### 6.1 필수 조건 (MUST PASS)

#### ✅ 1. DB Cleanup 안정성
- `database/cleanup.py` 모듈 추가 완료
- `tests/test_phase24_1_db_cleanup.py` 테스트 ≥ 1개 PASS
- `clean_state_complete.py` 실행 후:
  - **Trades 재등장 0건** (특정 test run_id 기준)
  - 로그에 "After COMMIT: X trades" 출력 시 X == 0

#### ✅ 2. 통합 인프라 진단 스크립트
- `scripts/infra/phase24_1_infra_diagnostics.py` 추가 완료
- DB/Redis/FlowGuardian 3개 subsystem 모두 점검
- Exit code 0 (INFRA OK) 또는 1 (INFRA FAIL) 명확히 구분
- `tests/test_phase24_1_infra_diagnostics.py` 기본 테스트 PASS

#### ✅ 3. 1H PAPER 인프라 테스트
- Duration: 1.0H (±2% 허용)
- Ensemble V2 정상 작동:
  - Aggregate 평가 ≥ 100회
  - Tier1/Tier2/Skip 분포 확인
- Trades: ≥ 1건
- **Redis ERROR/CRITICAL: 0건**
- **DB ERROR/CRITICAL: 0건**
- **FlowGuardian ERROR/CRITICAL: 0건**

### 6.2 선택 조건 (NICE TO HAVE)

#### ⏸️ 1. DB 스키마 조사 스크립트
- `scripts/infra/inspect_db_schema.py` 추가
- `trading.trades` 테이블 컬럼 리스트 출력
- 샘플 데이터 10건 출력

#### ⏸️ 2. PAPER 실행 전 자동 pre-flight check
- `scripts/run_v2.py`에 `--check-infra` 옵션 추가
- 실행 전 `phase24_1_infra_diagnostics.py` 자동 호출
- Exit code != 0이면 PAPER 실행 중단

---

## 7. Timeline & Milestones

### 7.1 예상 작업 시간
- **STEP 0 (Context Loading)**: 완료
- **STEP 1 (설계 문서)**: 현재
- **STEP 2 (DB Cleanup 구현)**: ~30분
- **STEP 3 (인프라 진단 스크립트)**: ~20분
- **STEP 4 (1H PAPER 테스트)**: ~1.5H (1H 실행 + 준비/분석)
- **STEP 5 (문서화)**: ~20분
- **STEP 6 (테스트 & Git 커밋)**: ~10분
- **Total**: ~2.5H (실제 PAPER 1H 포함)

### 7.2 Milestones
- [ ] STEP 1 완료: 설계 문서 작성
- [ ] STEP 2 완료: DB cleanup 헬퍼 + 테스트
- [ ] STEP 3 완료: 인프라 진단 스크립트 + 테스트
- [ ] STEP 4 완료: 1H PAPER 실행 및 결과 분석
- [ ] STEP 5 완료: PHASE24-1 리포트 + ROADMAP 업데이트
- [ ] STEP 6 완료: Git 커밋 + working tree clean

---

**작성자**: Windsurf AI  
**작성일**: 2025-12-02  
**검토 대상**: PHASE24-0 완료 후 즉시 착수
