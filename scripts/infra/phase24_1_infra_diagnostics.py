#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE24-1: Unified Infra Diagnostics
=====================================
DB + Redis + FlowGuardian Pre-flight Check
"""
import os
import sys
from pathlib import Path
from typing import Dict

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()


def check_db() -> Dict:
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
        import psycopg2
        
        # DB 연결
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5433')),
            database=os.getenv('DB_NAME', 'trading_db'),
            user=os.getenv('DB_USER', 'trading_user'),
            password=os.getenv('DB_PASSWORD', 'trading_pw_2024')
        )
        
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
                conn.close()
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
        
        conn.close()
        
        return {
            'status': 'ok',
            'message': f'DB connection OK ({os.getenv("DB_HOST")}:{os.getenv("DB_PORT")})',
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


def check_redis() -> Dict:
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
        
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))
        
        r = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
        # PING
        ping_ok = r.ping()
        
        # 키 카운트
        total_keys = r.dbsize()
        
        # paper 관련 키
        paper_keys = len(r.keys("*:paper:*"))
        
        return {
            'status': 'ok',
            'message': f'Redis OK ({host}:{port}, db={db})',
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


def check_flow_guardian() -> Dict:
    """
    Engine & Guard 로직 readiness 점검
    
    FlowGuardian은 engine.py 내부 로직이므로 별도 모듈이 아님.
    대신 engine.py import 가능 여부를 확인.
    
    Returns:
        dict: {
            'status': 'ok' | 'warn' | 'fail',
            'message': str,
            'details': {}
        }
    """
    try:
        # Engine 모듈 import 가능 여부 확인
        import execution.engine as engine_module
        
        # engine.py가 정상적으로 import되는지만 확인
        # FlowGuardian은 엔진 실행 시 내부적으로 초기화됨
        
        return {
            'status': 'ok',
            'message': 'Engine module import OK (FlowGuardian/Guard logic embedded in engine)',
            'details': {
                'engine_module': str(engine_module.__file__)
            }
        }
    
    except ImportError as e:
        return {
            'status': 'fail',
            'message': f'Engine module import failed: {e}',
            'details': {}
        }
    except Exception as e:
        return {
            'status': 'warn',
            'message': f'Engine check warning: {e}',
            'details': {}
        }


def main() -> int:
    """Main diagnostics entry point"""
    print("=" * 80)
    print("PHASE24-1: Unified Infra Diagnostics")
    print("=" * 80)
    
    all_ok = True
    results = {}
    
    # 1. DB Check
    print("\n[1/3] DB Check...")
    db_result = check_db()
    results['db'] = db_result
    print(f"  Status: {db_result['status'].upper()}")
    print(f"  Message: {db_result['message']}")
    if db_result['details']:
        print(f"  Details:")
        for key, value in db_result['details'].items():
            print(f"    - {key}: {value}")
    if db_result['status'] != 'ok':
        all_ok = False
    
    # 2. Redis Check
    print("\n[2/3] Redis Check...")
    redis_result = check_redis()
    results['redis'] = redis_result
    print(f"  Status: {redis_result['status'].upper()}")
    print(f"  Message: {redis_result['message']}")
    if redis_result['details']:
        print(f"  Details:")
        for key, value in redis_result['details'].items():
            print(f"    - {key}: {value}")
    if redis_result['status'] != 'ok':
        all_ok = False
    
    # 3. FlowGuardian Check
    print("\n[3/3] FlowGuardian Check...")
    guardian_result = check_flow_guardian()
    results['flow_guardian'] = guardian_result
    print(f"  Status: {guardian_result['status'].upper()}")
    print(f"  Message: {guardian_result['message']}")
    if guardian_result['details']:
        print(f"  Details:")
        for key, value in guardian_result['details'].items():
            print(f"    - {key}: {value}")
    if guardian_result['status'] != 'ok':
        all_ok = False
    
    # Summary
    print("\n" + "=" * 80)
    if all_ok:
        print("✅ INFRA OK - All subsystems ready")
        print("=" * 80)
        print("\n[NEXT] You can now proceed with PAPER/BACKTEST/LIVE execution")
        return 0
    else:
        print("❌ INFRA FAIL - One or more subsystems failed")
        print("=" * 80)
        print("\n[ACTION] Fix the failing subsystems before proceeding:")
        for subsystem, result in results.items():
            if result['status'] != 'ok':
                print(f"  - {subsystem.upper()}: {result['message']}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
