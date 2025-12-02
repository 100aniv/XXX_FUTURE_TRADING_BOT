#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE25-2: Random Search Runner
================================
Random Search 튜닝 실행 CLI

Usage:
    python scripts/infra/phase25_2_run_random_search.py \\
        --run-name scalping_rsi_tuning \\
        --strategy-name scalping \\
        --n-trials 20 \\
        --base-config configs/paper/phase21_scalping_quick.yml \\
        --param-space-file tuning_params/scalping_param_space.yml \\
        --max-workers 1

Features:
    - Random Search 알고리즘을 통한 하이퍼파라미터 튜닝
    - JobQueue 기반 분산 실행 (multi-worker 지원)
    - 상위 K개 결과 자동 추출 및 요약
"""
import sys
import argparse
import time
import yaml
from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tuning.algorithms import RandomSearchTuner, ParamSpace, RandomSearchConfig
from tuning.cluster import JobQueue, TuningWorker
from common.logger import setup_logger

logger = setup_logger("phase25_2_random_search")


def load_param_space_from_file(filepath: str) -> ParamSpace:
    """
    YAML 파일에서 ParamSpace 로드
    
    Args:
        filepath: YAML 파일 경로
    
    Returns:
        ParamSpace: 로드된 ParamSpace
    
    Examples:
        YAML 파일 예시:
        ```yaml
        rsi_oversold:
          type: int
          min: 25
          max: 35
        rsi_overbought:
          type: int
          min: 65
          max: 75
        stop_loss_pct:
          type: float
          min: 0.5
          max: 2.0
        ```
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        space_dict = yaml.safe_load(f)
    
    return ParamSpace(space=space_dict)


def run_workers(run_id: str, max_workers: int, job_queue: JobQueue):
    """
    Worker 실행 (동기 모드)
    
    Args:
        run_id: Run ID
        max_workers: 최대 Worker 수
        job_queue: JobQueue 인스턴스
    """
    logger.info("=" * 80)
    logger.info(f"🚀 Worker 시작: {max_workers}개")
    logger.info("=" * 80)
    
    # 단순 구현: 단일 Worker가 모든 Job 순차 처리
    # (추후: 멀티프로세싱으로 확장 가능)
    
    if max_workers == 1:
        # 단일 Worker 모드
        worker = TuningWorker(
            worker_id="worker-001",
            job_queue=job_queue,
            run_id=run_id
        )
        
        # Job이 없을 때까지 계속 처리
        while True:
            # Run 상태 확인
            status = job_queue.get_run_status(run_id)
            pending_count = status.get('pending_jobs', 0)
            
            if pending_count == 0:
                logger.info("✅ 모든 Job 처리 완료")
                break
            
            logger.info(f"📊 남은 Job: {pending_count}개")
            
            # 1개 Job 처리
            worker.loop(once=True, poll_interval_sec=2)
    
    else:
        # Multi-worker 모드 (미구현)
        logger.warning("⚠️  Multi-worker 모드는 아직 미구현. max_workers=1로 실행")
        run_workers(run_id, 1, job_queue)


def print_top_k_results(run_id: str, tuner: RandomSearchTuner, k: int = 10):
    """
    상위 K개 결과 출력
    
    Args:
        run_id: Run ID
        tuner: RandomSearchTuner 인스턴스
        k: 상위 k개
    """
    logger.info("=" * 80)
    logger.info(f"📊 Top {k} 결과")
    logger.info("=" * 80)
    
    top_k = tuner.get_top_k_results(run_id, k=k, ascending=False)
    
    if not top_k:
        logger.warning("⚠️  결과 없음")
        return
    
    # 표 형식 출력
    header = f"{'Rank':<6} {'Sharpe':<10} {'PnL':<12} {'PnL%':<10} {'Trades':<8} {'Win%':<10}"
    logger.info(header)
    logger.info("-" * 80)
    
    for i, result in enumerate(top_k, 1):
        line = (
            f"{i:<6} "
            f"{result.get('sharpe_ratio', 0):<10.4f} "
            f"{result.get('pnl', 0):<12.2f} "
            f"{result.get('pnl_pct', 0):<10.2f} "
            f"{result.get('trade_count', 0):<8} "
            f"{result.get('win_rate', 0) * 100:<10.2f}"
        )
        logger.info(line)
    
    logger.info("=" * 80)


