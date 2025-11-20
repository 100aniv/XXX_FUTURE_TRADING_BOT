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
    print("\n[1/2] Postgres Clean-State 초기화...")
    
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()
        
        # Paper 모드 거래 기록 삭제
        cursor.execute("DELETE FROM trading.trades WHERE mode = 'paper';")
        deleted_trades = cursor.rowcount
        print(f"  ✅ trading.trades (paper): {deleted_trades}건 삭제")
        
        # Monitoring signals 삭제 (테이블이 있다면)
        try:
            cursor.execute("DELETE FROM monitoring.signals WHERE mode = 'paper';")
            deleted_signals = cursor.rowcount
            print(f"  ✅ monitoring.signals (paper): {deleted_signals}건 삭제")
        except Exception as e:
            if "does not exist" not in str(e):
                print(f"  ⚠️  monitoring.signals: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("  ✅ Postgres 초기화 완료\n")
        
    except Exception as e:
        print(f"  ❌ Postgres 초기화 실패: {e}\n")
        raise


def clean_redis():
    """Redis 테스트 키 초기화"""
    print("[2/2] Redis Clean-State 초기화...")
    
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
                print(f"  ✅ {pattern}: {deleted}개 키 삭제")
        
        print(f"  ✅ Redis 초기화 완료 (총 {total_deleted}개 키 삭제)\n")
        
    except Exception as e:
        print(f"  ❌ Redis 초기화 실패: {e}\n")
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
    print("✅ Clean-State 초기화 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
