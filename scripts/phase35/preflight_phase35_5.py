"""PHASE35-5 Preflight: Docker + DB + cleanup + evidence"""
import sys
from pathlib import Path
import json
import subprocess
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.database import get_db_connection

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "phase35" / "phase35_5" / "preflight"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def check_docker():
    """Check Docker containers"""
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
    
    return {
        "trading_db_postgres": containers.get("trading_db_postgres", "NOT FOUND"),
        "trading_redis": containers.get("trading_redis", "NOT FOUND")
    }

def check_db_before():
    """Check DB before cleanup"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM trading.trades")
                count = cur.fetchone()[0]
                
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'trading' 
                    ORDER BY table_name
                """)
                tables = [row[0] for row in cur.fetchall()]
                
                return {
                    "connection": "SUCCESS",
                    "trades_count_before": count,
                    "tables": tables
                }
    except Exception as e:
        return {"connection": "FAIL", "error": str(e)}

def clean_db():
    """Clean trading.trades table"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM trading.trades")
                conn.commit()
                
                cur.execute("SELECT COUNT(*) FROM trading.trades")
                count = cur.fetchone()[0]
                
                return {
                    "cleanup": "SUCCESS",
                    "trades_count_after": count
                }
    except Exception as e:
        return {"cleanup": "FAIL", "error": str(e)}

def main():
    print("=" * 80)
    print("PHASE35-5 PREFLIGHT CHECK")
    print("=" * 80)
    
    # 1. Docker check
    print("\n1. Checking Docker containers...")
    docker_status = check_docker()
    print(f"   trading_db_postgres: {docker_status['trading_db_postgres']}")
    print(f"   trading_redis: {docker_status['trading_redis']}")
    
    # 2. DB check before
    print("\n2. Checking DB status...")
    db_before = check_db_before()
    if db_before.get("connection") == "SUCCESS":
        print(f"   ✅ DB connection: SUCCESS")
        print(f"   trades count (before): {db_before['trades_count_before']}")
        print(f"   tables: {', '.join(db_before['tables'])}")
    else:
        print(f"   ❌ DB connection: FAIL")
        print(f"   error: {db_before.get('error')}")
        return
    
    # 3. DB cleanup
    print("\n3. Cleaning trading.trades...")
    cleanup_result = clean_db()
    if cleanup_result.get("cleanup") == "SUCCESS":
        print(f"   ✅ Cleanup: SUCCESS")
        print(f"   trades count (after): {cleanup_result['trades_count_after']}")
    else:
        print(f"   ❌ Cleanup: FAIL")
        print(f"   error: {cleanup_result.get('error')}")
        return
    
    # 4. Save evidence
    evidence = {
        "timestamp": datetime.now().isoformat(),
        "docker": docker_status,
        "db_before": db_before,
        "cleanup": cleanup_result
    }
    
    evidence_path = ARTIFACTS_DIR / "preflight_evidence.json"
    with open(evidence_path, "w") as f:
        json.dump(evidence, f, indent=2)
    
    print(f"\n4. Evidence saved: {evidence_path}")
    print("\n" + "=" * 80)
    print("✅ PREFLIGHT PASS")
    print("=" * 80)

if __name__ == "__main__":
    main()
