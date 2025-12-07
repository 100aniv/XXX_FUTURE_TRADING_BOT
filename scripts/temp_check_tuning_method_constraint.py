#!/usr/bin/env python3
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT pg_get_constraintdef(oid) 
            FROM pg_constraint 
            WHERE conname = 'runs_tuning_method_check'
        """)
        constraint = cur.fetchone()
        
        if constraint:
            print("tuning_method constraint:")
            print(constraint[0])
        else:
            print("Constraint not found")
