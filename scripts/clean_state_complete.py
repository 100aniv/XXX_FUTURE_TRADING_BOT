#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete Clean-State Initialization
====================================
PHASE21-1A용 완전한 Clean-State 초기화
DB (Postgres) + Redis 모든 Paper 모드 상태 정리
"""
import os
import sys
import redis
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()


def safe_print(msg):
    """Windows console safe print"""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def clean_postgres():
    """Postgres paper mode data cleanup (PHASE24-1 개선 - cleanup 헬퍼 사용)"""
    safe_print("\n[1/2] Postgres Clean-State...")
    
    try:
        # PHASE24-1: cleanup 헬퍼 모듈 사용
        from database.cleanup import delete_trades_for_mode, delete_signals_for_mode, delete_metrics_for_env, verify_cleanup
        
        # 1. Before count
        verify_before = verify_cleanup(mode="paper")
        safe_print(f"  [DEBUG] Before DELETE: {verify_before['trades']} paper trades")
        
        # 2. Trades 삭제
        deleted_trades = delete_trades_for_mode(mode="paper")
        safe_print(f"  [OK] trading.trades (paper): {deleted_trades} deleted")
        
        # 3. Signals 삭제
        deleted_signals = delete_signals_for_mode(mode="paper")
        if deleted_signals >= 0:
            safe_print(f"  [OK] monitoring.signals (paper): {deleted_signals} deleted")
        else:
            safe_print(f"  [SKIP] monitoring.signals: 테이블 없음")
        
        # 4. Metrics 삭제
        deleted_metrics = delete_metrics_for_env(environment="paper")
        if deleted_metrics >= 0:
            safe_print(f"  [OK] monitoring.metrics (paper): {deleted_metrics} deleted")
        else:
            safe_print(f"  [SKIP] monitoring.metrics: 테이블 없음")
        
        # 5. 검증 (새 연결로 재확인)
        verify_after = verify_cleanup(mode="paper")
        safe_print(f"  [VERIFY] After cleanup: trades={verify_after['trades']}, signals={verify_after['signals']}, metrics={verify_after['metrics']}")
        
        # 6. 재등장 체크
        if verify_after['trades'] > 0:
            safe_print(f"  [WARN] ⚠️  {verify_after['trades']} trades reappeared after cleanup!")
            safe_print(f"  [HINT] This may indicate concurrent inserts or transaction isolation issues.")
        else:
            safe_print(f"  [OK] ✅ No trades reappeared - cleanup successful")
        
        safe_print("  [OK] Postgres cleanup complete\n")
        return True
        
    except Exception as e:
        safe_print(f"  [ERROR] Postgres cleanup failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def clean_redis():
    """Redis paper mode keys cleanup with retry logic"""
    safe_print("[2/2] Redis Clean-State...")
    
    max_retries = 10
    retry_delay = 1  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", "6379"))
            db = int(os.getenv("REDIS_DB", "0"))
            
            safe_print(f"  [INFO] Connecting to Redis: {host}:{port} (attempt {attempt}/{max_retries})")
            r = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Connection test
            r.ping()
            safe_print(f"  [OK] Redis connection successful!")
            
            # Paper mode key patterns (based on namespace.py)
            patterns = [
                "candle:seen:paper:*",      # Candle dedup
                "cooldown:paper:*",         # Strategy cooldown
                "signal:paper:*",           # Signal cache
                "exposure:paper:*",         # Exposure tracking
                "budget:paper:*",           # Budget tracking
                "guard:paper:*",            # Guard states
                "portfolio:paper:*",        # Portfolio states
                "dedup:*",                  # Legacy dedup keys
                "flow_guardian:*",          # Flow guardian states
            ]
            
            total_deleted = 0
            for pattern in patterns:
                keys = r.keys(pattern)
                if keys:
                    deleted = r.delete(*keys)
                    total_deleted += deleted
                    safe_print(f"  [OK] {pattern}: {deleted} keys deleted")
                else:
                    safe_print(f"  [SKIP] {pattern}: no keys")
            
            safe_print(f"  [OK] Redis cleanup complete (total {total_deleted} keys deleted)\n")
            return True
            
        except Exception as e:
            if attempt < max_retries:
                safe_print(f"  [RETRY] Redis connection failed ({attempt}/{max_retries}): {e}")
                safe_print(f"  [WAIT] Retrying in {retry_delay} second(s)...")
                import time
                time.sleep(retry_delay)
            else:
                safe_print(f"  [ERROR] Redis connection failed after {max_retries} attempts: {e}")
                safe_print(f"  [HINT] Please check Docker container: docker ps | grep trading_redis\n")
                return False
    
    return False


def main():
    """Main execution"""
    safe_print("=" * 60)
    safe_print("PHASE21-1A: Complete Clean-State Initialization")
    safe_print("=" * 60)
    
    # Postgres cleanup
    pg_success = clean_postgres()
    
    # Redis cleanup
    redis_success = clean_redis()
    
    # Final status
    safe_print("=" * 60)
    if pg_success and redis_success:
        safe_print("[OK] Clean-State initialization complete!")
        safe_print("=" * 60)
        return 0
    else:
        safe_print("[ERROR] Clean-State initialization failed!")
        safe_print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
