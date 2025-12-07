#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema='tuning' AND table_name='results'
            ORDER BY ordinal_position
        """)
        cols = cur.fetchall()
        print("tuning.results columns:")
        for col in cols:
            print(f"  - {col[0]} ({col[1]})")
