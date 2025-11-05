#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""백테스트 결과 분석"""
import sqlite3
import pandas as pd

conn = sqlite3.connect('backtest.db')

# 기본 통계
print("=" * 80)
print("📊 백테스트 결과 분석")
print("=" * 80)

# 전체 통계
df = pd.read_sql_query("""
    SELECT 
        COUNT(*) as total_trades,
        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses,
        AVG(pnl) as avg_pnl,
        SUM(pnl) as total_pnl,
        AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
        AVG(CASE WHEN pnl <= 0 THEN pnl END) as avg_loss
    FROM trades 
    WHERE exit_reason IS NOT NULL
""", conn)

print(f"\n총 거래: {df['total_trades'][0]}건")
print(f"승리: {df['wins'][0]}건 ({df['wins'][0]/df['total_trades'][0]*100:.1f}%)")
print(f"손실: {df['losses'][0]}건 ({df['losses'][0]/df['total_trades'][0]*100:.1f}%)")
print(f"평균 PnL: ${df['avg_pnl'][0]:.2f}")
print(f"총 PnL: ${df['total_pnl'][0]:.2f}")
print(f"평균 승리: ${df['avg_win'][0]:.2f}")
print(f"평균 손실: ${df['avg_loss'][0]:.2f}")
if df['avg_loss'][0] != 0:
    print(f"손익비 (RR): {abs(df['avg_win'][0] / df['avg_loss'][0]):.2f}")

# 청산 사유별
print("\n" + "=" * 80)
print("📈 청산 사유별 분석")
print("=" * 80)
reason_df = pd.read_sql_query("""
    SELECT 
        exit_reason,
        COUNT(*) as count,
        AVG(pnl) as avg_pnl,
        SUM(pnl) as total_pnl
    FROM trades 
    WHERE exit_reason IS NOT NULL
    GROUP BY exit_reason
    ORDER BY count DESC
""", conn)
print(reason_df.to_string(index=False))

# 심볼별
print("\n" + "=" * 80)
print("💰 심볼별 분석")
print("=" * 80)
symbol_df = pd.read_sql_query("""
    SELECT 
        symbol,
        COUNT(*) as count,
        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
        AVG(pnl) as avg_pnl,
        SUM(pnl) as total_pnl
    FROM trades 
    WHERE exit_reason IS NOT NULL
    GROUP BY symbol
    ORDER BY total_pnl DESC
""", conn)
symbol_df['win_rate'] = (symbol_df['wins'] / symbol_df['count'] * 100).round(1)
print(symbol_df.to_string(index=False))

# 전략별
print("\n" + "=" * 80)
print("🎯 전략별 분석")
print("=" * 80)
strategy_df = pd.read_sql_query("""
    SELECT 
        strategy_id,
        COUNT(*) as count,
        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
        AVG(pnl) as avg_pnl,
        SUM(pnl) as total_pnl
    FROM trades 
    WHERE exit_reason IS NOT NULL
    GROUP BY strategy_id
    ORDER BY total_pnl DESC
""", conn)
strategy_df['win_rate'] = (strategy_df['wins'] / strategy_df['count'] * 100).round(1)
print(strategy_df.to_string(index=False))

# TP 분할 효과 분석
print("\n" + "=" * 80)
print("🎯 TP 분할 효과 분석")
print("=" * 80)
tp_stats = pd.read_sql_query("""
    SELECT 
        exit_reason,
        COUNT(*) as count,
        AVG(pnl) as avg_pnl
    FROM trades 
    WHERE exit_reason IN ('TP1', 'TP2', 'TP', 'TRAILING_SL')
    GROUP BY exit_reason
    ORDER BY 
        CASE exit_reason 
            WHEN 'TP1' THEN 1 
            WHEN 'TP2' THEN 2 
            WHEN 'TRAILING_SL' THEN 3 
            ELSE 4 
        END
""", conn)
if len(tp_stats) > 0:
    print(tp_stats.to_string(index=False))
    tp1_count = tp_stats[tp_stats['exit_reason'] == 'TP1']['count'].sum()
    tp2_count = tp_stats[tp_stats['exit_reason'] == 'TP2']['count'].sum()
    trail_count = tp_stats[tp_stats['exit_reason'] == 'TRAILING_SL']['count'].sum()
    print(f"\nTP1 도달: {tp1_count}건 (30% 청산)")
    print(f"TP2 도달: {tp2_count}건 (40% 청산)")
    print(f"트레일링 청산: {trail_count}건 (나머지 30%)")
else:
    print("TP 분할 데이터 없음")

conn.close()
print("\n" + "=" * 80)
