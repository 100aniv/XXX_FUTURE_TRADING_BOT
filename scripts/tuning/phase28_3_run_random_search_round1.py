#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-3: Random Search Round 1 - Fully Automated Execution
=============================================================
대규모 Random Search (≥20 trials, ≥2 market periods) 완전 자동화 스크립트

주요 기능:
1. 환경 검증 (Python version, DB/Redis 연결)
2. Job 제출 (ParamSpace 샘플링 + JobQueue enqueue)
3. 진행 상황 모니터링 (자동 status 출력)
4. 결과 집계 및 리포트 생성 (Markdown + JSON)

Usage:
    python scripts/tuning/phase28_3_run_random_search_round1.py --trials 20 --periods bull,range
    python scripts/tuning/phase28_3_run_random_search_round1.py --trials 10 --periods neutral --smoke
"""
import sys
import os
import argparse
import time
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection
from tuning.algorithms.random_search import ParamSpace, RandomSearchConfig, RandomSearchTuner
from tuning.cluster.job_queue import JobQueue
from tuning.cluster.worker import TuningWorker
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


# ========================================
# Utility Functions
# ========================================

def generate_run_id(base_name: str) -> str:
    """Generate unique run_id with timestamp (including milliseconds)"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:21]  # YYYYmmdd_HHMMSS_fff
    return f"{base_name}_{timestamp}"


# ========================================
# Environment Check
# ========================================

def check_environment():
    """환경 검증: Python version, DB, Redis"""
    logger.info("=" * 80)
    logger.info("🔍 Environment Check")
    logger.info("=" * 80)
    
    # Python version
    if sys.version_info < (3, 9):
        logger.error(f"❌ Python 3.9+ required (current: {sys.version})")
        return False
    logger.info(f"✅ Python version: {sys.version.split()[0]}")
    
    # Postgres
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
                logger.info(f"✅ Postgres reachable: {version.split(',')[0]}")
    except Exception as e:
        logger.error(f"❌ Postgres unreachable: {e}")
        return False
    
    # Redis (optional, 현재 tuning은 Redis 필수 아님)
    # TODO: Add Redis check if needed
    
    logger.info("=" * 80)
    logger.info("✅ Environment check PASSED")
    logger.info("=" * 80)
    return True


# ========================================
# Load ParamSpace
# ========================================

def load_param_space(yaml_path: str) -> Tuple[ParamSpace, Dict[str, Any]]:
    """ParamSpace YAML 로딩"""
    logger.info(f"📄 Loading ParamSpace YAML: {yaml_path}")
    
    if not Path(yaml_path).exists():
        raise FileNotFoundError(f"❌ ParamSpace YAML not found: {yaml_path}")
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # ParamSpace 생성
    param_space_dict = data.get('param_space', {})
    param_space = ParamSpace(space=param_space_dict)
    param_space.validate()
    
    logger.info(f"✅ ParamSpace loaded: {len(param_space_dict)} parameters")
    
    # Metadata
    metadata = {
        'run_metadata': data.get('run_metadata', {}),
        'market_periods': data.get('market_periods', {}),
        'base_config': data.get('base_config', {}),
    }
    
    return param_space, metadata


# ========================================
# Job Submission
# ========================================

def submit_jobs_for_period(
    param_space: ParamSpace,
    period_name: str,
    period_config: Dict[str, Any],
    n_trials: int,
    base_config_path: str,
    seed: int,
    phase: str = "PHASE28-3"
) -> str:
    """특정 market period에 대해 N개 jobs 제출"""
    logger.info("=" * 80)
    logger.info(f"🚀 Submitting jobs for period: {period_name}")
    logger.info("=" * 80)
    logger.info(f"📊 Period: {period_config.get('name')} ({period_config.get('start')} ~ {period_config.get('end')})")
    logger.info(f"🔢 Trials: {n_trials}")
    logger.info(f"🌱 Seed: {seed}")
    
    # RandomSearchConfig 생성
    run_name = f"phase28_3_{period_name}"
    config = RandomSearchConfig(
        run_name=run_name,
        phase=phase,
        strategy_family="baseline",
        strategy_name="btc5m_baseline_v1",
        mode="backtest",
        tuning_method="random",
        target_metric="sharpe_like_ratio",
        n_trials=n_trials,
        base_config_path=base_config_path,
        param_space=param_space,
        seed=seed,
        metadata={
            'period_name': period_name,
            'period_config': period_config
        }
    )
    
    # Run 생성 및 Jobs enqueue
    tuner = RandomSearchTuner()
    run_id, job_ids = tuner.create_run_and_jobs(config)
    
    logger.info(f"✅ Jobs submitted: run_id={run_id}, {len(job_ids)} jobs enqueued")
    logger.info("=" * 80)
    
    return run_id


