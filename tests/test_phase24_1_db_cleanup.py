#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE24-1: DB Cleanup 테스트
============================
DELETE 후 trades 재등장 없음 검증
"""
import pytest
import os
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from database.cleanup import (
    delete_trades_for_mode,
    delete_signals_for_mode,
    delete_metrics_for_env,
    verify_cleanup,
    get_db_connection_for_cleanup
)


@pytest.fixture(scope="function")
def test_trade_data():
    """테스트용 trade 데이터 삽입 및 cleanup fixture"""
    test_trade_id = f"TEST_PHASE24_1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 테스트 데이터 삽입
    with get_db_connection_for_cleanup() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO trading.trades (
                    trade_id, symbol, side, entry_price, quantity,
                    leverage, ts_open, status, strategy_id, mode
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    test_trade_id,
                    "BTCUSDT",
                    "LONG",
                    50000.0,
                    0.1,
                    1,
                    datetime.now(),
                    "OPEN",
                    "test_strategy",
                    "paper"
                )
            )
    
    yield test_trade_id
    
    # Cleanup: 테스트 후 삭제 (혹시 남아있을 경우)
    try:
        with get_db_connection_for_cleanup() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM trading.trades WHERE trade_id = %s", [test_trade_id])
    except:
        pass


def test_delete_trades_no_reappear(test_trade_data):
    """
    DELETE 후 trades 재등장 없음을 검증
    
    시나리오:
    1. 테스트 trade 삽입 (fixture)
    2. delete_trades_for_mode() 호출
    3. verify_cleanup()으로 재확인
    4. 재등장 없음 확인
    """
    test_trade_id = test_trade_data
    
    # 1. 삽입 확인 (fixture에서 이미 삽입됨)
    verify_before = verify_cleanup(mode="paper")
    assert verify_before['trades'] >= 1, "Test trade should exist before deletion"
    
    # 2. 삭제
    deleted = delete_trades_for_mode(mode="paper")
    assert deleted >= 1, f"At least 1 trade should be deleted, got {deleted}"
    
    # 3. 검증 (새 연결로 재확인)
    verify_after = verify_cleanup(mode="paper")
    
    # 4. 재등장 없음 확인
    assert verify_after['trades'] == 0, f"Trades reappeared after cleanup: {verify_after['trades']} trades found"
    
    print(f"✅ Test passed: deleted {deleted} trades, verified 0 remaining")


def test_cleanup_with_specific_mode():
    """
    mode 필터가 정확히 작동하는지 검증
    
    시나리오:
    1. 'paper' mode trade 삽입
    2. 'backtest' mode로 삭제 시도
    3. 'paper' trade는 그대로 남아있어야 함
    """
    test_trade_id = f"TEST_MODE_FILTER_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 1. paper mode trade 삽입
    with get_db_connection_for_cleanup() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO trading.trades (
                    trade_id, symbol, side, entry_price, quantity,
                    leverage, ts_open, status, strategy_id, mode
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    test_trade_id,
                    "BTCUSDT",
                    "LONG",
                    50000.0,
                    0.1,
                    1,
                    datetime.now(),
                    "OPEN",
                    "test_strategy",
                    "paper"  # paper mode
                )
            )
    
    try:
        # 2. backtest mode로 삭제 시도
        deleted = delete_trades_for_mode(mode="backtest")
        
        # 3. paper trade는 그대로 남아있어야 함
        with get_db_connection_for_cleanup() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM trading.trades WHERE trade_id = %s", [test_trade_id])
                count = cur.fetchone()[0]
        
        assert count == 1, f"Paper trade should not be deleted when filtering by 'backtest' mode"
        
        print(f"✅ Test passed: mode filter works correctly")
    
    finally:
        # Cleanup
        with get_db_connection_for_cleanup() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM trading.trades WHERE trade_id = %s", [test_trade_id])


def test_verify_cleanup_function():
    """
    verify_cleanup() 함수가 정확한 카운트를 반환하는지 검증
    """
    # 현재 paper trades 카운트 확인
    result = verify_cleanup(mode="paper")
    
    assert 'trades' in result, "Result should have 'trades' key"
    assert 'signals' in result, "Result should have 'signals' key"
    assert 'metrics' in result, "Result should have 'metrics' key"
    
    assert isinstance(result['trades'], int), "trades count should be int"
    assert result['trades'] >= 0, "trades count should be non-negative"
    
    print(f"✅ Test passed: verify_cleanup returns {result}")


def test_transaction_commit_isolation():
    """
    트랜잭션 커밋 후 새 연결에서도 변경사항이 보이는지 검증
    
    시나리오:
    1. Trade 삽입 후 커밋
    2. 새 연결로 확인
    3. 삭제 후 커밋
    4. 새 연결로 확인
    """
    test_trade_id = f"TEST_ISOLATION_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 1. 삽입
    with get_db_connection_for_cleanup() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO trading.trades (
                    trade_id, symbol, side, entry_price, quantity,
                    leverage, ts_open, status, strategy_id, mode
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    test_trade_id,
                    "BTCUSDT",
                    "LONG",
                    50000.0,
                    0.1,
                    1,
                    datetime.now(),
                    "OPEN",
                    "test_strategy",
                    "paper"
                )
            )
    # 커밋은 context manager에서 자동
    
    # 2. 새 연결로 확인 (커밋 후 보여야 함)
    with get_db_connection_for_cleanup() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM trading.trades WHERE trade_id = %s", [test_trade_id])
            count_after_insert = cur.fetchone()[0]
    
    assert count_after_insert == 1, f"Trade should be visible in new connection after insert+commit"
    
    # 3. 삭제
    with get_db_connection_for_cleanup() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM trading.trades WHERE trade_id = %s", [test_trade_id])
    # 커밋은 context manager에서 자동
    
    # 4. 새 연결로 확인 (삭제 후 안 보여야 함)
    with get_db_connection_for_cleanup() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM trading.trades WHERE trade_id = %s", [test_trade_id])
            count_after_delete = cur.fetchone()[0]
    
    assert count_after_delete == 0, f"Trade should NOT be visible in new connection after delete+commit"
    
    print(f"✅ Test passed: transaction isolation works correctly")


if __name__ == "__main__":
    # 개별 실행 시 pytest 없이도 실행 가능
    print("=" * 80)
    print("PHASE24-1: DB Cleanup Tests")
    print("=" * 80)
    
    # 간단한 smoke test
    print("\n[1/3] Testing verify_cleanup...")
    test_verify_cleanup_function()
    
    print("\n[2/3] Testing transaction isolation...")
    test_transaction_commit_isolation()
    
    print("\n[3/3] Testing mode filter...")
    test_cleanup_with_specific_mode()
    
    print("\n" + "=" * 80)
    print("✅ All smoke tests passed!")
    print("=" * 80)
    print("\nRun 'pytest tests/test_phase24_1_db_cleanup.py' for full test suite")
