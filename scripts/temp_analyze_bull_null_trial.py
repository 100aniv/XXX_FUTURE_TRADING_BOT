#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trial_id=NULL인 Bull 백테스트 결과 분석
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection
import json
import numpy as np
from datetime import datetime

def calculate_sharpe_ratio(returns):
    if len(returns) == 0:
        return 0.0
    mean_return = np.mean(returns)
    std_return = np.std(returns, ddof=1) if len(returns) > 1 else 0.0
    if std_return == 0:
        return 0.0
    return mean_return / std_return

def calculate_max_drawdown(equity_curve):
    if len(equity_curve) == 0:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    return max_dd

def analyze_bull_trades():
    """Bull 백테스트 결과 분석"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 2024-10 기간, trial_id NULL 거래 조회
            cur.execute("""
                SELECT
                    ts_open,
                    ts_close,
                    side,
                    entry_price,
                    exit_price,
                    quantity,
                    pnl,
                    pnl_pct,
                    fees,
                    strategy_id
                FROM trading.trades
                WHERE trial_id IS NULL
                  AND ts_open >= '2024-10-01'
                  AND ts_open < '2024-11-01'
                ORDER BY ts_open
            """)
            
            trades = cur.fetchall()
            
            if not trades:
                print("⚠️ 2024-10 기간 거래 데이터 없음")
                return
            
            print(f"✅ {len(trades)}개 거래 데이터 조회 완료")
            
            # 메트릭 계산
            total_trades = len(trades)
            long_trades = sum(1 for t in trades if t[2] == 'LONG')
            short_trades = sum(1 for t in trades if t[2] == 'SHORT')
            
            pnls = [float(t[6]) for t in trades if t[6] is not None]
            pnl_pcts = [float(t[7]) for t in trades if t[7] is not None]
            
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p <= 0]
            
            win_count = len(wins)
            loss_count = len(losses)
            win_rate = win_count / total_trades if total_trades > 0 else 0.0
            
            total_pnl = sum(pnls)
            avg_pnl = np.mean(pnls) if pnls else 0.0
            avg_win = np.mean(wins) if wins else 0.0
            avg_loss = np.mean(losses) if losses else 0.0
            
            # Profit Factor
            gross_profit = sum(wins) if wins else 0.0
            gross_loss = abs(sum(losses)) if losses else 0.0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
            
            # Sharpe Ratio
            sharpe = calculate_sharpe_ratio(pnl_pcts)
            
            # Equity Curve & Max Drawdown
            equity_curve = [50000.0]
            for pnl in pnls:
                equity_curve.append(equity_curve[-1] + pnl)
            
            max_dd = calculate_max_drawdown(equity_curve)
            final_equity = equity_curve[-1]
            total_return_pct = ((final_equity - 50000) / 50000) * 100
            
            # 결과 출력
            print("\n" + "=" * 80)
            print("📊 BULL Period 백테스트 결과 (2024-10-01 ~ 2024-10-31)")
            print("=" * 80)
            print(f"\n📈 Trades: {total_trades} (Long: {long_trades}, Short: {short_trades})")
            print(f"💹 Win Rate: {round(win_rate * 100, 2)}%")
            print(f"📊 Sharpe Ratio: {round(sharpe, 4)}")
            print(f"💰 Total PnL: ${round(total_pnl, 2)}")
            print(f"📉 Max Drawdown: {round(max_dd * 100, 2)}%")
            print(f"🎯 Total Return: {round(total_return_pct, 2)}%")
            print(f"💵 Final Equity: ${round(final_equity, 2)}")
            print("=" * 80 + "\n")
            
            # JSON 저장
            results = {
                'run_id': 'phase28_8_btc5m_baseline_v2_bull',
                'period': '2024-10-01 ~ 2024-10-31',
                'timestamp': datetime.now().isoformat(),
                'trades': {
                    'total': total_trades,
                    'long': long_trades,
                    'short': short_trades,
                    'long_short_ratio': long_trades / short_trades if short_trades > 0 else 0.0
                },
                'performance': {
                    'win_count': win_count,
                    'loss_count': loss_count,
                    'win_rate': round(win_rate * 100, 2),
                    'profit_factor': round(profit_factor, 3),
                    'sharpe_ratio': round(sharpe, 4)
                },
                'pnl': {
                    'total': round(total_pnl, 2),
                    'avg_pnl': round(avg_pnl, 2),
                    'avg_win': round(avg_win, 2),
                    'avg_loss': round(avg_loss, 2),
                    'total_return_pct': round(total_return_pct, 2)
                },
                'risk': {
                    'max_drawdown': round(max_dd * 100, 2),
                    'final_equity': round(final_equity, 2)
                }
            }
            
            output_file = 'reports/backtest/phase28_8/baseline_bull.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"💾 결과 저장: {output_file}\n")

if __name__ == "__main__":
    analyze_bull_trades()
