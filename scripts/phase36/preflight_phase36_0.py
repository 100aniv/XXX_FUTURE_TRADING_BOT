"""
PHASE36-0 Preflight: Paper Validation Pack 환경 점검
===================================================
PHASE35-5 preflight를 재사용하되, Paper 모드 특화 체크 추가

체크 항목:
1. Docker 컨테이너 (trading_db_postgres, trading_redis)
2. DB 연결 및 trading.trades 테이블 확인
3. DB cleanup (trading.trades 초기화)
4. Redis cleanup (cooldown, portfolio 상태 초기화)
5. Binance API 연결 테스트 (선택, 레이트리밋 체크)
6. Evidence 저장 (JSON)

Usage:
    python scripts/phase36/preflight_phase36_0.py --stage smoke
"""
import sys
from pathlib import Path
import json
import subprocess
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.database import get_db_connection

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "phase36" / "phase36_0" / "preflight"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def check_docker():
    """Docker 컨테이너 상태 확인"""
    print("\n[1/6] Docker 컨테이너 체크...")
    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
        capture_output=True,
        text=True
    )
    
    containers = {}
    for line in result.stdout.strip().split('\n'):
        if '\t' in line:
            name, status = line.split('\t', 1)
            containers[name] = status
    
    postgres_status = containers.get("trading_db_postgres", "NOT FOUND")
    redis_status = containers.get("trading_redis", "NOT FOUND")
    
    print(f"   trading_db_postgres: {postgres_status}")
    print(f"   trading_redis: {redis_status}")
    
    if "NOT FOUND" in [postgres_status, redis_status]:
        print("   ❌ FAIL: 필수 컨테이너 없음")
        return {
            "status": "FAIL",
            "trading_db_postgres": postgres_status,
            "trading_redis": redis_status
        }
    
    print("   ✅ PASS")
    return {
        "status": "PASS",
        "trading_db_postgres": postgres_status,
        "trading_redis": redis_status
    }


