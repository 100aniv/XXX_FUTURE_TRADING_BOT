#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-8: Multi-Period Baseline 결과 분석 스크립트
================================================
DB에서 백테스트 결과를 조회하고 메트릭 계산

Usage:
    python scripts/analysis/phase28_8_analyze_baseline.py --run-id phase28_8_btc5m_baseline_v2_bull
    python scripts/analysis/phase28_8_analyze_baseline.py --period bull
"""
import sys
import os
import argparse
import json
from pathlib import Path
from datetime import datetime
import numpy as np

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from common.logger import setup_logger
from database import get_db_connection

logger = setup_logger("phase28_8_analyze")


def calculate_sharpe_ratio(returns, risk_free_rate=0.0):
    """Sharpe Ratio 계산"""
    if len(returns) == 0:
        return 0.0
    
    mean_return = np.mean(returns)
    std_return = np.std(returns, ddof=1) if len(returns) > 1 else 0.0
    
    if std_return == 0:
        return 0.0
    
    return (mean_return - risk_free_rate) / std_return


def calculate_max_drawdown(equity_curve):
    """Max Drawdown 계산"""
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


def analyze_backtest_results(run_id, output_file=None):
    """
    백테스트 결과 분석
    
    Args:
        run_id: 백테스트 run_id
        output_file: JSON 결과 파일 경로 (optional)
    
    Returns:
        dict: 분석 결과
    """
    logger.info(f"📊 백테스트 결과 분석 시작: {run_id}")
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 1. Trade 데이터 조회
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
                    WHERE trial_id = %s
                    ORDER BY ts_open
                """, (run_id,))
                
                trades = cur.fetchall()
                
                if not trades:
                    logger.warning(f"⚠️ {run_id}에 대한 거래 데이터 없음")
                    return {
                        'run_id': run_id,
                        'trades': 0,
                        'error': 'No trades found'
                    }
                
                logger.info(f"✅ {len(trades)}개 거래 데이터 조회 완료")
                
                # 2. 메트릭 계산
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
                equity_curve = [50000.0]  # Initial capital
                for pnl in pnls:
                    equity_curve.append(equity_curve[-1] + pnl)
                
                max_dd = calculate_max_drawdown(equity_curve)
                final_equity = equity_curve[-1]
                total_return_pct = ((final_equity - 50000) / 50000) * 100
                
                # 3. 결과 딕셔너리
                results = {
                    'run_id': run_id,
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
                
                # 4. JSON 파일로 저장
                if output_file:
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False)
                    logger.info(f"💾 결과 저장: {output_file}")
                
                # 5. 콘솔 출력
                print("\n" + "=" * 80)
                print(f"📊 백테스트 결과 요약: {run_id}")
                print("=" * 80)
                print(f"\n📈 Trades: {total_trades} (Long: {long_trades}, Short: {short_trades})")
                print(f"💹 Win Rate: {results['performance']['win_rate']}%")
                print(f"📊 Sharpe Ratio: {results['performance']['sharpe_ratio']}")
                print(f"💰 Total PnL: ${results['pnl']['total']}")
                print(f"📉 Max Drawdown: {results['risk']['max_drawdown']}%")
                print(f"🎯 Total Return: {results['pnl']['total_return_pct']}%")
                print("=" * 80 + "\n")
                
                return results
        
    except Exception as e:
        logger.error(f"❌ 분석 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def main():
    """메인 진입점"""
    parser = argparse.ArgumentParser(description='PHASE28-8 Baseline 백테스트 결과 분석')
    parser.add_argument('--run-id', type=str, help='백테스트 run_id')
    parser.add_argument('--period', type=str, choices=['bull', 'bear', 'range'], 
                        help='분석할 Period (bull/bear/range)')
    parser.add_argument('--output', type=str, help='결과 JSON 파일 경로')
    
    args = parser.parse_args()
    
    # run_id 결정
    if args.run_id:
        run_id = args.run_id
    elif args.period:
        run_id = f"phase28_8_btc5m_baseline_v2_{args.period}"
    else:
        logger.error("--run-id 또는 --period 중 하나는 필수입니다")
        return 1
    
    # output 파일 경로
    if args.output:
        output_file = args.output
    elif args.period:
        output_file = f"reports/backtest/phase28_8/baseline_{args.period}.json"
    else:
        output_file = None
    
    # 분석 실행
    results = analyze_backtest_results(run_id, output_file)
    
    if results:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
