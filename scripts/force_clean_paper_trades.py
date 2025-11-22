#!/usr/bin/env python3
"""
Force clean paper trades using various methods
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

# Method 1: Try with explicit transaction
print("[Method 1] DELETE with explicit transaction...")
conn = get_conn()
conn.set_session(autocommit=False)
cur = conn.cursor()

cur.execute("BEGIN")
cur.execute("SELECT COUNT(*) FROM trading.trades WHERE mode='paper'")
before = cur.fetchone()[0]
print(f"  Before: {before}")

cur.execute("DELETE FROM trading.trades WHERE mode='paper'")
deleted = cur.rowcount
print(f"  Deleted: {deleted}")

cur.execute("COMMIT")
conn.commit()

cur.execute("SELECT COUNT(*) FROM trading.trades WHERE mode='paper'")
after = cur.fetchone()[0]
print(f"  After commit: {after}")

cur.close()
conn.close()

# Verify with new connection
print("\n[Verify] New connection check...")
conn2 = get_conn()
cur2 = conn2.cursor()
cur2.execute("SELECT COUNT(*) FROM trading.trades WHERE mode='paper'")
final = cur2.fetchone()[0]
print(f"  Final count: {final}")
cur2.close()
conn2.close()

if final > 0:
    print("\n[CRITICAL] DELETE with transaction FAILED!")
    print("There might be triggers or constraints preventing deletion.")
else:
    print("\n[SUCCESS] Paper trades cleaned successfully!")
