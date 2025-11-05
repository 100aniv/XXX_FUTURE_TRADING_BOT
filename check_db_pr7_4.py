#!/usr/bin/env python3
"""PR7-4 DB 검증"""
import os
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost:5432/test')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_PORT', '5432')
os.environ.setdefault('DB_NAME', 'test')
os.environ.setdefault('DB_USER', 'test')
os.environ.setdefault('DB_PASSWORD', 'test')

from common.database import get_db_connection

print("🔍 PR7-4 DB 검증 시작...\n")

try:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. 다중 TF 신호 확인
        print("=" * 60)
        print("1. 다중 Timeframe 신호 생성 확인")
        print("=" * 60)
        cursor.execute("""
            SELECT timeframe, COUNT(*) AS cnt, MAX(created_at) AS last
            FROM monitoring.signals
            WHERE created_at > NOW() - INTERVAL '1 hour'
            GROUP BY timeframe
            ORDER BY timeframe
        """)
        signals = cursor.fetchall()
        if signals:
            for row in signals:
                print(f"   {row[0]}: {row[1]}개 | 최근: {row[2]}")
        else:
            print("   ⚠️ 신호 없음 (정상: 캔들 생성 대기 중)")
        
        # 2. 앙상블 결정 확인
        print("\n" + "=" * 60)
        print("2. 앙상블 결정 생성 확인")
        print("=" * 60)
        cursor.execute("""
            SELECT COUNT(*) as cnt, MAX(created_at) as last
            FROM trading.decisions
            WHERE created_at > NOW() - INTERVAL '1 hour'
        """)
        decisions = cursor.fetchone()
        print(f"   총 결정: {decisions[0]}개")
        print(f"   최근: {decisions[1]}")
        
        # 3. 거래 확인
        print("\n" + "=" * 60)
        print("3. Paper 거래 확인")
        print("=" * 60)
        cursor.execute("""
            SELECT symbol, side, entry_price, exit_price, pnl, 
                   exit_reason, created_at
            FROM trading.trades
            WHERE created_at > NOW() - INTERVAL '1 hour'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        trades = cursor.fetchall()
        if trades:
            for trade in trades:
                exit_price = trade[3] if trade[3] else 0
                pnl = trade[4] if trade[4] else 0
                exit_reason = trade[5] if trade[5] else 'N/A'
                print(f"   {trade[6]} | {trade[0]} {trade[1].upper()} @ {trade[2]:.2f} → {exit_price:.2f} | PnL: ${pnl:.2f} | {exit_reason}")
        else:
            print("   거래 없음 (정상: 신호 대기 중)")
        
        # 4. 활성 포지션 확인
        print("\n" + "=" * 60)
        print("4. 활성 포지션 확인")
        print("=" * 60)
        cursor.execute("""
            SELECT symbol, side, entry_price, qty, unrealized_pnl
            FROM trading.positions
            WHERE status = 'OPEN'
        """)
        positions = cursor.fetchall()
        if positions:
            for pos in positions:
                print(f"   {pos[0]} {pos[1].upper()} @ {pos[2]:.2f} | Qty: {pos[3]:.4f} | PnL: ${pos[4]:.2f}")
        else:
            print("   활성 포지션 없음")
        
        print("\n✅ DB 검증 완료!")
        
except Exception as e:
    print(f"❌ DB 검증 실패: {e}")
    import traceback
    traceback.print_exc()
