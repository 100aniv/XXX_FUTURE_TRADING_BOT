#!/usr/bin/env python
"""
튜닝 자동 루프 스크립트 (Phase 1.5)

자동으로 주기적으로 튜닝을 실행하고 결과를 Redis로 발행합니다.

Usage:
    python scripts/run_tuner_loop.py --interval 3600 --trials 3

참조:
    - PR13_ARCHITECTURE_DESIGN.md (1.2 런타임 역할)
    - PR13_MASTER_PLAN.md (런타임/컨테이너 역할)
    - .windsurfrules (Runtime & Roles)
"""

import argparse
import os
import sys
import time
from pathlib import Path
from datetime import datetime
import uuid
import json

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tuning.config_overlay import ConfigOverlay
from tuning.ensemble_tuner import EnsembleTuner
from common.logger import logger


def publish_to_redis(redis_client, namespace: str, env: str, run_id: str, params: dict):
    """
    최적 파라미터를 Redis로 발행
    
    채널: {ns}:{env}:{run_id}:tuning.params.set
    """
    try:
        channel = f"{namespace}:{env}:{run_id}:tuning.params.set"
        message = json.dumps({
            "timestamp": datetime.now().isoformat(),
            "params": params,
            "source": "ensemble_tuner"
        })
        
        redis_client.publish(channel, message)
        logger.info(f"✅ Redis 발행 성공: {channel}")
        
    except Exception as e:
        logger.error(f"❌ Redis 발행 실패: {e}")


def run_tuning_cycle(args, redis_client=None):
    """단일 튜닝 사이클 실행"""
    
    # Study 이름 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    study_name = f"ensemble_tuning_{timestamp}"
    
    # Storage URL 설정
    storage = args.storage or os.getenv(
        "DATABASE_URL",
        "postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db"
    )
    
    # run_id 생성
    run_id = str(uuid.uuid4())
    env = "tuner"
    
    logger.info("=" * 80)
    logger.info("🔄 튜닝 사이클 시작")
    logger.info("=" * 80)
    logger.info(f"Study: {study_name}")
    logger.info(f"Trials: {args.trials}")
    logger.info(f"Window: {args.window}시간")
    logger.info(f"Run ID: {run_id}")
    logger.info("=" * 80)
    
    try:
        # ConfigOverlay 초기화
        config_overlay = ConfigOverlay(
            base_config_path=args.base_config,
            redis_client=redis_client,
            namespace="fa",
            env=env,
            run_id=run_id
        )
        
        # EnsembleTuner 초기화
        tuner = EnsembleTuner(
            study_name=study_name,
            storage=storage,
            window_hours=args.window,
            config_overlay=config_overlay
        )
        
        # 최적화 실행
        logger.info(f"🎯 최적화 시작 ({args.trials} trials)...")
        best_params = tuner.optimize(n_trials=args.trials)
        
        logger.info("=" * 80)
        logger.info("✅ 튜닝 사이클 완료!")
        logger.info(f"📈 Best 값: {tuner.get_best_value():.4f}")
        logger.info("=" * 80)
        
        # Redis 발행
        if redis_client and args.publish_redis:
            publish_to_redis(redis_client, "fa", env, run_id, best_params)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 튜닝 사이클 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Ensemble 파라미터 튜닝 자동 루프")
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="튜닝 간격 (초, 기본: 3600 = 1시간)"
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=3,
        help="Optuna trials 수 (기본: 3)"
    )
    parser.add_argument(
        "--window",
        type=float,
        default=24,
        help="실험 윈도우 시간 (기본: 24)"
    )
    parser.add_argument(
        "--storage",
        type=str,
        default=None,
        help="Optuna storage URL (기본: PostgreSQL from env)"
    )
    parser.add_argument(
        "--base-config",
        type=str,
        default="config.yml",
        help="베이스 설정 파일 (기본: config.yml)"
    )
    parser.add_argument(
        "--publish-redis",
        action="store_true",
        help="Redis로 파라미터 발행 (기본: False)"
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=0,
        help="최대 사이클 수 (0 = 무한, 기본: 0)"
    )
    
    args = parser.parse_args()
    
    # Redis 클라이언트 초기화 (선택)
    redis_client = None
    if args.publish_redis:
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            redis_client = redis.from_url(redis_url)
            logger.info(f"✅ Redis 연결: {redis_url}")
        except Exception as e:
            logger.warning(f"⚠️ Redis 연결 실패: {e}")
    
    logger.info("=" * 80)
    logger.info("🚀 튜닝 자동 루프 시작")
    logger.info("=" * 80)
    logger.info(f"간격: {args.interval}초")
    logger.info(f"Trials: {args.trials}")
    logger.info(f"Window: {args.window}시간")
    logger.info(f"Max Cycles: {'무한' if args.max_cycles == 0 else args.max_cycles}")
    logger.info(f"Redis 발행: {'활성화' if args.publish_redis else '비활성화'}")
    logger.info("=" * 80)
    
    cycle_count = 0
    
    try:
        while True:
            cycle_count += 1
            logger.info(f"\n🔄 사이클 #{cycle_count} 시작")
            
            # 튜닝 실행
            success = run_tuning_cycle(args, redis_client)
            
            if success:
                logger.info(f"✅ 사이클 #{cycle_count} 완료")
            else:
                logger.error(f"❌ 사이클 #{cycle_count} 실패")
            
            # 최대 사이클 체크
            if args.max_cycles > 0 and cycle_count >= args.max_cycles:
                logger.info(f"🏁 최대 사이클 도달 ({args.max_cycles})")
                break
            
            # 대기
            logger.info(f"⏳ {args.interval}초 대기 중...")
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        logger.info("\n🛑 사용자 중단")
    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    logger.info("=" * 80)
    logger.info(f"🎉 튜닝 자동 루프 종료 (총 {cycle_count} 사이클)")
    logger.info("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
