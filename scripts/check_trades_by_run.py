#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE22-2: Run ID 기반 트레이드 조회 및 전략별 통계
========================================================
Usage:
    python scripts/check_trades_by_run.py --run-id 20251122_194150_ouhr
    python scripts/check_trades_by_run.py --run-id 20251122_194150_ouhr --detailed
"""
import sys
import argparse
import psycopg2
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import os

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()


def get_db_connection():
    """DB 연결 생성"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5433)),
        database=os.getenv('DB_NAME', 'trading_bot'),
        user=os.getenv('DB_USER', 'trading_user'),
        password=os.getenv('DB_PASSWORD', 'trading_pass')
    )


def get_run_summary(conn, run_id=None):
    """Run ID별 전체 요약"""
    cur = conn.cursor()
    
    if run_id:
        query = """
        SELECT 
            run_id,
            COUNT(*) as trade_count,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as win_count,
            SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as loss_count,
            SUM(pnl) as total_pnl,
            AVG(pnl) as avg_pnl,
            MAX(pnl) as max_pnl,
            MIN(pnl) as min_pnl,
            MIN(entry_time) as first_trade,
            MAX(exit_time) as last_trade
        FROM trading.trades
        WHERE mode = 'paper' AND run_id = %s
        GROUP BY run_id
        """
        cur.execute(query, (run_id,))
    else:
        query = """
        SELECT 
            run_id,
            COUNT(*) as trade_count,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as win_count,
            SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as loss_count,
            SUM(pnl) as total_pnl,
            AVG(pnl) as avg_pnl,
            MAX(pnl) as max_pnl,
            MIN(pnl) as min_pnl,
            MIN(entry_time) as first_trade,
            MAX(exit_time) as last_trade
        FROM trading.trades
        WHERE mode = 'paper'
        GROUP BY run_id
        ORDER BY MIN(entry_time) DESC
        LIMIT 10
        """
        cur.execute(query)
    
    rows = cur.fetchall()
    cur.close()
    
    return rows


def get_strategy_stats(conn, run_id):
    """전략별 통계"""
    cur = conn.cursor()
    
    query = """
    SELECT 
        strategy,
        COUNT(*) as trade_count,
        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as win_count,
        SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as loss_count,
        SUM(pnl) as total_pnl,
        AVG(pnl) as avg_pnl,
        MAX(pnl) as max_pnl,
        MIN(pnl) as min_pnl,
        SUM(CASE WHEN side = 'LONG' THEN 1 ELSE 0 END) as long_count,
        SUM(CASE WHEN side = 'SHORT' THEN 1 ELSE 0 END) as short_count
    FROM trading.trades
    WHERE mode = 'paper' AND run_id = %s
    GROUP BY strategy
    ORDER BY trade_count DESC
    """
    
    cur.execute(query, (run_id,))
    rows = cur.fetchall()
    cur.close()
    
    return rows


def get_detailed_trades(conn, run_id, limit=50):
    """상세 트레이드 내역"""
    cur = conn.cursor()
    
    query = """
    SELECT 
        id,
        strategy,
        symbol,
        side,
        entry_price,
        exit_price,
        quantity,
        pnl,
        pnl_pct,
        entry_time,
        exit_time
    FROM trading.trades
    WHERE mode = 'paper' AND run_id = %s
    ORDER BY entry_time DESC
    LIMIT %s
    """
    
    cur.execute(query, (run_id, limit))
    rows = cur.fetchall()
    cur.close()
    
    return rows


def print_summary(rows):
    """요약 출력"""
    print("\n" + "=" * 100)
    print("📊 Run ID별 트레이드 요약")
    print("=" * 100)
    
    if not rows:
        print("⚠️  트레이드 없음")
        return
    
    header = f"{'Run ID':<25} {'Trades':>8} {'Win':>5} {'Loss':>5} {'Win%':>6} {'Total PnL':>12} {'Avg PnL':>10} {'Duration':>20}"
    print(header)
    print("-" * 100)
    
    for row in rows:
        run_id, trade_count, win_count, loss_count, total_pnl, avg_pnl, max_pnl, min_pnl, first_trade, last_trade = row
        
        win_rate = (win_count / trade_count * 100) if trade_count > 0 else 0
        
        if first_trade and last_trade:
            duration = last_trade - first_trade
            duration_str = str(duration).split('.')[0]  # 소수점 제거
        else:
            duration_str = "N/A"
        
        print(f"{run_id:<25} {trade_count:>8} {win_count:>5} {loss_count:>5} {win_rate:>5.1f}% "
              f"${total_pnl:>11.2f} ${avg_pnl:>9.2f} {duration_str:>20}")
    
    print("=" * 100)


