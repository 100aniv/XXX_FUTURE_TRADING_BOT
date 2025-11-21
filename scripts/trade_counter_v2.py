#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trade Counter V2
================
Paper 모드 거래 수를 정확하게 카운트
전략별, 시간 범위별 필터링 지원
"""
import os
import psycopg2
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5433")),
    "database": os.getenv("DB_NAME", "trading_db"),
    "user": os.getenv("DB_USER", "trading_user"),
    "password": os.getenv("DB_PASSWORD", "trading_pw_2024")
}


def get_connection():
    """DB 연결 생성"""
    return psycopg2.connect(**DB_CONFIG)


def count_paper_trades(
    strategy_id: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None
) -> int:
    """
    Paper 모드 거래 수 카운트
    
    Args:
        strategy_id: 전략 ID (None이면 모든 전략)
        since: 시작 시간 (None이면 제한 없음)
        until: 종료 시간 (None이면 제한 없음)
    
    Returns:
        int: 거래 수
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Build query
        query = "SELECT COUNT(*) FROM trading.trades WHERE mode = 'paper'"
        params = []
        
        if strategy_id:
            query += " AND strategy_id = %s"
            params.append(strategy_id)
        
        if since:
            query += " AND created_at >= %s"
            params.append(since)
        
        if until:
            query += " AND created_at <= %s"
            params.append(until)
        
        cur.execute(query, params)
        count = cur.fetchone()[0]
        conn.close()
        return count
        
    except Exception as e:
        print(f"[ERROR] count_paper_trades failed: {e}")
        return -1


def get_paper_trade_stats(
    strategy_id: Optional[str] = None,
    since: Optional[datetime] = None
) -> dict:
    """
    Paper 모드 거래 통계
    
    Returns:
        dict: {
            'total': int,
            'long': int,
            'short': int,
            'pnl_total': float,
            'pnl_avg': float
        }
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        query = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN side = 'LONG' THEN 1 ELSE 0 END) as long_count,
            SUM(CASE WHEN side = 'SHORT' THEN 1 ELSE 0 END) as short_count,
            COALESCE(SUM(pnl), 0) as pnl_total,
            COALESCE(AVG(pnl), 0) as pnl_avg
        FROM trading.trades
        WHERE mode = 'paper'
        """
        
        params = []
        
        if strategy_id:
            query += " AND strategy_id = %s"
            params.append(strategy_id)
        
        if since:
            query += " AND created_at >= %s"
            params.append(since)
        
        cur.execute(query, params)
        row = cur.fetchone()
        conn.close()
        
        return {
            'total': row[0] or 0,
            'long': row[1] or 0,
            'short': row[2] or 0,
            'pnl_total': float(row[3]) if row[3] else 0.0,
            'pnl_avg': float(row[4]) if row[4] else 0.0
        }
        
    except Exception as e:
        print(f"[ERROR] get_paper_trade_stats failed: {e}")
        return {
            'total': -1,
            'long': -1,
            'short': -1,
            'pnl_total': 0.0,
            'pnl_avg': 0.0
        }


if __name__ == "__main__":
    print("=== Trade Counter V2 Test ===")
    
    # Test 1: Total count
    total = count_paper_trades()
    print(f"Total paper trades: {total}")
    
    # Test 2: By strategy
    for strategy in ['scalping', 'breakout', 'reversion']:
        count = count_paper_trades(strategy_id=strategy)
        print(f"{strategy}: {count} trades")
    
    # Test 3: Stats
    stats = get_paper_trade_stats()
    print(f"\nStats: {stats}")
