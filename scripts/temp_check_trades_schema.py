#!/usr/bin/env python3
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema='trading' AND table_name='trades' 
            ORDER BY ordinal_position
        """)
        columns = [row[0] for row in cur.fetchall()]
        
        print("trading.trades columns:")
        for col in columns:
            print(f"  - {col}")