def print_strategy_stats(rows, total_trades):
    """전략별 통계 출력"""
    print("\n" + "=" * 100)
    print("🎯 전략별 트레이드 통계")
    print("=" * 100)
    
    if not rows:
        print("⚠️  트레이드 없음")
        return
    
    header = f"{'Strategy':<20} {'Trades':>8} {'Win':>5} {'Loss':>5} {'Win%':>6} {'Ratio':>7} {'Total PnL':>12} {'Avg PnL':>10} {'L/S':>8}"
    print(header)
    print("-" * 100)
    
    for row in rows:
        strategy, trade_count, win_count, loss_count, total_pnl, avg_pnl, max_pnl, min_pnl, long_count, short_count = row
        
        win_rate = (win_count / trade_count * 100) if trade_count > 0 else 0
        ratio = (trade_count / total_trades * 100) if total_trades > 0 else 0
        
        print(f"{strategy:<20} {trade_count:>8} {win_count:>5} {loss_count:>5} {win_rate:>5.1f}% {ratio:>6.1f}% "
              f"${total_pnl:>11.2f} ${avg_pnl:>9.2f} {long_count:>3}/{short_count:<3}")
    
    print("=" * 100)
    
    # Acceptance Criteria 체크
    print("\n📋 Acceptance Criteria 체크:")
    max_ratio = max([row[1] / total_trades * 100 for row in rows]) if rows else 0
    if max_ratio >= 80:
        print(f"  ❌ 특정 전략 편중도: {max_ratio:.1f}% (기준: < 80%)")
    else:
        print(f"  ✅ 특정 전략 편중도: {max_ratio:.1f}% (기준: < 80%)")
    
    strategy_with_trades = sum(1 for row in rows if row[1] > 0)
    if strategy_with_trades >= 2:
        print(f"  ✅ 2개 이상 전략 참여: {strategy_with_trades}개")
    else:
        print(f"  ❌ 2개 이상 전략 참여: {strategy_with_trades}개 (기준: ≥ 2)")


def print_detailed_trades(rows):
    """상세 트레이드 출력"""
    print("\n" + "=" * 120)
    print("📝 최근 트레이드 상세 내역 (최대 50개)")
    print("=" * 120)
    
    if not rows:
        print("⚠️  트레이드 없음")
        return
    
    header = f"{'ID':>6} {'Strategy':<15} {'Symbol':<10} {'Side':<6} {'Entry':>10} {'Exit':>10} {'Qty':>8} {'PnL':>10} {'PnL%':>7} {'Entry Time':>19} {'Exit Time':>19}"
    print(header)
    print("-" * 120)
    
    for row in rows:
        trade_id, strategy, symbol, side, entry_price, exit_price, quantity, pnl, pnl_pct, entry_time, exit_time = row
        
        entry_time_str = entry_time.strftime('%Y-%m-%d %H:%M:%S') if entry_time else 'N/A'
        exit_time_str = exit_time.strftime('%Y-%m-%d %H:%M:%S') if exit_time else 'N/A'
        
        print(f"{trade_id:>6} {strategy:<15} {symbol:<10} {side:<6} "
              f"{entry_price:>10.2f} {exit_price:>10.2f} {quantity:>8.4f} "
              f"${pnl:>9.2f} {pnl_pct:>6.2f}% {entry_time_str:>19} {exit_time_str:>19}")
    
    print("=" * 120)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='PHASE22-2: Run ID 기반 트레이드 조회',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--run-id',
        type=str,
        default=None,
        help='Run ID (지정하지 않으면 최근 10개 Run 요약)'
    )
    
    parser.add_argument(
        '--detailed',
        action='store_true',
        default=False,
        help='상세 트레이드 내역 출력'
    )
    
    args = parser.parse_args()
    
    try:
        conn = get_db_connection()
        
        # 1. Run 요약
        summary_rows = get_run_summary(conn, args.run_id)
        print_summary(summary_rows)
        
        # 2. Run ID 지정 시 추가 정보
        if args.run_id and summary_rows:
            total_trades = summary_rows[0][1]  # trade_count
            
            # 전략별 통계
            strategy_rows = get_strategy_stats(conn, args.run_id)
            print_strategy_stats(strategy_rows, total_trades)
            
            # 상세 내역 (옵션)
            if args.detailed:
                detailed_rows = get_detailed_trades(conn, args.run_id)
                print_detailed_trades(detailed_rows)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
