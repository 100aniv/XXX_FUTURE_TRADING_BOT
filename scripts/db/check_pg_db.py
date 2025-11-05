#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PostgreSQL DB 확인"""
import os
os.environ['DATABASE_URL'] = 'postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db'

from common.database import get_db_connection

print("=" * 80)
print("PostgreSQL DB 확인")
print("=" * 80)

try:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1. trades 테이블 개수
            cur.execute("SELECT COUNT(*) FROM trading.trades")
            total_trades = cur.fetchone()[0]
            print(f"\n✅ Total trades: {total_trades}개")
            
            # 2. 최근 거래 5개
            if total_trades > 0:
                cur.execute("""
                    SELECT trade_id, symbol, side, quantity, entry_price, status, ts_open 
                    FROM trading.trades 
                    ORDER BY ts_open DESC 
                    LIMIT 5
                """)
                print("\n📊 최근 거래 5개:")
                for row in cur.fetchall():
                    print(f"   {row[1]} {row[2]} | Qty: {row[3]:.2f} | Entry: ${row[4]:.4f} | Status: {row[5]}")
            
            # 3. positions 테이블 개수
            cur.execute("SELECT COUNT(*) FROM trading.positions")
            total_positions = cur.fetchone()[0]
            print(f"\n✅ Active positions: {total_positions}개")
            
            # 4. 현재 포지션
            if total_positions > 0:
                cur.execute("""
                    SELECT position_id, symbol, side, quantity, avg_entry 
                    FROM trading.positions 
                    ORDER BY opened_at DESC
                """)
                print("\n📊 현재 포지션:")
                for row in cur.fetchall():
                    print(f"   {row[1]} {row[2]} | Qty: {row[3]:.2f} | Entry: ${row[4]:.4f}")
                    
except Exception as e:
    print(f"\n❌ DB 연결 실패: {e}")

print("\n" + "=" * 80)
