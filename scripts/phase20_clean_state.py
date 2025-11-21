"""
PHASE20-1: Clean-State 초기화 스크립트
DB와 Redis를 깨끗하게 초기화하여 테스트 환경 준비
"""
import os
import sys
import redis
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# .env 로드
load_dotenv()


def clean_postgres():
    """Postgres 테스트 데이터 초기화"""
    print("\n[1/2] Postgres Clean-State initialization...")
    
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()
        
        # Paper mode trades deletion
        cursor.execute("DELETE FROM trading.trades WHERE mode = 'paper';")
        deleted_trades = cursor.rowcount
        print(f"  [OK] trading.trades (paper): {deleted_trades} deleted")
        
        # Monitoring signals deletion (if table exists)
        try:
            cursor.execute("DELETE FROM monitoring.signals WHERE mode = 'paper';")
            deleted_signals = cursor.rowcount
            print(f"  [OK] monitoring.signals (paper): {deleted_signals} deleted")
        except Exception as e:
            if "does not exist" not in str(e):
                print(f"  [WARN] monitoring.signals: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("  [OK] Postgres initialization complete\n")
        
    except Exception as e:
        print(f"  [ERROR] Postgres initialization failed: {e}\n")
        raise


def clean_redis():
    """Redis test key initialization"""
    print("[2/2] Redis Clean-State initialization...")
    
    try:
        # 환경변수 또는 기본값
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))
        
        r = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        
        # FlowGuardian 관련 키
        patterns = [
            "flow_guardian:*",
            "cooldown:*",
            "dedup:*",
            "signal:*",
            "guard:*",
            "exposure:*",
        ]
        
        total_deleted = 0
        for pattern in patterns:
            keys = r.keys(pattern)
            if keys:
                deleted = r.delete(*keys)
                total_deleted += deleted
                print(f"  [OK] {pattern}: {deleted} keys deleted")
        
        print(f"  [OK] Redis initialization complete (total {total_deleted} keys deleted)\n")
        
    except Exception as e:
        print(f"  [ERROR] Redis initialization failed: {e}\n")
        raise


def main():
    """메인 실행"""
    print("=" * 60)
    print("PHASE20-1: Clean-State 초기화")
    print("=" * 60)
    
    # 초기화 실행
    clean_postgres()
    clean_redis()
    
    print("=" * 60)
    print("[OK] Clean-State initialization complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
