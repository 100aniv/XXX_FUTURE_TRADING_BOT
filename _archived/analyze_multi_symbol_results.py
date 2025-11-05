#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
멀티 심볼 백테스트 결과 분석
============================
심볼별 성과 비교 분석
"""
import sqlite3
import pandas as pd
from pathlib import Path

DB_FILE = 'backtest_results.db'

def analyze_by_symbol():
    """심볼별 분석"""
    conn = sqlite3.connect(DB_FILE)
    
    query = """
    SELECT 
        symbol,
        strategy,
        COUNT(*) as trades,
        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses,
        ROUND(AVG(CASE WHEN pnl > 0 THEN 1.0 ELSE 0.0 END) * 100, 2) as win_rate,
        ROUND(SUM(pnl), 2) as total_pnl,
        ROUND(AVG(pnl), 2) as avg_pnl,
        ROUND(MAX(pnl), 2) as max_profit,
        ROUND(MIN(pnl), 2) as max_loss
    FROM trades
    WHERE exit_price IS NOT NULL
    GROUP BY symbol, strategy
    ORDER BY symbol, total_pnl DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df


def analyze_by_symbol_total():
    """심볼별 총합"""
    conn = sqlite3.connect(DB_FILE)
    
    query = """
    SELECT 
        symbol,
        COUNT(*) as trades,
        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(AVG(CASE WHEN pnl > 0 THEN 1.0 ELSE 0.0 END) * 100, 2) as win_rate,
        ROUND(SUM(pnl), 2) as total_pnl,
        ROUND(AVG(pnl), 2) as avg_pnl
    FROM trades
    WHERE exit_price IS NOT NULL
    GROUP BY symbol
    ORDER BY total_pnl DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df


def main():
    print("="*80)
    print("📊 멀티 심볼 백테스트 결과 분석")
    print("="*80)
    print()
    
    # 1. 심볼별 총합
    print("## 1️⃣ 심볼별 총 성과")
    print("="*80)
    df_total = analyze_by_symbol_total()
    print(df_total.to_string(index=False))
    print()
    
    # 2. 심볼별 전략 성과
    print("## 2️⃣ 심볼별 전략 성과 (Top 5 per symbol)")
    print("="*80)
    df_detail = analyze_by_symbol()
    
    for symbol in df_detail['symbol'].unique():
        print(f"\n### {symbol}")
        symbol_data = df_detail[df_detail['symbol'] == symbol].head(5)
        print(symbol_data[['strategy', 'trades', 'win_rate', 'total_pnl']].to_string(index=False))
    
    print()
    print("="*80)
    print("✅ 분석 완료")
    print("="*80)
    print()
    
    # 3. 요약
    print("## 📝 핵심 발견:")
    print()
    
    best_symbol = df_total.iloc[0]
    worst_symbol = df_total.iloc[-1]
    
    print(f"✅ 최고 심볼: {best_symbol['symbol']}")
    print(f"   - PnL: ${best_symbol['total_pnl']:,.2f}")
    print(f"   - 승률: {best_symbol['win_rate']}%")
    print(f"   - 거래: {best_symbol['trades']}건")
    print()
    
    print(f"❌ 최악 심볼: {worst_symbol['symbol']}")
    print(f"   - PnL: ${worst_symbol['total_pnl']:,.2f}")
    print(f"   - 승률: {worst_symbol['win_rate']}%")
    print(f"   - 거래: {worst_symbol['trades']}건")
    print()
    
    profitable_symbols = df_total[df_total['total_pnl'] > 0]
    print(f"💰 수익 심볼: {len(profitable_symbols)}개 / {len(df_total)}개")
    if len(profitable_symbols) > 0:
        print(profitable_symbols[['symbol', 'total_pnl']].to_string(index=False))


if __name__ == '__main__':
    main()
