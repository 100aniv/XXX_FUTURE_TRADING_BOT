#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE25-3: Bayesian Search Runner
==================================
Bayesian Optimization 기반 하이퍼파라미터 튜닝 실행 CLI

Usage:
    python scripts/infra/phase25_3_run_bayesian_search.py \\
        --run-name scalping_bayes_001 \\
        --strategy-name scalping \\
        --n-trials 30 \\
        --base-config configs/paper/phase21_scalping_quick.yml \\
        --target-metric sharpe_ratio \\
        --direction maximize \\
        --top-k 10
"""
import sys
import argparse
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Project root 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tuning.algorithms import BayesianSearchTuner, BayesianSearchConfig, ParamSpace
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


def parse_args():
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="PHASE25-3: Bayesian Search Runner"
    )
    
    # Run 설정
    parser.add_argument(
        '--run-name',
        type=str,
        required=True,
        help='Run 이름 (예: scalping_bayes_001)'
    )
    parser.add_argument(
        '--phase',
        type=str,
        default='PHASE25-3',
        help='PHASE 번호'
    )
    parser.add_argument(
        '--strategy-family',
        type=str,
        default='momentum',
        help='전략 패밀리'
    )
    parser.add_argument(
        '--strategy-name',
        type=str,
        default='scalping',
        help='전략 이름'
    )
    parser.add_argument(
        '--mode',
        type=str,
        default='backtest',
        choices=['backtest', 'paper'],
        help='실행 모드'
    )
    
    # 튜닝 파라미터
    parser.add_argument(
        '--n-trials',
        type=int,
        default=30,
        help='Trial 수'
    )
    parser.add_argument(
        '--base-config',
        type=str,
        required=True,
        help='Base config 파일 경로'
    )
    parser.add_argument(
        '--param-space-file',
        type=str,
        default=None,
        help='ParamSpace YAML 파일 경로 (없으면 기본값 사용)'
    )
    parser.add_argument(
        '--target-metric',
        type=str,
        default='sharpe_ratio',
        help='최적화 목표 메트릭'
    )
    parser.add_argument(
        '--direction',
        type=str,
        default='maximize',
        choices=['maximize', 'minimize'],
        help='최적화 방향'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='Random seed'
    )
    
    # 결과 출력
    parser.add_argument(
        '--top-k',
        type=int,
        default=10,
        help='상위 K개 결과 출력'
    )
    
    return parser.parse_args()


def load_param_space_from_file(filepath: str) -> ParamSpace:
    """
    YAML 파일에서 ParamSpace 로드
    
    Args:
        filepath: YAML 파일 경로
    
    Returns:
        ParamSpace 인스턴스
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        space_dict = yaml.safe_load(f)
    
    return ParamSpace(space=space_dict)


def get_default_param_space() -> ParamSpace:
    """
    기본 ParamSpace 반환 (scalping 전략용)
    
    Returns:
        ParamSpace 인스턴스
    """
    return ParamSpace(space={
        'rsi_period': {'type': 'int', 'min': 10, 'max': 20},
        'rsi_oversold': {'type': 'int', 'min': 25, 'max': 35},
        'rsi_overbought': {'type': 'int', 'min': 65, 'max': 75},
        'ema_fast': {'type': 'int', 'min': 5, 'max': 15},
        'ema_slow': {'type': 'int', 'min': 20, 'max': 40},
        'stop_loss_pct': {'type': 'float', 'min': 0.5, 'max': 2.0},
        'take_profit_pct': {'type': 'float', 'min': 0.3, 'max': 1.0},
    })


def print_top_k_results(results: list, k: int, target_metric: str):
    """
    상위 K개 결과 출력
    
    Args:
        results: 결과 리스트
        k: 출력 개수
        target_metric: 타겟 메트릭 이름
    """
    if not results:
        print("\n❌ 결과 없음")
        return
    
    print("\n" + "=" * 120)
    print(f"🏆 Top {min(k, len(results))} Results")
    print("=" * 120)
    
    # 테이블 헤더
    print(f"{'Rank':<6} {'Job Index':<12} {'PnL':<12} {'PnL%':<10} "
          f"{'Trades':<8} {'Win Rate':<10} {'Sharpe':<10} {target_metric.upper():<12}")
    print("-" * 120)
    
    # 결과 출력
    for i, result in enumerate(results[:k], 1):
        print(f"{i:<6} "
              f"#{result['job_index']:<11} "
              f"{result['pnl']:>11.2f} "
              f"{result['pnl_pct']:>9.2f}% "
              f"{result['trade_count']:>7} "
              f"{result['win_rate']:>9.2%} "
              f"{result['sharpe_ratio']:>9.4f} "
              f"{result[target_metric]:>11.4f}")
    
    print("=" * 120)
    
    # Best result 상세
    best = results[0]
    print(f"\n🥇 Best Result (Job #{best['job_index']}):")
    print(f"  Params: {json.dumps(best['params'], indent=2)}")
    print(f"  {target_metric}: {best[target_metric]:.4f}")
    print(f"  PnL: {best['pnl']:.2f} USDT ({best['pnl_pct']:.2f}%)")
    print(f"  Win Rate: {best['win_rate']:.2%} ({best['trade_count']} trades)")
    print(f"  Sharpe Ratio: {best['sharpe_ratio']:.4f}")


