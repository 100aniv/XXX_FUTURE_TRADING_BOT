#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.postgres import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema='trading' AND table_name='trades' 
            ORDER BY ordinal_position
        """)
        print("trading.trades schema:")
        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]}")
