#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-4: Bayesian Search Round 1 결과 분석 및 요약
====================================================
Bayesian Round 1 실행 결과를 DB/JSON에서 수집하여 분석하고 리포트 생성

주요 기능:
1. DB에서 PHASE28-4 결과 조회
2. 전체 분포 통계 계산 (Sharpe, PnL, trades, win_rate)
3. Top-N trial 선정
4. Random Search Round 1 (PHASE28-3)과 비교
5. 파라미터 경향 분석
6. JSON 결과 저장
7. Markdown 리포트 텍스트 생성

Usage:
    python scripts/tuning/phase28_4_summarize_bayesian_round1.py
"""
import sys
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple
from collections import defaultdict

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


# ========================================
# DB 쿼리
# ========================================

def fetch_bayesian_results() -> List[Dict[str, Any]]:
    """
    DB에서 PHASE28-4 Bayesian Search 결과 조회
    
    Returns:
        List[Dict]: Trial 결과 리스트
    """
    logger.info("=" * 80)
    logger.info("📊 Fetching Bayesian Round 1 Results from DB")
    logger.info("=" * 80)
    
    results = []
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # PHASE28-4 run_id 패턴으로 필터링
            cur.execute("""
                SELECT 
                    r.run_id,
                    r.job_id,
                    r.total_trades,
                    r.pnl,
                    r.pnl_pct,
                    r.sharpe_like_ratio,
                    r.win_rate,
                    r.max_drawdown,
                    r.params_json,
                    r.created_at,
                    j.period
                FROM tuning.results r
                LEFT JOIN tuning.jobs j ON r.job_id = j.job_id
                WHERE r.run_id LIKE 'btc5m_bayesian_round1_%'
                  OR j.run_id LIKE 'btc5m_bayesian_round1_%'
                ORDER BY r.sharpe_like_ratio DESC NULLS LAST
            """)
            
            rows = cur.fetchall()
            for row in rows:
                results.append({
                    'run_id': row[0],
                    'job_id': row[1],
                    'trade_count': int(row[2]) if row[2] is not None else 0,
                    'pnl': float(row[3]) if row[3] is not None else 0.0,
                    'pnl_pct': float(row[4]) if row[4] is not None else 0.0,
                    'sharpe_ratio': float(row[5]) if row[5] is not None else 0.0,
                    'win_rate': float(row[6]) if row[6] is not None else 0.0,
                    'max_drawdown': float(row[7]) if row[7] is not None else 0.0,
                    'params': row[8] if row[8] else {},
                    'created_at': row[9].isoformat() if row[9] else None,
                    'period': row[10] if row[10] else 'unknown'
                })
    
    logger.info(f"✅ Fetched {len(results)} trials")
    logger.info("=" * 80)
    return results


# ========================================
# 통계 분석
# ========================================

def calculate_statistics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    전체 결과 통계 계산
    
    Args:
        results: Trial 결과 리스트
    
    Returns:
        Dict: 통계 요약
    """
    logger.info("=" * 80)
    logger.info("📈 Calculating Statistics")
    logger.info("=" * 80)
    
    if not results:
        logger.warning("⚠️ No results to analyze")
        return {}
    
    # 데이터 추출
    sharpes = [r['sharpe_ratio'] for r in results]
    pnls = [r['pnl'] for r in results]
    trades = [r['trade_count'] for r in results]
    win_rates = [r['win_rate'] for r in results]
    max_dds = [r['max_drawdown'] for r in results]
    
    # 필터링 (최소 거래 수 기준)
    min_trades = 5
    valid_results = [r for r in results if r['trade_count'] >= min_trades]
    positive_sharpe_results = [r for r in valid_results if r['sharpe_ratio'] > 0]
    
    stats = {
        'total_trials': len(results),
        'valid_trials': len(valid_results),
        'positive_sharpe_trials': len(positive_sharpe_results),
        'sharpe': {
            'min': float(np.min(sharpes)) if sharpes else 0.0,
            'max': float(np.max(sharpes)) if sharpes else 0.0,
            'mean': float(np.mean(sharpes)) if sharpes else 0.0,
            'median': float(np.median(sharpes)) if sharpes else 0.0,
            'std': float(np.std(sharpes)) if sharpes else 0.0
        },
        'pnl': {
            'min': float(np.min(pnls)) if pnls else 0.0,
            'max': float(np.max(pnls)) if pnls else 0.0,
            'mean': float(np.mean(pnls)) if pnls else 0.0,
            'median': float(np.median(pnls)) if pnls else 0.0
        },
        'trade_count': {
            'min': int(np.min(trades)) if trades else 0,
            'max': int(np.max(trades)) if trades else 0,
            'mean': float(np.mean(trades)) if trades else 0.0,
            'median': float(np.median(trades)) if trades else 0.0
        },
        'win_rate': {
            'min': float(np.min(win_rates)) if win_rates else 0.0,
            'max': float(np.max(win_rates)) if win_rates else 0.0,
            'mean': float(np.mean(win_rates)) if win_rates else 0.0
        },
        'max_drawdown': {
            'min': float(np.min(max_dds)) if max_dds else 0.0,
            'max': float(np.max(max_dds)) if max_dds else 0.0,
            'mean': float(np.mean(max_dds)) if max_dds else 0.0
        },
        'period_distribution': {}
    }
    
    # Period별 분포
    period_counts = defaultdict(int)
    for r in results:
        period_counts[r['period']] += 1
    stats['period_distribution'] = dict(period_counts)
    
    logger.info(f"✅ Total trials: {stats['total_trials']}")
    logger.info(f"✅ Valid trials (≥{min_trades} trades): {stats['valid_trials']}")
    logger.info(f"✅ Positive Sharpe trials: {stats['positive_sharpe_trials']}")
    logger.info(f"✅ Sharpe range: [{stats['sharpe']['min']:.4f}, {stats['sharpe']['max']:.4f}]")
    logger.info(f"✅ PnL range: [{stats['pnl']['min']:.2f}, {stats['pnl']['max']:.2f}]")
    logger.info("=" * 80)
    
    return stats


