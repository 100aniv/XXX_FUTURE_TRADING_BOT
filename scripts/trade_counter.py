#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trade Counter Helper
====================
Paper 모드 거래 수를 정확하게 카운트하는 헬퍼 모듈
"""
import os
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5433")),
    "database": os.getenv("DB_NAME", "trading_db"),
    "user": os.getenv("DB_USER", "trading_user"),
    "password": os.getenv("DB_PASSWORD", "trading_pw_2024")
}


def get_paper_trade_count():
    """
    Paper 모드 거래 총 수
    Returns: int (거래 수)
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trading.trades WHERE mode = 'paper'")
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"[ERROR] get_paper_trade_count failed: {e}")
        return -1


def get_paper_trade_count_since(since_timestamp):
    """
    특정 시간 이후 생성된 Paper 모드 거래 수
    Args: since_timestamp (datetime or str in ISO format)
    Returns: int (거래 수)
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # 타입 변환
        if isinstance(since_timestamp, datetime):
            since_str = since_timestamp.isoformat()
        else:
            since_str = str(since_timestamp)
        
        cur.execute(
            "SELECT COUNT(*) FROM trading.trades WHERE mode = 'paper' AND created_at >= %s",
            (since_str,)
        )
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"[ERROR] get_paper_trade_count_since failed: {e}")
        return -1


def get_paper_trades_by_strategy(strategy_id):
    """
    특정 전략의 Paper 모드 거래 수
    Args: strategy_id (str)
    Returns: int (거래 수)
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM trading.trades WHERE mode = 'paper' AND strategy_id = %s",
            (strategy_id,)
        )
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"[ERROR] get_paper_trades_by_strategy failed: {e}")
        return -1


def get_paper_trades_since_by_strategy(strategy_id, since_timestamp):
    """
    특정 전략의 특정 시간 이후 Paper 모드 거래 수
    Args: strategy_id (str), since_timestamp (datetime or str)
    Returns: int (거래 수)
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        if isinstance(since_timestamp, datetime):
            since_str = since_timestamp.isoformat()
        else:
            since_str = str(since_timestamp)
        
        cur.execute(
            "SELECT COUNT(*) FROM trading.trades WHERE mode = 'paper' AND strategy_id = %s AND created_at >= %s",
            (strategy_id, since_str)
        )
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"[ERROR] get_paper_trades_since_by_strategy failed: {e}")
        return -1


if __name__ == "__main__":
    print("=== Trade Counter Test ===")
    print(f"Total paper trades: {get_paper_trade_count()}")
    print(f"Scalping trades: {get_paper_trades_by_strategy('scalping')}")
    print(f"Breakout trades: {get_paper_trades_by_strategy('breakout')}")
