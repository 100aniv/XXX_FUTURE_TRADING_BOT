#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE30-1: AC3 성능 분석 스크립트
==================================

btc15m_core_v1 3M Baseline 백테스트 결과에 대한 AC3 성능 평가

Acceptance Criteria AC3:
- Win Rate: 40~45% (목표)
- Max DD: ≤ 12%
- Profit Factor: > 1.2
- Trades: 60~120건/월 (3M 기준 180~360건)
"""
import json
import psycopg2
from pathlib import Path
from datetime import datetime

def analyze_ac3_performance(trial_id: str, summary_json_path: str):
    """
    AC3 성능 분석
    
    Args:
        trial_id: 백테스트 trial_id
        summary_json_path: Summary JSON 경로
    """
    print("=" * 80)
    print("PHASE30-1: AC3 성능 분석")
    print("=" * 80)
    print(f"Trial ID: {trial_id}")
    print(f"Summary JSON: {summary_json_path}\n")
    
    # Summary JSON 로드
    with open(summary_json_path, 'r', encoding='utf-8') as f:
        summary = json.load(f)
    
    print("=== Summary JSON 메트릭 ===")
    print(f"Total Trades: {summary.get('total_trades', 0)}")
    print(f"Win Rate: {summary.get('win_rate_pct', 0):.2f}%")
    print(f"Max Drawdown: {summary.get('max_drawdown_pct', 0):.2f}%")
    print(f"Profit Factor: {summary.get('profit_factor', 0):.2f}")
    print(f"PnL Total: ${summary.get('pnl_total', 0):,.2f}")
    print(f"PnL Net: ${summary.get('pnl_net', 0):,.2f}")
    print(f"Sharpe Ratio: {summary.get('sharpe_ratio', 0):.2f}\n")
    
    # DB에서 상세 trades 쿼리
    print("=== DB Trades 상세 분석 ===")
    # trading_db_postgres: localhost:5433, DB=trading_db
    conn = psycopg2.connect('postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db')
    cur = conn.cursor()
    
    # 1) 전체 거래 수
    cur.execute("""
        SELECT COUNT(*), 
               SUM(CASE WHEN pnl_net > 0 THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN pnl_net <= 0 THEN 1 ELSE 0 END) as losses
        FROM trading.trades
        WHERE trial_id = %s
    """, (trial_id,))
    
    total, wins, losses = cur.fetchone()
    win_rate = (wins / total * 100) if total > 0 else 0
    
    print(f"Total Trades: {total}")
    print(f"Wins: {wins}, Losses: {losses}")
    print(f"Win Rate: {win_rate:.2f}%\n")
    
    # 2) PnL 합계
    cur.execute("""
        SELECT SUM(pnl_net), AVG(pnl_net),
               SUM(CASE WHEN pnl_net > 0 THEN pnl_net ELSE 0 END) as total_win_pnl,
               SUM(CASE WHEN pnl_net < 0 THEN ABS(pnl_net) ELSE 0 END) as total_loss_pnl
        FROM trading.trades
        WHERE trial_id = %s
    """, (trial_id,))
    
    total_pnl, avg_pnl, total_win, total_loss = cur.fetchone()
    profit_factor = (total_win / total_loss) if total_loss and total_loss > 0 else 0
    
    print(f"Total PnL: ${total_pnl:,.2f}")
    print(f"Avg PnL: ${avg_pnl:,.2f}")
    print(f"Total Win PnL: ${total_win:,.2f}")
    print(f"Total Loss PnL: ${total_loss:,.2f}")
    print(f"Profit Factor: {profit_factor:.2f}\n")
    
    # 3) Side별 분포
    cur.execute("""
        SELECT side, COUNT(*),
               SUM(CASE WHEN pnl_net > 0 THEN 1 ELSE 0 END) as wins
        FROM trading.trades
        WHERE trial_id = %s
        GROUP BY side
    """, (trial_id,))
    
    print("Side별 분포:")
    for side, count, side_wins in cur.fetchall():
        side_wr = (side_wins / count * 100) if count > 0 else 0
        print(f"  {side}: {count}건, Win Rate {side_wr:.1f}%")
    print()
    
    # 4) Max Consecutive Losses
    cur.execute("""
        WITH trade_seq AS (
            SELECT entry_time, pnl_net,
                   CASE WHEN pnl_net <= 0 THEN 1 ELSE 0 END as is_loss
            FROM trading.trades
            WHERE trial_id = %s
            ORDER BY entry_time
        ),
        loss_groups AS (
            SELECT entry_time, is_loss,
                   SUM(CASE WHEN is_loss = 0 THEN 1 ELSE 0 END) 
                       OVER (ORDER BY entry_time) as group_id
            FROM trade_seq
        )
        SELECT MAX(loss_count) as max_consecutive_losses
        FROM (
            SELECT group_id, SUM(is_loss) as loss_count
            FROM loss_groups
            WHERE is_loss = 1
            GROUP BY group_id
        ) sub
    """, (trial_id,))
    
    max_cons_loss = cur.fetchone()[0] or 0
    print(f"Max Consecutive Losses: {max_cons_loss}건\n")
    
    conn.close()
    
    # AC3 판정
    print("=" * 80)
    print("AC3 성능 기준 판정")
    print("=" * 80)
    
    ac3_results = {}
    
    # Win Rate
    target_wr_min = 40.0
    target_wr_max = 45.0
    if target_wr_min <= win_rate <= target_wr_max:
        wr_pass = "✅ PASS"
        ac3_results['win_rate'] = 'PASS'
    elif win_rate >= target_wr_min:
        wr_pass = "⚠️ CONDITIONAL PASS (목표 범위 초과)"
        ac3_results['win_rate'] = 'CONDITIONAL'
    else:
        wr_pass = "❌ FAIL"
        ac3_results['win_rate'] = 'FAIL'
    
    print(f"Win Rate: {win_rate:.2f}% (목표: {target_wr_min}~{target_wr_max}%) → {wr_pass}")
    
    # Max DD
    max_dd = summary.get('max_drawdown_pct', 0)
    target_max_dd = 12.0
    if max_dd <= target_max_dd:
        dd_pass = "✅ PASS"
        ac3_results['max_dd'] = 'PASS'
    else:
        dd_pass = "❌ FAIL"
        ac3_results['max_dd'] = 'FAIL'
    
    print(f"Max Drawdown: {max_dd:.2f}% (목표: ≤ {target_max_dd}%) → {dd_pass}")
    
    # Profit Factor
    target_pf = 1.2
    if profit_factor > target_pf:
        pf_pass = "✅ PASS"
        ac3_results['profit_factor'] = 'PASS'
    else:
        pf_pass = "❌ FAIL"
        ac3_results['profit_factor'] = 'FAIL'
    
    print(f"Profit Factor: {profit_factor:.2f} (목표: > {target_pf}) → {pf_pass}")
    
    # Trades (월 평균)
    trades_per_month = total / 3.0  # 3개월 기준
    target_trades_min = 60
    target_trades_max = 120
    if target_trades_min <= trades_per_month <= target_trades_max:
        trades_pass = "✅ PASS"
        ac3_results['trades'] = 'PASS'
    elif trades_per_month < target_trades_min:
        trades_pass = "⚠️ 거래 부족"
        ac3_results['trades'] = 'LOW'
    else:
        trades_pass = "⚠️ 거래 과다"
        ac3_results['trades'] = 'HIGH'
    
    print(f"Trades/Month: {trades_per_month:.1f}건 (목표: {target_trades_min}~{target_trades_max}건/월) → {trades_pass}")
    
    # 최종 판정
    print("\n" + "=" * 80)
    pass_count = sum(1 for v in ac3_results.values() if v == 'PASS')
    fail_count = sum(1 for v in ac3_results.values() if v == 'FAIL')
    
    if pass_count == 4:
        final_verdict = "✅ AC3 PASS (모든 기준 충족)"
    elif fail_count == 0:
        final_verdict = "⚠️ AC3 CONDITIONAL PASS (일부 기준 조건부 충족)"
    else:
        final_verdict = "❌ AC3 FAIL (핵심 기준 미달)"
    
    print(f"최종 판정: {final_verdict}")
    print(f"  PASS: {pass_count}/4, FAIL: {fail_count}/4")
    print("=" * 80)
    
    # JSON 저장
    output = {
        'trial_id': trial_id,
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_trades': total,
            'wins': wins,
            'losses': losses,
            'win_rate_pct': round(win_rate, 2),
            'max_drawdown_pct': round(max_dd, 2),
            'profit_factor': round(profit_factor, 2),
            'pnl_total': round(total_pnl, 2) if total_pnl else 0,
            'trades_per_month': round(trades_per_month, 1),
            'max_consecutive_losses': max_cons_loss
        },
        'ac3_criteria': {
            'win_rate': {'result': ac3_results['win_rate'], 'value': round(win_rate, 2), 'target': f"{target_wr_min}~{target_wr_max}%"},
            'max_dd': {'result': ac3_results['max_dd'], 'value': round(max_dd, 2), 'target': f"≤{target_max_dd}%"},
            'profit_factor': {'result': ac3_results['profit_factor'], 'value': round(profit_factor, 2), 'target': f">{target_pf}"},
            'trades': {'result': ac3_results['trades'], 'value': round(trades_per_month, 1), 'target': f"{target_trades_min}~{target_trades_max}/월"}
        },
        'final_verdict': final_verdict,
        'pass_count': pass_count,
        'fail_count': fail_count
    }
    
    output_path = Path('reports/analysis/PHASE30/phase30_1_ac3_performance.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ AC3 분석 완료: {output_path}")
    
    return output


if __name__ == '__main__':
    trial_id = 'phase30_1_btc15m_core_v1_3m_baseline'
    summary_json = 'reports/backtest/phase30_1/btc15m_core_v1_3m_baseline_summary.json'
    
    result = analyze_ac3_performance(trial_id, summary_json)
    
    print(f"\n다음 단계: PHASE30_1_3M_BASELINE_RESULT_KR.md 작성")