def save_summary_report(run_id: str, tuner: RandomSearchTuner, output_path: str):
    """
    요약 리포트 저장
    
    Args:
        run_id: Run ID
        tuner: RandomSearchTuner 인스턴스
        output_path: 출력 파일 경로
    """
    logger.info(f"💾 요약 리포트 저장: {output_path}")
    
    # Run 상태 조회
    status = tuner.job_queue.get_run_status(run_id)
    
    # Top 10 결과 조회
    top_10 = tuner.get_top_k_results(run_id, k=10, ascending=False)
    
    # Markdown 리포트 생성
    report = f"""# Random Search 튜닝 결과

## Run 정보
- **Run ID**: {run_id}
- **총 Job 수**: {status.get('total_jobs', 0)}
- **완료**: {status.get('completed_jobs', 0)}
- **실패**: {status.get('failed_jobs', 0)}
- **상태**: {status.get('status', 'N/A')}

## Top 10 결과

| Rank | Sharpe | PnL (USDT) | PnL (%) | Trades | Win Rate (%) |
|------|--------|------------|---------|--------|--------------|
"""
    
    for i, result in enumerate(top_10, 1):
        report += (
            f"| {i} | {result.get('sharpe_ratio', 0):.4f} | "
            f"{result.get('pnl', 0):.2f} | {result.get('pnl_pct', 0):.2f} | "
            f"{result.get('trade_count', 0)} | {result.get('win_rate', 0) * 100:.2f} |\n"
        )
    
    # 저장
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"✅ 저장 완료: {output_path}")


def main():
    """메인 진입점"""
    parser = argparse.ArgumentParser(
        description='PHASE25-2: Random Search 튜닝 실행',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('--run-name', type=str, required=True,
                        help='Run 이름 (예: scalping_rsi_tuning)')
    parser.add_argument('--phase', type=str, default='PHASE25-2',
                        help='PHASE 번호')
    parser.add_argument('--strategy-family', type=str, default='momentum',
                        help='전략 패밀리 (예: momentum, volatility)')
    parser.add_argument('--strategy-name', type=str, required=True,
                        help='전략 이름 (예: scalping)')
    parser.add_argument('--mode', type=str, default='paper', choices=['backtest', 'paper'],
                        help='실행 모드')
    parser.add_argument('--target-metric', type=str, default='sharpe_ratio',
                        help='최적화 목표 메트릭')
    parser.add_argument('--n-trials', type=int, required=True,
                        help='총 trial 수')
    parser.add_argument('--base-config', type=str, required=True,
                        help='기본 config YAML 파일 경로')
    parser.add_argument('--param-space-file', type=str, default=None,
                        help='ParamSpace YAML 파일 경로 (옵션)')
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed (재현성)')
    parser.add_argument('--max-workers', type=int, default=1,
                        help='최대 Worker 수')
    parser.add_argument('--top-k', type=int, default=10,
                        help='상위 k개 결과 출력')
    parser.add_argument('--output', type=str, default=None,
                        help='요약 리포트 출력 경로')
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("🎯 PHASE25-2: Random Search 시작")
    logger.info("=" * 80)
    
    # 1. ParamSpace 정의
    if args.param_space_file:
        logger.info(f"📄 ParamSpace 로드: {args.param_space_file}")
        param_space = load_param_space_from_file(args.param_space_file)
    else:
        # 기본 ParamSpace (scalping 예시)
        logger.info("📄 기본 ParamSpace 사용 (scalping)")
        param_space = ParamSpace(space={
            'entry_threshold': {'type': 'float', 'min': 0.3, 'max': 0.7},
            'exit_threshold': {'type': 'float', 'min': 0.2, 'max': 0.5},
            'stop_loss_pct': {'type': 'float', 'min': 0.5, 'max': 2.0},
            'take_profit_pct': {'type': 'float', 'min': 0.3, 'max': 1.0},
        })
    
    # 2. RandomSearchConfig 생성
    config = RandomSearchConfig(
        run_name=args.run_name,
        phase=args.phase,
        strategy_family=args.strategy_family,
        strategy_name=args.strategy_name,
        mode=args.mode,
        tuning_method='random',
        target_metric=args.target_metric,
        n_trials=args.n_trials,
        base_config_path=args.base_config,
        param_space=param_space,
        seed=args.seed
    )
    
    # 3. Tuner 생성
    tuner = RandomSearchTuner()
    
    # 4. Run 및 Job 생성
    try:
        run_id, job_ids = tuner.create_run_and_jobs(config)
        logger.info(f"✅ Run 생성 완료: {run_id}")
        logger.info(f"✅ Job {len(job_ids)}개 생성 완료")
    except Exception as e:
        logger.error(f"❌ Run/Job 생성 실패: {e}")
        return 1
    
    # 5. Worker 실행
    try:
        run_workers(run_id, args.max_workers, tuner.job_queue)
    except KeyboardInterrupt:
        logger.warning("⚠️  사용자 중단")
        # Run 취소
        tuner.job_queue.cancel_run(run_id)
        return 130
    except Exception as e:
        logger.error(f"❌ Worker 실행 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    # 6. 결과 출력
    print_top_k_results(run_id, tuner, k=args.top_k)
    
    # 7. 요약 리포트 저장
    if args.output:
        save_summary_report(run_id, tuner, args.output)
    else:
        default_output = f"artifacts/tuning/{run_id}_summary.md"
        save_summary_report(run_id, tuner, default_output)
    
    logger.info("=" * 80)
    logger.info("✅ Random Search 완료")
    logger.info("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
