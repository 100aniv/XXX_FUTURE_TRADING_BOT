#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Cleanup Module (PHASE24-1)
====================================
DB cleanup 헬퍼 함수 - 트랜잭션 안정성 보장
"""
import psycopg2
from typing import Optional, Dict
from contextlib import contextmanager

from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


@contextmanager
def get_db_connection_for_cleanup():
    """
    Cleanup 전용 DB 연결 (명시적 isolation level 설정)
    
    - Isolation Level: READ COMMITTED (기본값)
    - Autocommit: False (명시적 트랜잭션 관리)
    - 트랜잭션 경계 명확화
    
    Yields:
        psycopg2.connection: DB 연결 객체
    """
    import os
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '5433')),
        database=os.getenv('DB_NAME', 'trading_db'),
        user=os.getenv('DB_USER', 'trading_user'),
        password=os.getenv('DB_PASSWORD', 'trading_pw_2024')
    )
    
    # Isolation level 명시 (기본값이지만 명시적으로 설정)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
    
    try:
        yield conn
        conn.commit()
        logger.info("✅ DB cleanup 트랜잭션 커밋 완료")
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ DB cleanup 트랜잭션 롤백: {e}")
        raise
    finally:
        conn.close()


def delete_trades_for_mode(
    mode: str = "paper",
    trial_id: Optional[str] = None
) -> int:
    """
    특정 mode (및 선택적으로 trial_id)의 trades 삭제
    
    Args:
        mode: 'paper' | 'backtest' | 'live'
        trial_id: 특정 trial만 삭제 (선택사항, 현재 스키마에는 있음)
    
    Returns:
        int: 삭제된 row 수
    
    Note:
        - trading.trades 테이블에는 run_id, environment 컬럼이 없음
        - mode와 trial_id (선택)만 사용 가능
    """
    with get_db_connection_for_cleanup() as conn:
        with conn.cursor() as cur:
            # WHERE 조건 구성
            conditions = ["mode = %s"]
            params = [mode]
            
            if trial_id:
                conditions.append("trial_id = %s")
                params.append(trial_id)
            
            where_clause = " AND ".join(conditions)
            sql = f"DELETE FROM trading.trades WHERE {where_clause}"
            
            logger.info(f"🔄 DELETE trades: WHERE {where_clause}, params={params}")
            
            cur.execute(sql, params)
            deleted = cur.rowcount
            
            logger.info(f"✅ Deleted {deleted} trades from trading.trades")
    
    return deleted


def delete_signals_for_mode(mode: str = "paper") -> int:
    """
    monitoring.signals 테이블에서 특정 mode의 신호 삭제
    
    Args:
        mode: 'paper' | 'backtest' | 'live'
    
    Returns:
        int: 삭제된 row 수
    """
    with get_db_connection_for_cleanup() as conn:
        with conn.cursor() as cur:
            try:
                sql = "DELETE FROM monitoring.signals WHERE mode = %s"
                logger.info(f"🔄 DELETE signals: WHERE mode = '{mode}'")
                
                cur.execute(sql, [mode])
                deleted = cur.rowcount
                
                logger.info(f"✅ Deleted {deleted} signals from monitoring.signals")
                return deleted
            
            except psycopg2.Error as e:
                if "does not exist" in str(e):
                    logger.warning(f"⚠️  monitoring.signals 테이블이 존재하지 않음: {e}")
                    return 0
                else:
                    raise


def delete_metrics_for_env(environment: str = "paper") -> int:
    """
    monitoring.metrics 테이블에서 특정 environment의 메트릭 삭제
    
    Args:
        environment: 'paper' | 'backtest' | 'live'
    
    Returns:
        int: 삭제된 row 수
    """
    with get_db_connection_for_cleanup() as conn:
        with conn.cursor() as cur:
            try:
                sql = "DELETE FROM monitoring.metrics WHERE env = %s"
                logger.info(f"🔄 DELETE metrics: WHERE env = '{environment}'")
                
                cur.execute(sql, [environment])
                deleted = cur.rowcount
                
                logger.info(f"✅ Deleted {deleted} metrics from monitoring.metrics")
                return deleted
            
            except psycopg2.Error as e:
                if "does not exist" in str(e):
                    logger.warning(f"⚠️  monitoring.metrics 테이블이 존재하지 않음: {e}")
                    return 0
                else:
                    raise


def verify_cleanup(mode: str = "paper", trial_id: Optional[str] = None) -> Dict[str, int]:
    """
    Cleanup 후 검증 (새 연결로 재확인)
    
    Args:
        mode: 확인할 mode
        trial_id: 확인할 trial_id (선택)
    
    Returns:
        dict: {
            'trades': count,
            'signals': count,
            'metrics': count (env 기준)
        }
    """
    # 명시적으로 **새 연결** 생성하여 트랜잭션 격리 확인
    import os
    verify_conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '5433')),
        database=os.getenv('DB_NAME', 'trading_db'),
        user=os.getenv('DB_USER', 'trading_user'),
        password=os.getenv('DB_PASSWORD', 'trading_pw_2024')
    )
    
    result = {}
    
    try:
        with verify_conn.cursor() as cur:
            # 1. Trades 확인
            conditions = ["mode = %s"]
            params = [mode]
            
            if trial_id:
                conditions.append("trial_id = %s")
                params.append(trial_id)
            
            where_clause = " AND ".join(conditions)
            sql = f"SELECT COUNT(*) FROM trading.trades WHERE {where_clause}"
            
            cur.execute(sql, params)
            result['trades'] = cur.fetchone()[0]
            
            # 2. Signals 확인
            try:
                cur.execute("SELECT COUNT(*) FROM monitoring.signals WHERE mode = %s", [mode])
                result['signals'] = cur.fetchone()[0]
            except psycopg2.Error:
                result['signals'] = -1  # 테이블 없음
            
            # 3. Metrics 확인 (env 기준)
            try:
                cur.execute("SELECT COUNT(*) FROM monitoring.metrics WHERE env = %s", [mode])
                result['metrics'] = cur.fetchone()[0]
            except psycopg2.Error:
                result['metrics'] = -1  # 테이블 없음
        
        logger.info(f"🔍 Cleanup 검증 결과 (mode={mode}): {result}")
    
    finally:
        verify_conn.close()
    
    return result


def clean_all_paper_data() -> Dict[str, int]:
    """
    모든 paper mode 데이터 일괄 삭제 (trades + signals + metrics)
    
    Returns:
        dict: {
            'trades_deleted': int,
            'signals_deleted': int,
            'metrics_deleted': int,
            'verification': {...}
        }
    """
    logger.info("=" * 80)
    logger.info("PHASE24-1: Clean All Paper Data")
    logger.info("=" * 80)
    
    result = {}
    
    # 1. Trades 삭제
    logger.info("\n[1/3] Deleting paper trades...")
    result['trades_deleted'] = delete_trades_for_mode(mode="paper")
    
    # 2. Signals 삭제
    logger.info("\n[2/3] Deleting paper signals...")
    result['signals_deleted'] = delete_signals_for_mode(mode="paper")
    
    # 3. Metrics 삭제
    logger.info("\n[3/3] Deleting paper metrics...")
    result['metrics_deleted'] = delete_metrics_for_env(environment="paper")
    
    # 4. 검증
    logger.info("\n[VERIFY] Checking cleanup results...")
    result['verification'] = verify_cleanup(mode="paper")
    
    # 5. 재등장 체크
    if result['verification']['trades'] > 0:
        logger.warning(f"⚠️  {result['verification']['trades']} trades reappeared after cleanup!")
    else:
        logger.info("✅ No trades reappeared - cleanup successful")
    
    logger.info("=" * 80)
    
    return result