def check_db_before():
    """DB 연결 및 trading.trades 테이블 확인 (cleanup 전)"""
    print("\n[2/6] DB 연결 체크...")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # trading.trades 카운트
                cur.execute("SELECT COUNT(*) FROM trading.trades")
                count = cur.fetchone()[0]
                
                # 테이블 목록
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'trading' 
                    ORDER BY table_name
                """)
                tables = [row[0] for row in cur.fetchall()]
                
                print(f"   trades count (before cleanup): {count}")
                print(f"   tables: {len(tables)} found")
                print("   ✅ PASS")
                
                return {
                    "status": "PASS",
                    "connection": "SUCCESS",
                    "trades_count_before": count,
                    "tables": tables
                }
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return {
            "status": "FAIL",
            "connection": "FAIL",
            "error": str(e)
        }


def clean_db():
    """trading.trades 테이블 정리"""
    print("\n[3/6] DB cleanup (trading.trades)...")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM trading.trades")
                conn.commit()
                
                cur.execute("SELECT COUNT(*) FROM trading.trades")
                count = cur.fetchone()[0]
                
                print(f"   trades count (after cleanup): {count}")
                print("   ✅ PASS")
                
                return {
                    "status": "PASS",
                    "cleanup": "SUCCESS",
                    "trades_count_after": count
                }
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return {
            "status": "FAIL",
            "cleanup": "FAIL",
            "error": str(e)
        }


def clean_redis():
    """Redis 상태 초기화 (cooldown, portfolio)"""
    print("\n[4/6] Redis cleanup...")
    try:
        import redis
        
        # Redis 연결 (환경변수 기본값)
        client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
        
        # ping 테스트
        client.ping()
        
        # cooldown 키 삭제
        cooldown_keys = client.keys("cooldown:*")
        if cooldown_keys:
            client.delete(*cooldown_keys)
        
        # portfolio 키 삭제
        portfolio_keys = client.keys("portfolio:*")
        if portfolio_keys:
            client.delete(*portfolio_keys)
        
        # guard 키 삭제
        guard_keys = client.keys("guard:*")
        if guard_keys:
            client.delete(*guard_keys)
        
        print(f"   Deleted: {len(cooldown_keys)} cooldown, {len(portfolio_keys)} portfolio, {len(guard_keys)} guard keys")
        print("   ✅ PASS")
        
        return {
            "status": "PASS",
            "cooldown_keys_deleted": len(cooldown_keys),
            "portfolio_keys_deleted": len(portfolio_keys),
            "guard_keys_deleted": len(guard_keys)
        }
    except Exception as e:
        print(f"   ⚠️ WARNING: {e}")
        return {
            "status": "WARNING",
            "error": str(e)
        }


def check_binance_api():
    """Binance API 연결 테스트 (선택, 레이트리밋 체크)"""
    print("\n[5/6] Binance API 연결 테스트...")
    try:
        from binance.client import Client
        import os
        
        # 환경변수 또는 기본값 (testnet)
        api_key = os.getenv('BINANCE_API_KEY', '')
        api_secret = os.getenv('BINANCE_API_SECRET', '')
        
        if not api_key or not api_secret:
            print("   ⚠️ SKIP: BINANCE_API_KEY/SECRET 없음 (Paper 모드는 API key 불필요)")
            return {
                "status": "SKIP",
                "reason": "No API key (Paper mode OK)"
            }
        
        client = Client(api_key, api_secret, testnet=True)
        
        # 서버 시간 조회 (가장 가벼운 API)
        server_time = client.get_server_time()
        
        print(f"   Server time: {server_time['serverTime']}")
        print("   ✅ PASS")
        
        return {
            "status": "PASS",
            "server_time": server_time['serverTime']
        }
    except Exception as e:
        print(f"   ⚠️ WARNING: {e}")
        return {
            "status": "WARNING",
            "error": str(e)
        }


def save_evidence(stage, docker_result, db_before, db_cleanup, redis_cleanup, api_check):
    """Preflight 증거 저장"""
    print("\n[6/6] Evidence 저장...")
    
    evidence = {
        "timestamp": datetime.now().isoformat(),
        "stage": stage,
        "docker": docker_result,
        "db_before": db_before,
        "db_cleanup": db_cleanup,
        "redis_cleanup": redis_cleanup,
        "binance_api": api_check
    }
    
    evidence_path = ARTIFACTS_DIR / f"preflight_evidence_{stage}.json"
    with open(evidence_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, ensure_ascii=False)
    
    print(f"   Saved: {evidence_path}")
    print("   ✅ PASS")
    
    return evidence_path


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="PHASE36-0 Preflight Check")
    parser.add_argument("--stage", type=str, default="smoke", choices=["smoke", "baseline", "longrun"],
                        help="Stage name (smoke/baseline/longrun)")
    args = parser.parse_args()
    
    print("=" * 80)
    print(f"PHASE36-0 PREFLIGHT CHECK - {args.stage.upper()}")
    print("=" * 80)
    
    # 1. Docker 체크
    docker_result = check_docker()
    if docker_result["status"] == "FAIL":
        print("\n❌ PREFLIGHT FAIL: Docker 컨테이너 없음")
        return 1
    
    # 2. DB 체크 (before)
    db_before = check_db_before()
    if db_before["status"] == "FAIL":
        print("\n❌ PREFLIGHT FAIL: DB 연결 실패")
        return 1
    
    # 3. DB cleanup
    db_cleanup = clean_db()
    if db_cleanup["status"] == "FAIL":
        print("\n❌ PREFLIGHT FAIL: DB cleanup 실패")
        return 1
    
    # 4. Redis cleanup
    redis_cleanup = clean_redis()
    # WARNING은 허용 (Redis 연결 실패는 치명적이지 않음)
    
    # 5. Binance API 체크
    api_check = check_binance_api()
    # SKIP/WARNING 허용
    
    # 6. Evidence 저장
    evidence_path = save_evidence(
        args.stage,
        docker_result,
        db_before,
        db_cleanup,
        redis_cleanup,
        api_check
    )
    
    print("\n" + "=" * 80)
    print("✅ PREFLIGHT PASS")
    print("=" * 80)
    print(f"Evidence: {evidence_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
