"""DB cleanup for PHASE35-5 preflight"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.database import get_db_connection

def main():
    print("Cleaning trading.trades...")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM trading.trades")
            conn.commit()
            
            cur.execute("SELECT COUNT(*) FROM trading.trades")
            count = cur.fetchone()[0]
            print(f"✅ trading.trades cleaned, current count: {count}")

if __name__ == "__main__":
    main()
