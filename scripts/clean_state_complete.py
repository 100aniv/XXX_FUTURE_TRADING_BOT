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
    """Postgres paper mode data cleanup"""
    safe_print("\n[1/2] Postgres Clean-State...")
    
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()
        
        # Check before delete
        cursor.execute("SELECT COUNT(*) FROM trading.trades WHERE mode = 'paper';")
        before_count = cursor.fetchone()[0]
        safe_print(f"  [DEBUG] Before DELETE: {before_count} paper trades")
        
        # Paper mode trades deletion
        cursor.execute("DELETE FROM trading.trades WHERE mode = 'paper';")
        deleted_trades = cursor.rowcount
        safe_print(f"  [OK] trading.trades (paper): {deleted_trades} deleted")
        
        # Check after delete (before commit)
        cursor.execute("SELECT COUNT(*) FROM trading.trades WHERE mode = 'paper';")
        after_count = cursor.fetchone()[0]
        safe_print(f"  [DEBUG] After DELETE (before commit): {after_count} paper trades")
        
        # Monitoring signals deletion (if exists)
        try:
            cursor.execute("DELETE FROM monitoring.signals WHERE mode = 'paper';")
            deleted_signals = cursor.rowcount
            safe_print(f"  [OK] monitoring.signals (paper): {deleted_signals} deleted")
        except Exception as e:
            if "does not exist" not in str(e):
                safe_print(f"  [WARN] monitoring.signals: {e}")
        
        # Monitoring metrics deletion (if exists)
        try:
            cursor.execute("DELETE FROM monitoring.metrics WHERE env = 'paper';")
            deleted_metrics = cursor.rowcount
            safe_print(f"  [OK] monitoring.metrics (paper): {deleted_metrics} deleted")
        except Exception as e:
            if "does not exist" not in str(e):
                safe_print(f"  [WARN] monitoring.metrics: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Check after commit with NEW connection
        verify_conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        verify_cur = verify_conn.cursor()
        verify_cur.execute("SELECT COUNT(*) FROM trading.trades WHERE mode = 'paper';")
        final_count = verify_cur.fetchone()[0]
        safe_print(f"  [DEBUG] After COMMIT (new connection): {final_count} paper trades")
        verify_cur.close()
        verify_conn.close()
        
        safe_print("  [OK] Postgres cleanup complete\n")
        return True
        
    except Exception as e:
        safe_print(f"  [ERROR] Postgres cleanup failed: {e}\n")
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
