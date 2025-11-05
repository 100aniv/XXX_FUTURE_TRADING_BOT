#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DB 상태 확인
"""
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT')),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)

try:
    with conn.cursor() as cur:
        # 1. signals 확인
        print("=" * 60)
        print("1️⃣  monitoring.signals (최근 10건)")
        print("=" * 60)
        cur.execute("""
            SELECT strategy_id, symbol, direction, entry_price, sl_price, tp_price, created_at
            FROM monitoring.signals
            ORDER BY created_at DESC
            LIMIT 10
        """)
        rows = cur.fetchall()
        if rows:
            for r in rows:
                print(f"{r[0]:10} {r[1]:15} {r[2]:5} entry={r[3]} sl={r[4]} tp={r[5]} @ {r[6]}")
        else:
            print("⚠️  signals 테이블 비어있음!")
        
        print()
        print("=" * 60)
        print("2️⃣  trading.decisions (최근 10건)")
        print("=" * 60)
        cur.execute("""
            SELECT symbol, chosen_side, entry_price, sl_price, tp_price, chosen_size, created_at
            FROM trading.decisions
            ORDER BY created_at DESC
            LIMIT 10
        """)
        rows = cur.fetchall()
        if rows:
            for r in rows:
                print(f"{r[0]:15} {r[1]:5} entry={r[2]} sl={r[3]} tp={r[4]} size={r[5]} @ {r[6]}")
        else:
            print("⚠️  decisions 테이블 비어있음!")
        
        print()
        print("=" * 60)
        print("3️⃣  trading.trades (최근 5건)")
        print("=" * 60)
        cur.execute("""
            SELECT symbol, side, entry_price, quantity, status, created_at
            FROM trading.trades
            ORDER BY created_at DESC
            LIMIT 5
        """)
        rows = cur.fetchall()
        if rows:
            for r in rows:
                print(f"{r[0]:15} {r[1]:5} {r[2]} qty={r[3]} {r[4]} @ {r[5]}")
        else:
            print("⚠️  trades 테이블 비어있음!")
            
except Exception as e:
    print(f"❌ 에러: {e}")
finally:
    conn.close()
