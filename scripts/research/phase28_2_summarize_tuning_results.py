#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-2: Tuning Results Summarizer
=====================================
btc5m_baseline_v1 튜닝 결과 집계 및 리포트 생성

주요 기능:
- tuning.runs/results에서 PHASE28-2 데이터 조회
- 각 period별 + 전체 통합 Top N 파라미터 세트 선정
- Markdown + JSON 리포트 생성

사용법:
    python scripts/research/phase28_2_summarize_tuning_results.py
    python scripts/research/phase28_2_summarize_tuning_results.py --top-n 10
"""
import argparse
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


def query_tuning_results(phase: str = "PHASE28-2", strategy_name: str = "btc5m_baseline_v1") -> Dict[str, List[Dict[str, Any]]]:
    """
    DB에서 튜닝 결과 조회
    
    Args:
        phase: PHASE 번호
        strategy_name: 전략 이름
    
    Returns:
        Dict[period_name, List[result_dict]]: period별 결과 리스트
    """
    sql = """
    SELECT 
        r.run_id,
        rn.phase,
        rn.strategy_name,
        rn.tuning_method,
        rn.metadata,
        r.result_id,
        r.job_id,
        j.job_index,
        j.params_json,
        r.pnl,
        r.pnl_pct,
        r.trade_count,
        r.win_count,
        r.lose_count,
        r.win_rate,
        r.sharpe_ratio,
        r.max_drawdown,
        r.profit_factor,
        r.avg_win,
        r.avg_lose,
        r.runtime_sec,
        r.created_at
    FROM tuning.results r
    JOIN tuning.jobs j ON r.job_id = j.job_id
    JOIN tuning.runs rn ON r.run_id = rn.run_id
    WHERE rn.phase = %s
      AND rn.strategy_name = %s
    ORDER BY r.created_at ASC
    """
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (phase, strategy_name))
                rows = cur.fetchall()
                
                logger.info(f"✅ 튜닝 결과 조회: {len(rows)}건")
                
                # Period별로 그룹화
                results_by_period = {}
                
                for row in rows:
                    metadata = row[4] or {}
                    period_name = metadata.get('period_name', 'unknown')
                    
                    result_dict = {
                        'run_id': row[0],
                        'phase': row[1],
                        'strategy_name': row[2],
                        'tuning_method': row[3],
                        'period_name': period_name,
                        'period_weight': metadata.get('period_weight', 1.0),
                        'result_id': row[5],
                        'job_id': row[6],
                        'job_index': row[7],
                        'params': row[8] or {},
                        'pnl': float(row[9]) if row[9] is not None else 0.0,
                        'pnl_pct': float(row[10]) if row[10] is not None else 0.0,
                        'trade_count': int(row[11]) if row[11] is not None else 0,
                        'win_count': int(row[12]) if row[12] is not None else 0,
                        'lose_count': int(row[13]) if row[13] is not None else 0,
                        'win_rate': float(row[14]) if row[14] is not None else 0.0,
                        'sharpe_ratio': float(row[15]) if row[15] is not None else 0.0,
                        'max_drawdown': float(row[16]) if row[16] is not None else 0.0,
                        'profit_factor': float(row[17]) if row[17] is not None else 0.0,
                        'avg_win': float(row[18]) if row[18] is not None else 0.0,
                        'avg_lose': float(row[19]) if row[19] is not None else 0.0,
                        'runtime_sec': float(row[20]) if row[20] is not None else 0.0,
                        'created_at': row[21]
                    }
                    
                    if period_name not in results_by_period:
                        results_by_period[period_name] = []
                    
                    results_by_period[period_name].append(result_dict)
                
                return results_by_period
                
    except Exception as e:
        logger.error(f"❌ 튜닝 결과 조회 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}


def filter_valid_results(results: List[Dict[str, Any]], min_trades: int = 10, max_drawdown: float = 20.0) -> List[Dict[str, Any]]:
    """
    유효한 결과만 필터링
    
    Args:
        results: 결과 리스트
        min_trades: 최소 거래 수
        max_drawdown: 최대 낙폭 (%)
    
    Returns:
        List[Dict]: 필터링된 결과
    """
    valid = [
        r for r in results
        if r['trade_count'] >= min_trades
        and r['max_drawdown'] <= max_drawdown
    ]
    
    logger.info(f"   - 필터링: {len(results)}건 → {len(valid)}건 (min_trades={min_trades}, max_dd≤{max_drawdown}%)")
    
    return valid


def select_top_n(results: List[Dict[str, Any]], metric: str = 'sharpe_ratio', n: int = 10) -> List[Dict[str, Any]]:
    """
    Top N 파라미터 세트 선정
    
    Args:
        results: 결과 리스트
        metric: 정렬 기준 메트릭
        n: 상위 N개
    
    Returns:
        List[Dict]: Top N 결과
    """
    sorted_results = sorted(results, key=lambda x: x.get(metric, 0), reverse=True)
    return sorted_results[:n]


def generate_markdown_report(
    results_by_period: Dict[str, List[Dict[str, Any]]],
    top_n: int = 10,
    output_path: str = "docs/PHASE28/PHASE28-2_TUNING_ROUND1_REPORT.md"
) -> str:
    """
    Markdown 리포트 생성
    
    Args:
        results_by_period: Period별 결과
        top_n: 상위 N개
        output_path: 출력 경로
    
    Returns:
        str: 생성된 파일 경로
    """
    report_lines = []
    
    # ========================================
    # 리포트 헤더
    # ========================================
    report_lines.append("# PHASE28-2 TUNING ROUND 1 REPORT")
    report_lines.append("")
    report_lines.append(f"**일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**전략**: btc5m_baseline_v1")
    report_lines.append(f"**튜닝 방법**: Random Search")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    
    # ========================================
    # Period별 Top N
    # ========================================
    report_lines.append("## Period별 Top N 파라미터 세트")
    report_lines.append("")
    
    all_results = []
    
    for period_name, results in results_by_period.items():
        report_lines.append(f"### {period_name.upper()} Period")
        report_lines.append("")
        
        # 필터링
        valid_results = filter_valid_results(results, min_trades=10, max_drawdown=20.0)
        
        if not valid_results:
            report_lines.append("⚠️ 유효한 결과 없음 (min_trades < 10 또는 max_dd > 20%)")
            report_lines.append("")
            continue
        
        # Top N 선정
        top_results = select_top_n(valid_results, metric='sharpe_ratio', n=top_n)
        
        # 테이블 생성
        report_lines.append("| Rank | Sharpe | PnL (%) | Trades | Win Rate | Max DD | Params |")
        report_lines.append("|------|--------|---------|--------|----------|--------|--------|")
        
        for rank, result in enumerate(top_results, 1):
            params_str = ", ".join([f"{k}={v}" for k, v in list(result['params'].items())[:3]])
            if len(result['params']) > 3:
                params_str += ", ..."
            
            report_lines.append(
                f"| {rank} | {result['sharpe_ratio']:.4f} | {result['pnl_pct']:.2f} | "
                f"{result['trade_count']} | {result['win_rate']:.2%} | "
                f"{result['max_drawdown']:.2f}% | {params_str} |"
            )
        
        report_lines.append("")
        
        # 전체 집계용으로 추가
        all_results.extend(valid_results)
    
    # ========================================
    # 전체 통합 Top N
    # ========================================
    report_lines.append("## 전체 통합 Top N 파라미터 세트")
    report_lines.append("")
    
    if all_results:
        top_overall = select_top_n(all_results, metric='sharpe_ratio', n=top_n)
        
        report_lines.append("| Rank | Period | Sharpe | PnL (%) | Trades | Win Rate | Max DD | Key Params |")
        report_lines.append("|------|--------|--------|---------|--------|----------|--------|------------|")
        
        for rank, result in enumerate(top_overall, 1):
            # 주요 파라미터만 표시
            params = result['params']
            key_params = f"RSI={params.get('rsi_long_threshold', '?')}/{params.get('rsi_short_threshold', '?')}, BB={params.get('bb_std_main', '?')}/{params.get('bb_std_strong', '?')}"
            
            report_lines.append(
                f"| {rank} | {result['period_name']} | {result['sharpe_ratio']:.4f} | {result['pnl_pct']:.2f} | "
                f"{result['trade_count']} | {result['win_rate']:.2%} | "
                f"{result['max_drawdown']:.2f}% | {key_params} |"
            )
        
        report_lines.append("")
        
        # ========================================
        # 추천 파라미터 후보
        # ========================================
        report_lines.append("## 추천 파라미터 후보 (Top 3)")
        report_lines.append("")
        
        for rank, result in enumerate(top_overall[:3], 1):
            report_lines.append(f"### Candidate #{rank}")
            report_lines.append("")
            report_lines.append(f"- **Period**: {result['period_name']}")
            report_lines.append(f"- **Sharpe Ratio**: {result['sharpe_ratio']:.4f}")
            report_lines.append(f"- **PnL**: {result['pnl_pct']:.2f}%")
            report_lines.append(f"- **Trades**: {result['trade_count']}")
            report_lines.append(f"- **Win Rate**: {result['win_rate']:.2%}")
            report_lines.append(f"- **Max Drawdown**: {result['max_drawdown']:.2f}%")
            report_lines.append("")
            report_lines.append("**Parameters**:")
            report_lines.append("```yaml")
            for key, value in result['params'].items():
                report_lines.append(f"  {key}: {value}")
            report_lines.append("```")
            report_lines.append("")
    else:
        report_lines.append("⚠️ 유효한 결과 없음")
        report_lines.append("")
    
    # ========================================
    # 리포트 저장
    # ========================================
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
    
    logger.info(f"✅ Markdown 리포트 생성: {output_path}")
    
    return str(output_path)


def generate_json_report(
    results_by_period: Dict[str, List[Dict[str, Any]]],
    output_path: str = "reports/tuning/phase28_2/phase28_2_tuning_results.json"
) -> str:
    """JSON 리포트 생성"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    report_data = {
        'phase': 'PHASE28-2',
        'strategy': 'btc5m_baseline_v1',
        'generated_at': datetime.now().isoformat(),
        'results_by_period': results_by_period
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, default=str)
    
    logger.info(f"✅ JSON 리포트 생성: {output_path}")
    
    return str(output_path)