# ========================================
# Progress Monitoring
# ========================================

def monitor_progress(run_ids: List[str], check_interval: int = 30, timeout: int = 7200):
    """
    진행 상황 모니터링 및 자동 종료
    
    Args:
        run_ids: 모니터링할 run_id 리스트
        check_interval: 체크 간격 (초)
        timeout: 최대 대기 시간 (초, 기본 2시간)
    """
    logger.info("=" * 80)
    logger.info("📊 Progress Monitoring Started")
    logger.info("=" * 80)
    logger.info(f"🕒 Check interval: {check_interval}s")
    logger.info(f"⏰ Timeout: {timeout}s")
    
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            logger.warning(f"⏰ Timeout reached ({timeout}s), exiting monitor")
            break
        
        all_completed = True
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for run_id in run_ids:
                    # Job status 확인
                    cur.execute("""
                        SELECT status, COUNT(*) as count
                        FROM tuning.jobs
                        WHERE run_id = %s
                        GROUP BY status
                    """, (run_id,))
                    status_counts = dict(cur.fetchall())
                    
                    pending = status_counts.get('PENDING', 0)
                    running = status_counts.get('RUNNING', 0)
                    completed = status_counts.get('COMPLETED', 0)
                    failed = status_counts.get('FAILED', 0)
                    total = sum(status_counts.values())
                    
                    # Progress 출력
                    progress_pct = (completed / total * 100) if total > 0 else 0
                    logger.info(f"[{run_id[:20]}...] {completed}/{total} completed ({progress_pct:.1f}%), "
                               f"{running} running, {failed} failed, {pending} pending")
                    
                    # 모든 job 완료되지 않았으면 계속 대기
                    if completed + failed < total:
                        all_completed = False
        
        # 모든 run의 모든 job이 완료되면 종료
        if all_completed:
            logger.info("=" * 80)
            logger.info("✅ All jobs completed!")
            logger.info("=" * 80)
            break
        
        # 대기
        time.sleep(check_interval)
    
    logger.info(f"⏱️  Total monitoring time: {elapsed:.1f}s")


# ========================================
# Result Aggregation
# ========================================

def aggregate_results(run_ids: List[str], top_n: int = 10) -> Dict[str, Any]:
    """
    결과 집계 및 분석
    
    Args:
        run_ids: 집계할 run_id 리스트
        top_n: 상위 N개 선정
    
    Returns:
        집계 결과 딕셔너리
    """
    logger.info("=" * 80)
    logger.info("📊 Result Aggregation")
    logger.info("=" * 80)
    
    all_results = []
    period_results = {}
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for run_id in run_ids:
                # 결과 조회 (유효한 결과만)
                cur.execute("""
                    SELECT 
                        r.run_id,
                        r.job_id,
                        r.pnl,
                        r.pnl_pct,
                        r.sharpe_ratio,
                        r.trade_count,
                        r.win_rate,
                        r.max_drawdown,
                        j.params_json,
                        j.created_at
                    FROM tuning.results r
                    JOIN tuning.jobs j ON r.job_id = j.job_id
                    WHERE r.run_id = %s
                      AND r.trade_count >= 10
                      AND r.max_drawdown <= 20.0
                    ORDER BY r.sharpe_ratio DESC
                """, (run_id,))
                
                results = cur.fetchall()
                
                # Period 추출 (run_id에서)
                period_name = run_id.split('_')[2] if '_' in run_id else 'unknown'
                period_results[period_name] = results
                all_results.extend(results)
                
                logger.info(f"[{period_name}] {len(results)} valid results (trade_count≥10, MDD≤20%)")
    
    # 전체 Top-N
    all_results_sorted = sorted(all_results, key=lambda x: x[4], reverse=True)  # sharpe_ratio DESC
    top_n_overall = all_results_sorted[:top_n]
    
    logger.info("=" * 80)
    logger.info(f"🏆 Overall Top {top_n} Results:")
    for i, row in enumerate(top_n_overall, 1):
        logger.info(f"  [{i}] Sharpe={row[4]:.4f}, PnL={row[2]:.2f}, Win Rate={row[6]:.2%}, Trades={row[5]}")
    logger.info("=" * 80)
    
    # Period별 Top-N
    top_n_per_period = {}
    for period_name, results in period_results.items():
        top_n_period = results[:top_n]
        top_n_per_period[period_name] = top_n_period
        logger.info(f"[{period_name}] Top {len(top_n_period)} Results")
    
    aggregation = {
        'overall_top_n': top_n_overall,
        'period_top_n': top_n_per_period,
        'all_results': all_results_sorted,
        'total_valid_results': len(all_results),
        'generated_at': datetime.now().isoformat()
    }
    
    return aggregation


# ========================================
# Report Generation
# ========================================

