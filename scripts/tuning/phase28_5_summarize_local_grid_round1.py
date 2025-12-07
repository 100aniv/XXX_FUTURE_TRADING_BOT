#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-5: Local Grid Search Round 1 Results Summarizer
========================================================
PHASE28-5 결과 집계 및 리포트 생성 (JSON + Markdown)

Usage:
    python scripts/tuning/phase28_5_summarize_local_grid_round1.py
"""
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


def fetch_results(run_id_pattern: str = 'phase28_5_%', min_trades: int = 5) -> Dict[str, Any]:
    """
    DB에서 PHASE28-5 결과 조회
    
    Args:
        run_id_pattern: Run ID 패턴
        min_trades: 최소 거래 수 (필터링)
    
    Returns:
        Results 딕셔너리
    """
    logger.info("=" * 80)
    logger.info("📊 Fetching PHASE28-5 Results")
    logger.info("=" * 80)
    
    # 1. 전체 통계
    sql_stats = """
    SELECT
        COUNT(*) as total_trials,
        COUNT(CASE WHEN r.trade_count >= %s THEN 1 END) as valid_trials,
        MIN(r.sharpe_ratio) as min_sharpe,
        MAX(r.sharpe_ratio) as max_sharpe,
        AVG(r.sharpe_ratio) as avg_sharpe,
        MIN(r.pnl) as min_pnl,
        MAX(r.pnl) as max_pnl,
        AVG(r.pnl) as avg_pnl,
        AVG(r.trade_count) as avg_trades,
        AVG(r.win_rate) as avg_win_rate
    FROM tuning.results r
    JOIN tuning.jobs j ON r.job_id = j.job_id
    WHERE j.run_id LIKE %s
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_stats, (min_trades, run_id_pattern))
            stats_row = cur.fetchone()
    
    if not stats_row or stats_row[0] == 0:
        logger.warning("⚠️  No results found")
        return {'total_trials': 0, 'valid_trials': 0}
    
    stats = {
        'total_trials': stats_row[0],
        'valid_trials': stats_row[1],
        'min_sharpe': float(stats_row[2]) if stats_row[2] else 0.0,
        'max_sharpe': float(stats_row[3]) if stats_row[3] else 0.0,
        'avg_sharpe': float(stats_row[4]) if stats_row[4] else 0.0,
        'min_pnl': float(stats_row[5]) if stats_row[5] else 0.0,
        'max_pnl': float(stats_row[6]) if stats_row[6] else 0.0,
        'avg_pnl': float(stats_row[7]) if stats_row[7] else 0.0,
        'avg_trades': float(stats_row[8]) if stats_row[8] else 0.0,
        'avg_win_rate': float(stats_row[9]) if stats_row[9] else 0.0
    }
    
    logger.info(f"Total Trials: {stats['total_trials']}")
    logger.info(f"Valid Trials (trades ≥ {min_trades}): {stats['valid_trials']}")
    
    # 2. Top-N trials
    sql_top = """
    SELECT
        j.job_id,
        j.run_id,
        j.params_json,
        r.sharpe_ratio,
        r.pnl,
        r.pnl_pct,
        r.trade_count,
        r.win_count,
        r.lose_count,
        r.win_rate,
        r.max_drawdown,
        r.profit_factor,
        r.avg_win,
        r.avg_lose,
        r.runtime_sec
    FROM tuning.results r
    JOIN tuning.jobs j ON r.job_id = j.job_id
    WHERE j.run_id LIKE %s
      AND r.trade_count >= %s
    ORDER BY r.sharpe_ratio DESC
    LIMIT 10
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_top, (run_id_pattern, min_trades))
            top_rows = cur.fetchall()
    
    top_trials = []
    for row in top_rows:
        top_trials.append({
            'job_id': row[0],
            'run_id': row[1],
            'params': row[2],
            'sharpe_ratio': float(row[3]),
            'pnl': float(row[4]),
            'pnl_pct': float(row[5]),
            'trade_count': row[6],
            'win_count': row[7],
            'lose_count': row[8],
            'win_rate': float(row[9]),
            'max_drawdown': float(row[10]),
            'profit_factor': float(row[11]),
            'avg_win': float(row[12]),
            'avg_lose': float(row[13]),
            'runtime_sec': float(row[14])
        })
    
    logger.info(f"Top-10 Trials retrieved: {len(top_trials)}")
    
    return {
        'stats': stats,
        'top_trials': top_trials,
        'timestamp': datetime.now().isoformat(),
        'min_trades_filter': min_trades
    }


def save_json_report(results: Dict[str, Any], output_path: str):
    """JSON 리포트 저장"""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ JSON report saved: {output_path}")


def save_markdown_report(results: Dict[str, Any], output_path: str):
    """Markdown 리포트 생성"""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    stats = results['stats']
    top_trials = results['top_trials']
    timestamp = results['timestamp']
    min_trades = results['min_trades_filter']
    
    md = []
    md.append("# PHASE28-5: Local Grid Search Round 1 결과 리포트")
    md.append(f"**생성일**: {timestamp}  ")
    md.append(f"**상태**: 🟢 **COMPLETE**")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 📋 Executive Summary")
    md.append("")
    md.append(f"- **총 Trial 수**: {stats['total_trials']}개")
    md.append(f"- **유효 Trial** (거래 수 ≥{min_trades}): {stats['valid_trials']}개")
    md.append(f"- **Sharpe Ratio 범위**: [{stats['min_sharpe']:.4f}, {stats['max_sharpe']:.4f}]")
    md.append(f"- **평균 Sharpe Ratio**: {stats['avg_sharpe']:.4f}")
    md.append(f"- **PnL 범위**: [{stats['min_pnl']:.2f}, {stats['max_pnl']:.2f}]")
    md.append(f"- **평균 PnL**: {stats['avg_pnl']:.2f}")
    md.append(f"- **평균 거래 수**: {stats['avg_trades']:.1f}")
    md.append(f"- **평균 승률**: {stats['avg_win_rate']:.2%}")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 🏆 Top-10 Trials")
    md.append("")
    md.append("| Rank | Job ID | Sharpe | PnL | Trades | Win Rate | MaxDD | Profit Factor |")
    md.append("|------|--------|--------|-----|--------|----------|-------|---------------|")
    
    for idx, trial in enumerate(top_trials, 1):
        job_id_short = trial['job_id'][:12]
        sharpe = trial['sharpe_ratio']
        pnl = trial['pnl']
        trades = trial['trade_count']
        win_rate = trial['win_rate']
        max_dd = trial['max_drawdown']
        pf = trial['profit_factor']
        
        md.append(f"| {idx} | {job_id_short}... | {sharpe:.4f} | {pnl:.2f} | {trades} | {win_rate:.2%} | {max_dd:.2f} | {pf:.4f} |")
    
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 🔍 Top-3 Trials 파라미터")
    md.append("")
    
    for idx, trial in enumerate(top_trials[:3], 1):
        md.append(f"### Trial {idx}: Sharpe {trial['sharpe_ratio']:.4f}")
        md.append("")
        md.append("```json")
        md.append(json.dumps(trial['params'], indent=2))
        md.append("```")
        md.append("")
        md.append(f"- **PnL**: {trial['pnl']:.2f} ({trial['pnl_pct']:.2%})")
        md.append(f"- **Trades**: {trial['trade_count']} (Win: {trial['win_count']}, Lose: {trial['lose_count']})")
        md.append(f"- **Win Rate**: {trial['win_rate']:.2%}")
        md.append(f"- **Avg Win**: {trial['avg_win']:.2f}, **Avg Lose**: {trial['avg_lose']:.2f}")
        md.append(f"- **Max Drawdown**: {trial['max_drawdown']:.2f}")
        md.append(f"- **Profit Factor**: {trial['profit_factor']:.4f}")
        md.append("")
    
    md.append("---")
    md.append("")
    md.append("## 📊 Comparison with Bayesian Round 1")
    md.append("")
    md.append("### PHASE28-4 Bayesian Round 1 (Reference)")
    md.append("- **Best Sharpe**: -19.4773")
    md.append("- **Best PnL**: -202.84")
    md.append("- **Valid Trials**: 4 (거래 수 ≥5)")
    md.append("")
    md.append("### PHASE28-5 Local Grid Search Round 1")
    md.append(f"- **Best Sharpe**: {stats['max_sharpe']:.4f}")
    md.append(f"- **Best PnL**: {stats['max_pnl']:.2f}")
    md.append(f"- **Valid Trials**: {stats['valid_trials']}")
    md.append("")
    
    # 개선 여부 판정
    bayesian_best_sharpe = -19.4773
    local_grid_best_sharpe = stats['max_sharpe']
    
    if local_grid_best_sharpe > bayesian_best_sharpe:
        improvement_pct = ((local_grid_best_sharpe - bayesian_best_sharpe) / abs(bayesian_best_sharpe)) * 100
        md.append(f"### ✅ 개선 확인")
        md.append(f"- Local Grid Search가 Bayesian보다 **{improvement_pct:.1f}% 개선**")
    else:
        md.append(f"### ⚠️ 개선 미확인")
        md.append(f"- Local Grid Search가 Bayesian과 유사하거나 낮음")
        md.append(f"- 추가 전략 개선 필요")
    
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 💡 Conclusion")
    md.append("")
    md.append("**PHASE28-5 Local Grid Search Round 1 완료**")
    md.append("")
    
    if stats['valid_trials'] > 0 and stats['max_sharpe'] > bayesian_best_sharpe:
        md.append("- ✅ **성공**: Local Grid Search로 Bayesian보다 나은 파라미터 발견")
        md.append("- **다음 단계**: 상위 파라미터를 Paper Trading으로 검증 (PHASE29)")
    elif stats['valid_trials'] > 0:
        md.append("- ⚠️ **제한적 성공**: Valid trials 존재하나 Bayesian 대비 개선 미미")
        md.append("- **다음 단계**: 전략 로직 개선 또는 다른 파라미터 탐색 (PHASE28-6)")
    else:
        md.append("- ❌ **실패**: 유효한 trial 없음")
        md.append("- **다음 단계**: 전략 재설계 또는 다른 시장 구간 테스트")
    
    md.append("")
    md.append("---")
    md.append("")
    md.append(f"**Report Generated**: {timestamp}  ")
    md.append(f"**Phase**: PHASE28-5  ")
    md.append(f"**Author**: Automated Report Generator")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))
    
    logger.info(f"✅ Markdown report saved: {output_path}")


def main():
    """Main execution"""
    logger.info("=" * 80)
    logger.info("📊 PHASE28-5: Local Grid Search Round 1 Summarizer")
    logger.info("=" * 80)
    
    # 결과 조회
    results = fetch_results(
        run_id_pattern='phase28_5_%',
        min_trades=5
    )
    
    if results['stats']['total_trials'] == 0:
        logger.warning("⚠️  No results to summarize")
        return
    
    # JSON 리포트 저장
    json_path = "reports/tuning/phase28_5/local_grid_round1_results.json"
    save_json_report(results, json_path)
    
    # Markdown 리포트 저장
    md_path = "docs/PHASE28/PHASE28-5_LOCAL_GRID_SEARCH_ROUND1_RESULTS.md"
    save_markdown_report(results, md_path)
    
    logger.info("=" * 80)
    logger.info("✅ Summarization Complete")
    logger.info("=" * 80)
    logger.info(f"  JSON Report: {json_path}")
    logger.info(f"  Markdown Report: {md_path}")
    logger.info("=" * 80)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
