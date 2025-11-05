#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
백테스트 상태 확인 스크립트
"""
import sqlite3
from pathlib import Path

db_file = Path(__file__).parent.parent / 'backtest_results.db'

if not db_file.exists():
    print("❌ 백테스트 DB 없음 - 백테스트 미실행")
    exit(0)

print(f"📂 DB 파일: {db_file.name}")
print(f"📊 크기: {db_file.stat().st_size / 1024:.2f} KB\n")

conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# 테이블 확인
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"📋 테이블: {tables}\n")

if 'trades' in tables:
    # 거래 통계
    cursor.execute("SELECT COUNT(*) FROM trades")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM trades WHERE exit_price IS NOT NULL")
    closed = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM trades WHERE exit_price IS NULL")
    open_trades = cursor.fetchone()[0]
    
    print(f"📊 거래 통계:")
    print(f"   - 총 진입: {total}건")
    print(f"   - 종료: {closed}건")
    print(f"   - 활성: {open_trades}건\n")
    
    if closed > 0:
        # PnL 통계
        cursor.execute("SELECT SUM(pnl), AVG(pnl) FROM trades WHERE exit_price IS NOT NULL")
        total_pnl, avg_pnl = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) FROM trades WHERE exit_price IS NOT NULL AND pnl > 0")
        wins = cursor.fetchone()[0]
        
        win_rate = (wins / closed * 100) if closed > 0 else 0
        
        print(f"💰 PnL 통계:")
        print(f"   - 총 PnL: ${total_pnl:.2f}")
        print(f"   - 평균 PnL: ${avg_pnl:.2f}")
        print(f"   - Win Rate: {win_rate:.1f}% ({wins}/{closed})\n")
        
        # 최근 5건
        cursor.execute("""
            SELECT strategy, side, entry_price, exit_price, pnl, exit_reason
            FROM trades 
            WHERE exit_price IS NOT NULL 
            ORDER BY rowid DESC 
            LIMIT 5
        """)
        
        print(f"📝 최근 5건 거래:")
        for row in cursor.fetchall():
            strategy, side, entry, exit_price, pnl, reason = row
            print(f"   - {strategy} {side}: {entry:.2f} → {exit_price:.2f}, PnL: ${pnl:.2f} ({reason})")
else:
    print("⚠️  거래 데이터 없음")

conn.close()
