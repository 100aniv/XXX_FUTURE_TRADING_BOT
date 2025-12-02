#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE25-1: Tuning Worker CLI
=============================
튜닝 Job을 처리하는 Worker를 실행하는 CLI

사용법:
    # 한 번만 실행
    python scripts/infra/phase25_1_run_worker.py --worker-id worker-001 --once
    
    # 계속 루프 (Ctrl+C로 종료)
    python scripts/infra/phase25_1_run_worker.py --worker-id worker-001
    
    # 특정 Run만 처리
    python scripts/infra/phase25_1_run_worker.py --worker-id worker-001 --run-id run_abc123
    
    # Poll 간격 조정 (Job이 없을 때 대기 시간)
    python scripts/infra/phase25_1_run_worker.py --worker-id worker-001 --poll-interval 10

예시:
    # Worker 2개를 동시에 실행 (서로 다른 터미널)
    python scripts/infra/phase25_1_run_worker.py --worker-id worker-001
    python scripts/infra/phase25_1_run_worker.py --worker-id worker-002
"""
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tuning.cluster import JobQueue, TuningWorker
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


def print_banner(worker_id: str, run_id: str = None, once: bool = False, poll_interval: int = 5):
    """Worker 시작 배너 출력"""
    banner = f"""
{'=' * 80}
🔧 PHASE25-1: Tuning Worker
{'=' * 80}
Worker ID: {worker_id}
Target Run: {run_id if run_id else 'ALL'}
Mode: {'One-shot (1개 Job만 처리)' if once else 'Loop (계속 실행)'}
Poll Interval: {poll_interval}초 (Job 없을 때 대기 시간)
{'=' * 80}
"""
    print(banner)
    logger.info(f"🚀 Tuning Worker 시작: {worker_id}")
    if run_id:
        logger.info(f"   Target Run: {run_id}")
    if once:
        logger.info(f"   Mode: One-shot")
    else:
        logger.info(f"   Mode: Loop (Ctrl+C to stop)")
    logger.info(f"   Poll Interval: {poll_interval}초")


def main():
    parser = argparse.ArgumentParser(
        description="PHASE25-1 Tuning Worker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 한 번만 실행
  python scripts/infra/phase25_1_run_worker.py --worker-id worker-001 --once
  
  # 계속 루프
  python scripts/infra/phase25_1_run_worker.py --worker-id worker-001
  
  # 특정 Run만 처리
  python scripts/infra/phase25_1_run_worker.py --worker-id worker-001 --run-id run_abc123
        """
    )
    
    parser.add_argument(
        "--worker-id",
        required=True,
        help="Worker ID (예: worker-001, worker-002)"
    )
    
    parser.add_argument(
        "--once",
        action="store_true",
        help="1개 job만 처리 후 종료"
    )
    
    parser.add_argument(
        "--run-id",
        default=None,
        help="특정 Run만 처리 (지정하지 않으면 모든 Run 처리)"
    )
    
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Job이 없을 때 대기 시간 (초, 기본값: 5)"
    )
    
    args = parser.parse_args()
    
    # 배너 출력
    print_banner(
        worker_id=args.worker_id,
        run_id=args.run_id,
        once=args.once,
        poll_interval=args.poll_interval
    )
    
    # Worker 초기화
    job_queue = JobQueue()
    worker = TuningWorker(
        worker_id=args.worker_id,
        job_queue=job_queue,
        run_id=args.run_id
    )
    
    # Worker 실행
    try:
        worker.loop(once=args.once, poll_interval_sec=args.poll_interval)
    except KeyboardInterrupt:
        logger.info("⏹️  Worker 중지 (Ctrl+C)")
        worker.stop()
    except Exception as e:
        logger.error(f"❌ Worker 오류: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info("✅ Worker 종료")
    logger.info(f"   처리한 Job 수: {worker.jobs_processed}개")


if __name__ == "__main__":
    main()
