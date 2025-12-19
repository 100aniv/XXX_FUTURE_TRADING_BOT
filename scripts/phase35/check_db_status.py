"""Quick DB status checker for preflight"""
import sys
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.database import get_db_connection

def main():
    result = {
        "db_connection": "FAIL",
        "trades_count": 0,
        "tables": [],
        "db_url": "localhost:5433/trading_db"
    }
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Count trades
                cur.execute("SELECT COUNT(*) FROM trading.trades")
                result["trades_count"] = cur.fetchone()[0]
                
                # List tables
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'trading' 
                    ORDER BY table_name
                """)
                result["tables"] = [row[0] for row in cur.fetchall()]
                result["db_connection"] = "SUCCESS"
    except Exception as e:
        result["error"] = str(e)
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
