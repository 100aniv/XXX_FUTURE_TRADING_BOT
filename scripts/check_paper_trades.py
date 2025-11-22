#!/usr/bin/env python3
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT')),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)

cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM trading.trades WHERE mode='paper'")
count = cur.fetchone()[0]
print(f"Paper trades in DB: {count}")

cur.close()
conn.close()