def main():
    """메인 엔트리 포인트"""
    parser = argparse.ArgumentParser(
        description="PHASE28-2: Tuning Results Summarizer"
    )
    
    parser.add_argument(
        '--top-n',
        type=int,
        default=10,
        help='상위 N개 파라미터 세트'
    )
    
    args = parser.parse_args()
    
    try:
        logger.info("=" * 80)
        logger.info("PHASE28-2: Tuning Results Summarizer")
        logger.info("=" * 80)
        
        # 1. DB에서 결과 조회
        results_by_period = query_tuning_results(phase="PHASE28-2", strategy_name="btc5m_baseline_v1")
        
        if not results_by_period:
            logger.warning("⚠️  튜닝 결과 없음")
            logger.info("   - Random Search를 먼저 실행하세요: scripts/tuning/phase28_2_run_random_search.py")
            sys.exit(1)
        
        # 2. Markdown 리포트 생성
        md_path = generate_markdown_report(results_by_period, top_n=args.top_n)
        
        # 3. JSON 리포트 생성
        json_path = generate_json_report(results_by_period)
        
        logger.info("=" * 80)
        logger.info("✅ 리포트 생성 완료")
        logger.info(f"   - Markdown: {md_path}")
        logger.info(f"   - JSON: {json_path}")
        logger.info("=" * 80)
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"❌ 리포트 생성 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
