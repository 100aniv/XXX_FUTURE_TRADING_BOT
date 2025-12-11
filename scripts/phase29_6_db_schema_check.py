#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE29-6: DB Schema & trial_id/run_id 분석
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from common.database import get_db_connection

def main():
    print("=" * 80)
    print("PHASE29-6: DB Schema & trial_id/run_id Analysis")
    print("=" * 80)
    print()
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1. trading.trades 스키마
            print("1. trading.trades 스키마:")
            cur.execute("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_schema='trading' AND table_name='trades' 
                ORDER BY ordinal_position
            """)
            for row in cur.fetchall():
                print(f"   {row[0]:20} {row[1]:20} NULL={row[2]}")
            print()
            
            # 2. trial_id 분포
            print("2. trading.trades trial_id 분포:")
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(trial_id) as with_trial_id,
                    COUNT(DISTINCT trial_id) as unique_trial_ids
                FROM trading.trades
                WHERE status='CLOSED'
            """)
            row = cur.fetchone()
            print(f"   Total CLOSED trades: {row[0]}")
            print(f"   With trial_id: {row[1]}")
            print(f"   Unique trial_ids: {row[2]}")
            print()
            
            # 3. 최근 10개 trial_id (각 trial_id별 trade 수 포함)
            print("3. 최근 10개 trial_id:")
            cur.execute("""
                SELECT trial_id, COUNT(*) as num_trades, MAX(ts_close) as last_close
                FROM trading.trades 
                WHERE trial_id IS NOT NULL AND status='CLOSED'
                GROUP BY trial_id
                ORDER BY last_close DESC
                LIMIT 10
            """)
            for row in cur.fetchall():
                print(f"   {row[0]:40} ({row[1]:3} trades)")
            print()
            
            # 4. mode 분포
            print("4. trading.trades mode 분포:")
            cur.execute("""
                SELECT mode, COUNT(*) 
                FROM trading.trades 
                WHERE status='CLOSED'
                GROUP BY mode
                ORDER BY COUNT(*) DESC
            """)
            for row in cur.fetchall():
                print(f"   {row[0]:10} {row[1]:5} trades")
            print()
            
            # 5. 최근 백테스트 trade 샘플
            print("5. 최근 backtest trade (5개):")
            cur.execute("""
                SELECT trade_id, trial_id, symbol, pnl, ts_close 
                FROM trading.trades 
                WHERE mode='backtest' AND status='CLOSED'
                ORDER BY ts_close DESC
                LIMIT 5
            """)
            for row in cur.fetchall():
                trial_str = row[1][:20] if row[1] else 'NULL'
                print(f"   {row[0][:12]}... trial_id={trial_str:20} pnl={row[3]:8.2f}")
            print()

if __name__ == "__main__":
    main()
