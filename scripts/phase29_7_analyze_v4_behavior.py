#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE29-7: V4 Strategy Behavior Pattern Analysis

V4 전략의 실패 원인을 정량적으로 분석하여
Postmortem 문서의 근거 데이터를 생성한다.
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.postgres import get_db_connection


def analyze_v4_behavior(trial_id: str) -> Dict[str, Any]:
    """V4 전략의 행동 패턴을 분석한다."""
    results = {
        "trial_id": trial_id,
        "analysis_date": datetime.now().isoformat(),
        "sections": {}
    }
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. 기본 통계
            cur.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    COUNT(CASE WHEN pnl > 0 THEN 1 END) as wins,
                    COUNT(CASE WHEN pnl < 0 THEN 1 END) as losses,
                    AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                    AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss,
                    MAX(CASE WHEN pnl > 0 THEN pnl END) as max_win,
                    MIN(CASE WHEN pnl < 0 THEN pnl END) as max_loss,
                    SUM(pnl) as total_pnl
                FROM trading.trades
                WHERE trial_id = %s AND status = 'CLOSED'
            """, (trial_id,))
            results["sections"]["basic_stats"] = dict(cur.fetchone())
            
            # 2. Side별 성능
            cur.execute("""
                SELECT side, COUNT(*) as count,
                       COUNT(CASE WHEN pnl > 0 THEN 1 END) as wins,
                       AVG(pnl) as avg_pnl, SUM(pnl) as total_pnl
                FROM trading.trades
                WHERE trial_id = %s AND status = 'CLOSED'
                GROUP BY side
            """, (trial_id,))
            results["sections"]["side_performance"] = [dict(r) for r in cur.fetchall()]
            
            # 3. 연속 손실
            cur.execute("""
                WITH ordered_trades AS (
                    SELECT pnl, ROW_NUMBER() OVER (ORDER BY ts_close) as rn
                    FROM trading.trades
                    WHERE trial_id = %s AND status = 'CLOSED'
                )
                SELECT pnl FROM ordered_trades ORDER BY rn
            """, (trial_id,))
            trade_sequence = [r['pnl'] for r in cur.fetchall()]
            
            consecutive_losses = []
            current_streak = 0
            for pnl in trade_sequence:
                if pnl < 0:
                    current_streak += 1
                else:
                    if current_streak > 0:
                        consecutive_losses.append(current_streak)
                    current_streak = 0
            if current_streak > 0:
                consecutive_losses.append(current_streak)
            
            results["sections"]["consecutive_losses"] = {
                "max_streak": max(consecutive_losses) if consecutive_losses else 0,
                "avg_streak": sum(consecutive_losses) / len(consecutive_losses) if consecutive_losses else 0,
                "count_streaks": len(consecutive_losses)
            }
            
            # 4. 청산 패턴
            cur.execute("""
                SELECT exit_reason, COUNT(*) as count,
                       COUNT(CASE WHEN pnl > 0 THEN 1 END) as wins,
                       AVG(pnl) as avg_pnl
                FROM trading.trades
                WHERE trial_id = %s AND status = 'CLOSED' AND exit_reason IS NOT NULL
                GROUP BY exit_reason ORDER BY count DESC
            """, (trial_id,))
            results["sections"]["exit_patterns"] = [dict(r) for r in cur.fetchall()]
            
            # 5. Holding Time
            cur.execute("""
                SELECT EXTRACT(EPOCH FROM (ts_close - ts_open)) / 60 as hold_minutes, pnl
                FROM trading.trades
                WHERE trial_id = %s AND status = 'CLOSED' 
                      AND ts_open IS NOT NULL AND ts_close IS NOT NULL
            """, (trial_id,))
            hold_times = cur.fetchall()
            
            win_holds = [r['hold_minutes'] for r in hold_times if r['pnl'] > 0]
            loss_holds = [r['hold_minutes'] for r in hold_times if r['pnl'] < 0]
            
            results["sections"]["holding_time"] = {
                "avg_hold_all": sum(r['hold_minutes'] for r in hold_times) / len(hold_times) if hold_times else 0,
                "avg_hold_win": sum(win_holds) / len(win_holds) if win_holds else 0,
                "avg_hold_loss": sum(loss_holds) / len(loss_holds) if loss_holds else 0
            }
    
    return results


def generate_markdown_report(analysis: Dict[str, Any], output_path: str):
    """분석 결과를 Markdown 형식으로 출력한다."""
    bs = analysis['sections']['basic_stats']
    total = bs['total_trades']
    wins = bs['wins']
    losses = bs['losses']
    win_rate = (wins / total * 100) if total > 0 else 0
    
    lines = [
        "# PHASE29-7: V4 Strategy Behavior Analysis",
        "",
        f"**Trial ID**: {analysis['trial_id']}  ",
        f"**분석일**: {analysis['analysis_date']}",
        "",
        "## 1. 기본 통계",
        "",
        f"- 총 거래: {total}건",
        f"- Win Rate: **{win_rate:.1f}%** (목표: >=45%)",
        f"- 손실 비율: {losses/total*100:.1f}%",
        f"- 평균 승리: ${bs['avg_win']:.2f}" if bs['avg_win'] else "- 평균 승리: N/A",
        f"- 평균 손실: ${bs['avg_loss']:.2f}" if bs['avg_loss'] else "- 평균 손실: N/A",
        f"- 총 PnL: ${bs['total_pnl']:.2f}",
        "",
        "## 2. Side별 성능",
        ""
    ]
    
    for side_stat in analysis['sections']['side_performance']:
        side_wr = (side_stat['wins'] / side_stat['count'] * 100) if side_stat['count'] > 0 else 0
        lines.extend([
            f"**{side_stat['side']}**: {side_stat['count']}건, Win Rate {side_wr:.1f}%, PnL ${side_stat['total_pnl']:.2f}",
            ""
        ])
    
    cl = analysis['sections']['consecutive_losses']
    lines.extend([
        "## 3. 연속 손실",
        "",
        f"- 최대 연속 손실: **{cl['max_streak']}건**",
        f"- 평균 연속 손실: {cl['avg_streak']:.1f}건",
        f"- 발생 횟수: {cl['count_streaks']}회",
        "",
        "## 4. 청산 패턴",
        ""
    ])
    
    for exit_stat in analysis['sections']['exit_patterns']:
        exit_wr = (exit_stat['wins'] / exit_stat['count'] * 100) if exit_stat['count'] > 0 else 0
        lines.append(f"- **{exit_stat.get('exit_reason', 'Unknown')}**: {exit_stat['count']}건 (Win Rate {exit_wr:.1f}%)")
    
    ht = analysis['sections']['holding_time']
    lines.extend([
        "",
        "## 5. Holding Time",
        "",
        f"- 전체 평균: {ht['avg_hold_all']:.1f}분",
        f"- 승리 평균: {ht['avg_hold_win']:.1f}분",
        f"- 손실 평균: {ht['avg_hold_loss']:.1f}분",
        "",
        "## 핵심 문제점",
        "",
        f"1. **Win Rate 부족**: {win_rate:.1f}% (목표 45% 대비 {45-win_rate:.1f}%p 부족)",
        f"2. **손실 비율 과다**: {losses/total*100:.1f}%",
        f"3. **연속 손실 빈도**: {cl['count_streaks']}회 발생, 최대 {cl['max_streak']}건",
        "",
        "## 구조적 실패 원인",
        "",
        "- OR 기반 진입 조건이 저품질 신호 과다 생성",
        "- Score Threshold 낮음 (낮은 점수 신호도 진입)",
        "- SL/TP 비율이 시장 움직임과 미스매치",
        "- 5m 타임프레임의 과도한 노이즈",
        ""
    ])
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ Markdown 리포트: {output_path}")


def main():
    trial_id = "phase29_4_0_btc5m_baseline_v4_month_gate"
    print(f"🔍 V4 전략 행동 패턴 분석: {trial_id}")
    
    analysis = analyze_v4_behavior(trial_id)
    
    # JSON 저장
    json_path = "reports/analysis/PHASE29/phase29_7_v4_behavior_analysis.json"
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON 리포트: {json_path}")
    
    # Markdown 저장
    md_path = "reports/analysis/PHASE29/phase29_7_v4_behavior_analysis.md"
    generate_markdown_report(analysis, md_path)
    
    # 요약
    bs = analysis['sections']['basic_stats']
    print("\n" + "="*60)
    print("V4 전략 행동 분석 요약")
    print("="*60)
    print(f"총 거래: {bs['total_trades']}건")
    print(f"Win Rate: {bs['wins']/bs['total_trades']*100:.1f}%")
    print(f"최대 연속 손실: {analysis['sections']['consecutive_losses']['max_streak']}건")
    print(f"총 PnL: ${bs['total_pnl']:.2f}")
    print("="*60)


if __name__ == "__main__":
    main()
