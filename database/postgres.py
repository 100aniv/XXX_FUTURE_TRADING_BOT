#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL Database Module
===========================
PostgreSQL 연결 및 신호 저장

⚠️ 리팩토링: common/database.py → database/postgres.py (2025-11-02)

주요 기능:
- get_db_connection(): 트랜잭션 자동 관리 (컨텍스트 매니저)
- save_signal_to_db(): 신호 저장 (멱등성 보장)
- test_db_connection(): DB 연결 테스트
- get_latest_signals(): 최근 신호 조회

참고: docs/architecture/DB_SCHEMA_GUIDE.md
"""
import os
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from contextlib import contextmanager
from typing import Dict, Any, Optional
from datetime import datetime

from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")

# DB URL (환경변수에서 로드)
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL environment variable is required")


@contextmanager
def get_db_connection():
    """
    DB 연결 컨텍스트 매니저
    
    자동으로 commit/rollback 처리
    
    Examples:
        >>> with get_db_connection() as conn:
        >>>     with conn.cursor() as cur:
        >>>         cur.execute("SELECT * FROM table")
        >>>         result = cur.fetchall()
    """
    conn = psycopg2.connect(DB_URL)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"DB 트랜잭션 실패: {e}")
        raise
    finally:
        conn.close()


def save_signal_to_db(
    signal_id: str,
    strategy_id: str,
    symbol: str,
    timeframe: str,
    candle_closed_at: datetime,
    direction: str,
    confidence: float,
    entry_price: Optional[float] = None,
    sl_price: Optional[float] = None,
    tp_price: Optional[float] = None,
    atr: Optional[float] = None,
    leverage: Optional[int] = None,
    features: Optional[Dict[str, Any]] = None
) -> bool:
    """
    신호를 DB에 저장 (멱등성 보장)
    
    동일 전략/심볼/타임프레임/캔들에 대해 중복 저장 방지
    
    Args:
        signal_id: 신호 고유 ID
        strategy_id: 전략 ID (trend, reversion, breakout, scalping, daytrade, swing)
        symbol: 심볼 (BTCUSDT)
        timeframe: 타임프레임 (5m, 15m, 1h, 4h)
        candle_closed_at: 캔들 종료 시각
        direction: 방향 (LONG/SHORT/FLAT)
        confidence: 신뢰도 (0.0 ~ 1.0)
        entry_price: 진입가
        sl_price: 손절가
        tp_price: 익절가
        atr: ATR 값
        leverage: 레버리지
        features: 추가 특성 (JSONB)
    
    Returns:
        bool: 저장 성공 여부 (중복 시 False)
    
    Note:
        멱등성 보장: UNIQUE(strategy_id, symbol, timeframe, candle_closed_at)
    """
    sql = """
    INSERT INTO monitoring.signals (
        signal_id, strategy_id, symbol, timeframe,
        candle_closed_at, direction, confidence,
        entry_price, sl_price, tp_price, atr, leverage, features
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    ON CONFLICT (strategy_id, symbol, timeframe, candle_closed_at)
    DO NOTHING
    RETURNING signal_id;
    """
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    signal_id, strategy_id, symbol, timeframe,
                    candle_closed_at, direction, confidence,
                    entry_price, sl_price, tp_price, atr, leverage,
                    Json(features) if features else None
                ))
                result = cur.fetchone()
                
                if result:
                    logger.info(f"✅ DB 저장: {strategy_id} {symbol} {direction} @ {candle_closed_at}")
                    return True
                else:
                    logger.debug(f"⏭️  중복 스킵: {strategy_id} {symbol} @ {candle_closed_at}")
                    return False
    except Exception as e:
        logger.error(f"❌ DB 저장 실패: {e}")
        return False


def test_db_connection() -> bool:
    """
    DB 연결 테스트
    
    Returns:
        bool: 연결 성공 여부
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        logger.info("✅ PostgreSQL 연결 성공")
        return True
    except Exception as e:
        logger.error(f"❌ PostgreSQL 연결 실패: {e}")
        logger.warning("⚠️  DB 없이 실행 (신호 저장 안됨)")
        return False


def get_latest_signals(
    strategy_id: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 10
) -> list:
    """
    최근 신호 조회
    
    Args:
        strategy_id: 전략 ID 필터 (선택)
        symbol: 심볼 필터 (선택)
        limit: 조회 개수
    
    Returns:
        list: 신호 목록 (dict)
    """
    sql = """
    SELECT * FROM monitoring.signals
    WHERE 1=1
    """
    params = []
    
    if strategy_id:
        sql += " AND strategy_id = %s"
        params.append(strategy_id)
    
    if symbol:
        sql += " AND symbol = %s"
        params.append(symbol)
    
    sql += " ORDER BY candle_closed_at DESC LIMIT %s"
    params.append(limit)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                return cur.fetchall()
    except Exception as e:
        logger.error(f"❌ 신호 조회 실패: {e}")
        return []


# ============================================================================
# SQLite 백테스트 DB 함수 제거 완료 (2025-11-01)
# ============================================================================
# PostgreSQL 단일 DB 정책에 따라 모든 백테스트 결과는
# PostgreSQL trading.trades 테이블에 저장됩니다.
#
# 마이그레이션 가이드:
#   - get_backtest_db() → get_db_connection()
#   - init_backtest_db() → PostgreSQL 스키마 사용
#   - save_backtest_trade() → execution/engine.py의 save_trade_to_db()
#   - close_backtest_trade() → execution/engine.py의 close_trade_in_db()
# ============================================================================