def generate_markdown_report(aggregation: Dict[str, Any], output_path: str):
    """Markdown 리포트 생성"""
    logger.info(f"📝 Generating Markdown report: {output_path}")
    
    overall_top_n = aggregation['overall_top_n']
    period_top_n = aggregation['period_top_n']
    total_valid = aggregation['total_valid_results']
    
    # Markdown 작성
    lines = []
    lines.append("# PHASE28-3: Random Search Round 1 - Results")
    lines.append("")
    lines.append(f"**Generated**: {aggregation['generated_at']}")
    lines.append(f"**Total Valid Results**: {total_valid}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Overall Top-N
    lines.append(f"## 🏆 Overall Top {len(overall_top_n)} Results")
    lines.append("")
    lines.append("| Rank | Job ID | Sharpe Ratio | PnL (USDT) | Win Rate | Trades | Max DD (%) |")
    lines.append("|------|--------|--------------|------------|----------|--------|------------|")
    for i, row in enumerate(overall_top_n, 1):
        job_id = row[1]
        sharpe = row[4]
        pnl = row[2]
        win_rate = row[6]
        trades = row[5]
        max_dd = row[7]
        lines.append(f"| {i} | {job_id} | {sharpe:.4f} | {pnl:.2f} | {win_rate:.2%} | {trades} | {max_dd:.2f} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Period별 Top-N
    for period_name, results in period_top_n.items():
        lines.append(f"## 📊 {period_name.upper()} Period - Top {len(results)} Results")
        lines.append("")
        lines.append("| Rank | Job ID | Sharpe Ratio | PnL (USDT) | Win Rate | Trades | Max DD (%) |")
        lines.append("|------|--------|--------------|------------|----------|--------|------------|")
        for i, row in enumerate(results, 1):
            job_id = row[1]
            sharpe = row[4]
            pnl = row[2]
            win_rate = row[6]
            trades = row[5]
            max_dd = row[7]
            lines.append(f"| {i} | {job_id} | {sharpe:.4f} | {pnl:.2f} | {win_rate:.2%} | {trades} | {max_dd:.2f} |")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    # Top 3 Candidates (추천 파라미터)
    lines.append("## 🎯 Top 3 Recommended Candidates")
    lines.append("")
    lines.append("**For PHASE28-4/PHASE29 parameter tuning:**")
    lines.append("")
    for i, row in enumerate(overall_top_n[:3], 1):
        job_id = row[1]
        params = row[8]  # params_json
        lines.append(f"### Candidate {i}: {job_id}")
        lines.append("")
        lines.append(f"- **Sharpe Ratio**: {row[4]:.4f}")
        lines.append(f"- **PnL (USDT)**: {row[2]:.2f}")
        lines.append(f"- **Win Rate**: {row[6]:.2%}")
        lines.append(f"- **Trades**: {row[5]}")
        lines.append(f"- **Max DD (%)**: {row[7]:.2f}")
        lines.append("")
        lines.append("**Parameters**:")
        lines.append("```json")
        lines.append(json.dumps(params, indent=2))
        lines.append("```")
        lines.append("")
    
    # 파일 쓰기
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    logger.info(f"✅ Markdown report saved: {output_path}")


def generate_json_results(aggregation: Dict[str, Any], output_path: str):
    """JSON 결과 파일 생성"""
    logger.info(f"📝 Generating JSON results: {output_path}")
    
    # JSON 직렬화 가능한 형태로 변환
    def row_to_dict(row):
        return {
            'run_id': row[0],
            'job_id': row[1],
            'pnl': float(row[2]),
            'pnl_pct': float(row[3]),
            'sharpe_ratio': float(row[4]),
            'trade_count': int(row[5]),
            'win_rate': float(row[6]),
            'max_drawdown': float(row[7]),
            'params': row[8],
            'created_at': row[9].isoformat() if row[9] else None
        }
    
    output_data = {
        'overall_top_n': [row_to_dict(row) for row in aggregation['overall_top_n']],
        'period_top_n': {
            period: [row_to_dict(row) for row in results]
            for period, results in aggregation['period_top_n'].items()
        },
        'all_results': [row_to_dict(row) for row in aggregation['all_results']],
        'total_valid_results': aggregation['total_valid_results'],
        'generated_at': aggregation['generated_at']
    }
    
    # 파일 쓰기
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ JSON results saved: {output_path}")


# ========================================
# Worker Execution
# ========================================

def run_worker(run_ids: List[str]):
    """
    Worker 실행 (모든 job 완료까지 loop)
    
    Args:
        run_ids: 처리할 run_id 리스트
    """
    logger.info("=" * 80)
    logger.info("🔨 Starting TuningWorker")
    logger.info("=" * 80)
    logger.info(f"🎯 Target run_ids: {run_ids}")
    
    job_queue = JobQueue()
    
    # run_id 필터링을 위해 각 run_id별로 Worker 생성 및 처리
    for run_id in run_ids:
        logger.info(f"🔨 Processing run: {run_id}")
        worker = TuningWorker(worker_id=f"phase28_3_worker_{run_id[:8]}", job_queue=job_queue, run_id=run_id)
        
        # 해당 run의 모든 job이 완료될 때까지 loop
        while True:
            # 남은 pending job 확인
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM tuning.jobs 
                        WHERE run_id = %s AND status = 'PENDING'
                    """, (run_id,))
                    pending_count = cur.fetchone()[0]
            
            if pending_count == 0:
                logger.info(f"✅ All jobs completed for run: {run_id}")
                break
            
            # 1개 job 처리
            worker.loop(once=True, poll_interval_sec=5)
    
    logger.info("=" * 80)
    logger.info("🔨 TuningWorker finished")
    logger.info("=" * 80)


# ========================================
# Main
# ========================================

def main():
    parser = argparse.ArgumentParser(
        description='PHASE28-3: Random Search Round 1 - Fully Automated Execution',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('--trials', type=int, default=20,
                        help='Number of trials per period')
    parser.add_argument('--periods', type=str, default='bull,range',
                        help='Comma-separated list of periods (bull, range, neutral)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility')
    parser.add_argument('--top-n', type=int, default=10,
                        help='Top N results to select')
    parser.add_argument('--smoke', action='store_true',
                        help='Smoke test mode (reduced trials)')
    parser.add_argument('--check-interval', type=int, default=30,
                        help='Progress check interval (seconds)')
    
    args = parser.parse_args()
    
    # Smoke test mode
    if args.smoke:
        logger.info("🔥 Smoke test mode enabled (reduced trials)")
        args.trials = min(args.trials, 2)
    
    # 실행 시작
    logger.info("=" * 80)
    logger.info("🚀 PHASE28-3: Random Search Round 1 Execution")
    logger.info("=" * 80)
    logger.info(f"🔢 Trials per period: {args.trials}")
    logger.info(f"📊 Periods: {args.periods}")
    logger.info(f"🌱 Seed: {args.seed}")
    logger.info(f"🏆 Top-N: {args.top_n}")
    logger.info("=" * 80)
    
    # Step 1: Environment check
    if not check_environment():
        logger.error("❌ Environment check failed. Exiting.")
        return 1
    
    # Step 2: Load ParamSpace
    param_space_yaml = project_root / "configs" / "tuning" / "phase28_2_btc5m_baseline_paramspace.yml"
    param_space, metadata = load_param_space(str(param_space_yaml))
    
    # Market periods
    market_periods = metadata['market_periods']
    selected_periods = args.periods.split(',')
    
    # 선택된 period 검증
    for period in selected_periods:
        if period not in market_periods:
            logger.error(f"❌ Invalid period: {period}. Available: {list(market_periods.keys())}")
            return 1
    
    # Base config path
    base_config_path = metadata['base_config'].get('path', 'configs/backtest/phase28_2_btc5m_tuning_base.yml')
    base_config_path = str(project_root / base_config_path)
    
    # Step 3: Submit jobs for each period
    run_ids = []
    for period_name in selected_periods:
        period_config = market_periods[period_name]
        run_id = submit_jobs_for_period(
            param_space=param_space,
            period_name=period_name,
            period_config=period_config,
            n_trials=args.trials,
            base_config_path=base_config_path,
            seed=args.seed
        )
        run_ids.append(run_id)
    
    logger.info(f"✅ All jobs submitted: {len(run_ids)} runs, {args.trials * len(run_ids)} total jobs")
    
    # Step 4: Run worker (sequential processing)
    run_worker(run_ids)
    
    # Step 5: Monitor progress (확인용, worker가 이미 끝났으므로 빠르게 종료됨)
    monitor_progress(run_ids, check_interval=args.check_interval)
    
    # Step 6: Aggregate results
    aggregation = aggregate_results(run_ids, top_n=args.top_n)
    
    # Step 7: Generate reports
    markdown_output = project_root / "docs" / "PHASE28" / "PHASE28-3_RESULTS.md"
    json_output = project_root / "reports" / "tuning" / "phase28_3" / "results.json"
    
    generate_markdown_report(aggregation, str(markdown_output))
    generate_json_results(aggregation, str(json_output))
    
    # 완료
    logger.info("=" * 80)
    logger.info("✅ PHASE28-3 Random Search Round 1 COMPLETE")
    logger.info("=" * 80)
    logger.info(f"📝 Markdown report: {markdown_output}")
    logger.info(f"📊 JSON results: {json_output}")
    logger.info(f"🏆 Top {args.top_n} candidates selected")
    logger.info(f"📈 Total valid results: {aggregation['total_valid_results']}")
    logger.info("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