def save_summary_report(
    run_id: str,
    config: BayesianSearchConfig,
    results: list,
    elapsed_sec: float
):
    """
    요약 리포트 저장
    
    Args:
        run_id: Run ID
        config: BayesianSearchConfig
        results: 결과 리스트
        elapsed_sec: 실행 시간 (초)
    """
    # 리포트 디렉토리 생성
    report_dir = PROJECT_ROOT / 'logs' / 'tuning'
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # 파일 경로
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = report_dir / f"phase25_3_{config.run_name}_{timestamp}.md"
    
    # 리포트 작성
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# PHASE25-3: Bayesian Search Results\n\n")
        f.write(f"**Run ID**: `{run_id}`  \n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**Strategy**: {config.strategy_name} ({config.strategy_family})  \n")
        f.write(f"**Mode**: {config.mode}  \n")
        f.write(f"**Target Metric**: {config.target_metric} ({config.direction})  \n")
        f.write(f"**N Trials**: {config.n_trials}  \n")
        f.write(f"**Elapsed**: {elapsed_sec:.1f}s  \n\n")
        
        f.write("---\n\n")
        f.write("## Best Result\n\n")
        
        if results:
            best = results[0]
            f.write(f"- **Job Index**: #{best['job_index']}\n")
            f.write(f"- **{config.target_metric}**: {best[config.target_metric]:.4f}\n")
            f.write(f"- **PnL**: {best['pnl']:.2f} USDT ({best['pnl_pct']:.2f}%)\n")
            f.write(f"- **Win Rate**: {best['win_rate']:.2%} ({best['trade_count']} trades)\n")
            f.write(f"- **Sharpe Ratio**: {best['sharpe_ratio']:.4f}\n\n")
            f.write(f"### Params\n\n")
            f.write(f"```json\n{json.dumps(best['params'], indent=2)}\n```\n\n")
        else:
            f.write("❌ No results\n\n")
        
        f.write("---\n\n")
        f.write("## Top 10 Results\n\n")
        f.write("| Rank | Job Index | PnL | PnL% | Trades | Win Rate | Sharpe | Target |\n")
        f.write("|------|-----------|-----|------|--------|----------|--------|--------|\n")
        
        for i, result in enumerate(results[:10], 1):
            f.write(f"| {i} | #{result['job_index']} | "
                   f"{result['pnl']:.2f} | {result['pnl_pct']:.2f}% | "
                   f"{result['trade_count']} | {result['win_rate']:.2%} | "
                   f"{result['sharpe_ratio']:.4f} | "
                   f"{result[config.target_metric]:.4f} |\n")
        
        f.write("\n")
    
    print(f"\n💾 Summary report saved: {report_path}")


def main():
    """메인 함수"""
    print("=" * 120)
    print("PHASE25-3: Bayesian Search Runner")
    print("=" * 120)
    
    # 1. CLI 인자 파싱
    args = parse_args()
    
    print(f"\n📋 Configuration:")
    print(f"  Run Name: {args.run_name}")
    print(f"  Strategy: {args.strategy_name}")
    print(f"  N Trials: {args.n_trials}")
    print(f"  Base Config: {args.base_config}")
    print(f"  Target Metric: {args.target_metric} ({args.direction})")
    print(f"  Seed: {args.seed}")
    
    # 2. ParamSpace 로드
    if args.param_space_file:
        print(f"\n📂 Loading param space from: {args.param_space_file}")
        param_space = load_param_space_from_file(args.param_space_file)
    else:
        print(f"\n📂 Using default param space (scalping)")
        param_space = get_default_param_space()
    
    print(f"  Param count: {len(param_space.space)}")
    for param_name, spec in param_space.space.items():
        print(f"    - {param_name}: {spec}")
    
    # 3. BayesianSearchConfig 생성
    config = BayesianSearchConfig(
        run_name=args.run_name,
        phase=args.phase,
        strategy_family=args.strategy_family,
        strategy_name=args.strategy_name,
        mode=args.mode,
        tuning_method='bayesian',
        target_metric=args.target_metric,
        n_trials=args.n_trials,
        base_config_path=args.base_config,
        param_space=param_space,
        direction=args.direction,
        seed=args.seed
    )
    
    # 4. Tuner 생성 및 실행
    print("\n" + "=" * 120)
    print("🚀 Starting Bayesian Search...")
    print("=" * 120)
    
    import time
    start_time = time.time()
    
    try:
        tuner = BayesianSearchTuner()
        run_id = tuner.run_sequential(config)
        
        elapsed = time.time() - start_time
        
        print("\n" + "=" * 120)
        print(f"✅ Bayesian Search Completed ({elapsed:.1f}s)")
        print("=" * 120)
        
        # 5. 결과 조회 및 출력
        ascending = (args.direction == 'minimize')
        results = tuner.get_top_k_results(run_id, k=args.top_k, ascending=ascending)
        
        print_top_k_results(results, args.top_k, args.target_metric)
        
        # 6. 요약 리포트 저장
        save_summary_report(run_id, config, results, elapsed)
        
        print("\n" + "=" * 120)
        print("✅ DONE")
        print("=" * 120)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