# ========================================
# Top-N 선정
# ========================================

def select_top_n(results: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
    """
    Top-N trial 선정 (Sharpe Ratio 기준)
    
    Args:
        results: Trial 결과 리스트
        top_n: 상위 N개
    
    Returns:
        List[Dict]: Top-N trials
    """
    logger.info("=" * 80)
    logger.info(f"🏆 Selecting Top-{top_n} Trials")
    logger.info("=" * 80)
    
    # 최소 거래 수 필터링
    min_trades = 5
    valid_results = [r for r in results if r['trade_count'] >= min_trades]
    
    # Sharpe Ratio 기준 정렬
    sorted_results = sorted(valid_results, key=lambda x: x['sharpe_ratio'], reverse=True)
    top_results = sorted_results[:top_n]
    
    for i, trial in enumerate(top_results, 1):
        logger.info(f"#{i} - Sharpe: {trial['sharpe_ratio']:.4f}, PnL: {trial['pnl']:.2f}, Trades: {trial['trade_count']}")
    
    logger.info("=" * 80)
    return top_results


# ========================================
# 파라미터 경향 분석
# ========================================

def analyze_parameter_trends(top_trials: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Top trials의 파라미터 경향 분석
    
    Args:
        top_trials: Top-N trials
    
    Returns:
        Dict: 파라미터 경향 요약
    """
    logger.info("=" * 80)
    logger.info("🔍 Analyzing Parameter Trends")
    logger.info("=" * 80)
    
    if not top_trials:
        logger.warning("⚠️ No top trials to analyze")
        return {}
    
    # 파라미터 수집
    param_collections = defaultdict(list)
    for trial in top_trials:
        params = trial.get('params', {})
        for key, value in params.items():
            if isinstance(value, (int, float)):
                param_collections[key].append(value)
    
    # 통계 계산
    trends = {}
    for key, values in param_collections.items():
        if values:
            trends[key] = {
                'min': float(np.min(values)),
                'max': float(np.max(values)),
                'mean': float(np.mean(values)),
                'median': float(np.median(values)),
                'std': float(np.std(values))
            }
            logger.info(f"  {key}: [{trends[key]['min']:.2f}, {trends[key]['max']:.2f}], mean={trends[key]['mean']:.2f}")
    
    logger.info("=" * 80)
    return trends


# ========================================
# Random Search 비교
# ========================================

def compare_with_random_search() -> Dict[str, Any]:
    """
    PHASE28-3 Random Search 결과와 비교
    
    Returns:
        Dict: 비교 결과
    """
    logger.info("=" * 80)
    logger.info("🔄 Comparing with Random Search Round 1 (PHASE28-3)")
    logger.info("=" * 80)
    
    random_results_path = Path("reports/tuning/phase28_3/results.json")
    if not random_results_path.exists():
        logger.warning("⚠️ Random Search results not found")
        return {}
    
    with open(random_results_path, 'r', encoding='utf-8') as f:
        random_data = json.load(f)
    
    random_results = random_data.get('results', [])
    
    # Random Search 최고 Sharpe
    random_sharpes = [r['sharpe_ratio'] for r in random_results if r.get('trade_count', 0) >= 5]
    random_best_sharpe = max(random_sharpes) if random_sharpes else 0.0
    
    comparison = {
        'random_total_trials': len(random_results),
        'random_best_sharpe': float(random_best_sharpe),
        'random_valid_trials': len([r for r in random_results if r.get('trade_count', 0) >= 5])
    }
    
    logger.info(f"Random Search: {comparison['random_total_trials']} trials, Best Sharpe: {comparison['random_best_sharpe']:.4f}")
    logger.info("=" * 80)
    
    return comparison


# ========================================
# JSON 저장
# ========================================

def save_results_json(
    results: List[Dict[str, Any]],
    stats: Dict[str, Any],
    top_trials: List[Dict[str, Any]],
    param_trends: Dict[str, Any],
    comparison: Dict[str, Any],
    output_path: str
):
    """
    결과를 JSON으로 저장
    
    Args:
        results: 전체 결과
        stats: 통계
        top_trials: Top-N trials
        param_trends: 파라미터 경향
        comparison: Random Search 비교
        output_path: 출력 경로
    """
    logger.info("=" * 80)
    logger.info("💾 Saving Results to JSON")
    logger.info("=" * 80)
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    output_data = {
        'phase': 'PHASE28-4',
        'round': 'Bayesian Search Round 1',
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_trials': len(results),
            'statistics': stats,
            'comparison': comparison
        },
        'top_trials': top_trials,
        'parameter_trends': param_trends,
        'all_results': results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ JSON saved: {output_file}")
    logger.info("=" * 80)


# ========================================
# Markdown 리포트 생성
# ========================================

def generate_markdown_report(
    stats: Dict[str, Any],
    top_trials: List[Dict[str, Any]],
    param_trends: Dict[str, Any],
    comparison: Dict[str, Any]
) -> str:
    """
    Markdown 리포트 텍스트 생성
    
    Args:
        stats: 통계
        top_trials: Top-N trials
        param_trends: 파라미터 경향
        comparison: Random Search 비교
    
    Returns:
        str: Markdown 텍스트
    """
    logger.info("=" * 80)
    logger.info("📝 Generating Markdown Report")
    logger.info("=" * 80)
    
    md = []
    md.append("# PHASE28-4: Bayesian Search Round 1 결과 리포트\n")
    md.append(f"**생성일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    md.append("---\n")
    
    # 요약
    md.append("## 📋 요약 (Executive Summary)\n")
    md.append(f"- **총 Trial 수**: {stats['total_trials']}개\n")
    md.append(f"- **유효 Trial** (거래 수 ≥5): {stats['valid_trials']}개\n")
    md.append(f"- **양의 Sharpe Trial**: {stats['positive_sharpe_trials']}개\n")
    md.append(f"- **Sharpe Ratio 범위**: [{stats['sharpe']['min']:.4f}, {stats['sharpe']['max']:.4f}]\n")
    md.append(f"- **PnL 범위**: [{stats['pnl']['min']:.2f}, {stats['pnl']['max']:.2f}]\n")
    md.append("\n")
    
    # Top-N
    md.append(f"## 🏆 Top-{len(top_trials)} Trials\n")
    md.append("| Rank | Sharpe | PnL | Trades | Win Rate | MaxDD | Period |\n")
    md.append("|------|--------|-----|--------|----------|-------|--------|\n")
    for i, trial in enumerate(top_trials, 1):
        md.append(f"| {i} | {trial['sharpe_ratio']:.4f} | {trial['pnl']:.2f} | {trial['trade_count']} | {trial['win_rate']:.2%} | {trial['max_drawdown']:.2f}% | {trial['period']} |\n")
    md.append("\n")
    
    # 파라미터 경향
    md.append("## 🔍 파라미터 경향 (Parameter Trends)\n")
    md.append("Top trials의 주요 파라미터 분포:\n\n")
    md.append("| Parameter | Min | Max | Mean | Median |\n")
    md.append("|-----------|-----|-----|------|--------|\n")
    for key, trend in param_trends.items():
        md.append(f"| {key} | {trend['min']:.2f} | {trend['max']:.2f} | {trend['mean']:.2f} | {trend['median']:.2f} |\n")
    md.append("\n")
    
    # Random Search 비교
    md.append("## 🔄 Random Search Round 1과 비교\n")
    md.append(f"- **Random Search**: {comparison.get('random_total_trials', 0)} trials, Best Sharpe: {comparison.get('random_best_sharpe', 0):.4f}\n")
    md.append(f"- **Bayesian Search**: {stats['total_trials']} trials, Best Sharpe: {stats['sharpe']['max']:.4f}\n")
    if comparison.get('random_best_sharpe', 0) > 0:
        improvement = (stats['sharpe']['max'] - comparison['random_best_sharpe']) / abs(comparison['random_best_sharpe']) * 100
        md.append(f"- **개선율**: {improvement:+.2f}%\n")
    md.append("\n")
    
    # 다음 단계
    md.append("## 🚀 다음 단계 제안\n")
    md.append("1. **Local Grid Search (PHASE28-5)**: Top-3 trial 주변 파라미터 정밀 탐색\n")
    md.append("2. **PAPER 검증**: Best trial 후보 2~3개에 대해 실시간 PAPER 모드 검증\n")
    md.append("3. **앙상블 준비**: 다양한 레짐/구간에서 안정적인 후보 조합 설계\n")
    md.append("\n")
    
    md_text = "".join(md)
    logger.info("✅ Markdown report generated")
    logger.info("=" * 80)
    
    return md_text


# ========================================
# Main
# ========================================

def main():
    logger.info("=" * 80)
    logger.info("🚀 PHASE28-4: Bayesian Round 1 Results Analysis")
    logger.info("=" * 80)
    
    # 1. DB에서 결과 조회
    results = fetch_bayesian_results()
    
    if not results:
        logger.error("❌ No results found. Exiting.")
        return
    
    # 2. 통계 분석
    stats = calculate_statistics(results)
    
    # 3. Top-N 선정
    top_trials = select_top_n(results, top_n=5)
    
    # 4. 파라미터 경향 분석
    param_trends = analyze_parameter_trends(top_trials)
    
    # 5. Random Search 비교
    comparison = compare_with_random_search()
    
    # 6. JSON 저장
    output_json_path = "reports/tuning/phase28_4/bayesian_round1_results.json"
    save_results_json(results, stats, top_trials, param_trends, comparison, output_json_path)
    
    # 7. Markdown 리포트 생성
    md_report = generate_markdown_report(stats, top_trials, param_trends, comparison)
    
    # Markdown 저장
    output_md_path = Path("docs/PHASE28/PHASE28-4_BAYESIAN_SEARCH_ROUND1_RESULTS.md")
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_md_path, 'w', encoding='utf-8') as f:
        f.write(md_report)
    
    logger.info(f"✅ Markdown saved: {output_md_path}")
    
    logger.info("=" * 80)
    logger.info("✅ PHASE28-4 Results Analysis Complete")
    logger.info("=" * 80)
    logger.info(f"📊 JSON: {output_json_path}")
    logger.info(f"📝 Markdown: {output_md_path}")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
