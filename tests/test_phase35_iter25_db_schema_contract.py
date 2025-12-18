#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-4 ITER25: DB Schema Contract Tests
===========================================
DB 스키마/테이블 SSOT 및 qualified query 검증

목표:
- ensure_trading_schema() SQL에 "CREATE SCHEMA IF NOT EXISTS trading" 포함
- SQL 쿼리가 qualified (trading.trades) 사용 확인
- 테이블 생성 SQL이 init_db.sql 스키마와 호환
"""
import pytest
import re
from pathlib import Path


def test_ensure_trading_schema_creates_schema():
    """
    ensure_trading_schema()가 trading 스키마 생성 SQL을 포함하는지 확인
    """
    from scripts.phase35.run_iter25_db_schema_e2e import ensure_trading_schema
    
    # 함수 소스 코드 가져오기
    import inspect
    source = inspect.getsource(ensure_trading_schema)
    
    # "CREATE SCHEMA IF NOT EXISTS trading" 포함 확인
    assert "CREATE SCHEMA IF NOT EXISTS trading" in source, (
        "ensure_trading_schema()에 'CREATE SCHEMA IF NOT EXISTS trading' 포함 필요"
    )


def test_ensure_trading_schema_creates_trades_table():
    """
    ensure_trading_schema()가 trading.trades 테이블 생성 SQL을 포함하는지 확인
    """
    from scripts.phase35.run_iter25_db_schema_e2e import ensure_trading_schema
    
    import inspect
    source = inspect.getsource(ensure_trading_schema)
    
    # "CREATE TABLE IF NOT EXISTS trading.trades" 포함 확인
    assert "CREATE TABLE IF NOT EXISTS trading.trades" in source, (
        "ensure_trading_schema()에 'CREATE TABLE IF NOT EXISTS trading.trades' 포함 필요"
    )


def test_iter25_runner_uses_qualified_queries():
    """
    ITER25 runner의 collect_db_evidence_iter25()가 qualified query 사용 확인
    """
    from scripts.phase35.run_iter25_db_schema_e2e import collect_db_evidence_iter25
    
    import inspect
    source = inspect.getsource(collect_db_evidence_iter25)
    
    # "FROM trading.trades" 사용 확인
    assert "FROM trading.trades" in source, (
        "collect_db_evidence_iter25()는 'FROM trading.trades' (qualified) 사용 필요"
    )
    
    # "FROM trades" (unqualified) 없어야 함
    # 정규식으로 "FROM trades WHERE" 패턴 찾기 (trading.trades는 제외)
    unqualified_pattern = re.compile(r'FROM\s+trades\s+WHERE', re.IGNORECASE)
    matches = unqualified_pattern.findall(source)
    
    # "FROM trading.trades WHERE"는 괜찮으므로, "FROM trades WHERE"만 체크
    for match in matches:
        assert "trading.trades" in match or "trading." in source, (
            f"Unqualified 'FROM trades' 발견: {match}. 'FROM trading.trades' 사용 필요"
        )


def test_iter24_runner_uses_qualified_queries():
    """
    ITER24 runner (수정 후)의 collect_db_evidence()가 qualified query 사용 확인
    """
    from scripts.phase35.run_iter24_signal_diag_ultra_debug import collect_db_evidence
    
    import inspect
    source = inspect.getsource(collect_db_evidence)
    
    # "FROM trading.trades" 사용 확인
    assert "FROM trading.trades" in source, (
        "collect_db_evidence()는 'FROM trading.trades' (qualified) 사용 필요"
    )


def test_trades_table_schema_has_required_columns():
    """
    ensure_trading_schema()의 trades 테이블이 필수 컬럼 포함 확인
    """
    from scripts.phase35.run_iter25_db_schema_e2e import ensure_trading_schema
    
    import inspect
    source = inspect.getsource(ensure_trading_schema)
    
    required_columns = [
        "trade_id",
        "symbol",
        "side",
        "entry_price",
        "quantity",
        "status",
        "strategy_id",
        "trial_id",  # ITER24/25에서 중요
    ]
    
    for col in required_columns:
        assert col in source, (
            f"trading.trades 테이블에 '{col}' 컬럼 필요"
        )


def test_trades_table_has_trial_id_index():
    """
    ensure_trading_schema()가 trial_id 인덱스 생성 확인
    """
    from scripts.phase35.run_iter25_db_schema_e2e import ensure_trading_schema
    
    import inspect
    source = inspect.getsource(ensure_trading_schema)
    
    # trial_id 인덱스 확인
    assert "idx_trades_trial_id" in source or "trial_id" in source, (
        "trading.trades에 trial_id 인덱스 필요 (ITER24/25 쿼리 최적화)"
    )


def test_db_introspection_checks_qualified_table():
    """
    DB introspection 스크립트가 trading.trades (qualified) 체크 확인
    """
    from scripts.phase35.db_introspect_iter25 import introspect_db
    
    import inspect
    source = inspect.getsource(introspect_db)
    
    # "to_regclass('trading.trades')" 체크 확인
    assert "to_regclass('trading.trades')" in source or "to_regclass(\"trading.trades\")" in source, (
        "introspect_db()는 'to_regclass('trading.trades')' 체크 필요"
    )


def test_iter25_runner_has_ac_checks():
    """
    ITER25 runner의 check_ac() 함수가 모든 AC 체크 포함 확인
    """
    from scripts.phase35.run_iter25_db_schema_e2e import check_ac
    
    import inspect
    source = inspect.getsource(check_ac)
    
    required_acs = [
        "ac1_trades_table_exists",
        "ac2_l4_db_trades",
        "ac3_report_generated",
        "ac4_evidence_saved",
    ]
    
    for ac in required_acs:
        assert ac in source, (
            f"check_ac()에 '{ac}' 체크 필요"
        )


def test_init_db_sql_has_trading_schema():
    """
    init_db.sql이 trading 스키마를 정의하는지 확인
    """
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    init_db_path = PROJECT_ROOT / "scripts" / "db" / "init_db.sql"
    
    assert init_db_path.exists(), f"init_db.sql 파일 없음: {init_db_path}"
    
    content = init_db_path.read_text(encoding="utf-8")
    
    # trading 스키마 생성 확인
    assert "CREATE SCHEMA IF NOT EXISTS trading" in content, (
        "init_db.sql에 'CREATE SCHEMA IF NOT EXISTS trading' 필요"
    )
    
    # trading.trades 테이블 정의 확인
    assert "CREATE TABLE IF NOT EXISTS trading.trades" in content, (
        "init_db.sql에 'CREATE TABLE IF NOT EXISTS trading.trades' 정의 필요"
    )


def test_engine_save_trade_uses_qualified_query():
    """
    execution/engine.py의 save_trade_to_db()가 qualified query 사용 확인
    """
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    engine_path = PROJECT_ROOT / "execution" / "engine.py"
    
    assert engine_path.exists(), f"engine.py 파일 없음: {engine_path}"
    
    content = engine_path.read_text(encoding="utf-8")
    
    # save_trade_to_db 함수에서 "INSERT INTO trading.trades" 확인
    assert "INSERT INTO trading.trades" in content, (
        "engine.py의 save_trade_to_db()는 'INSERT INTO trading.trades' 사용 필요"
    )
