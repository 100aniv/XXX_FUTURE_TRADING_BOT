#!/usr/bin/env python
"""
튜닝 실행 스크립트 (Phase 1.5)

Usage:
    python scripts/run_tuner.py --trials 3 --window 24

참조:
    - PR13_ARCHITECTURE_DESIGN.md (2.2 EnsembleTuner)
    - PR13_MASTER_PLAN.md (Phase 1.5)
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime
import uuid

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tuning.config_overlay import ConfigOverlay
from tuning.ensemble_tuner import EnsembleTuner
from common.logger import logger


def main():
    parser = argparse.ArgumentParser(description="Ensemble 파라미터 튜닝 실행")
    parser.add_argument(
        "--trials",
        type=int,
        default=3,
        help="Optuna trials 수 (기본: 3)"
    )
    parser.add_argument(
        "--window",
        type=float,
        default=24.0,
        help="실험 윈도우 시간 (기본: 24.0, 소수점 가능)"
    )
    parser.add_argument(
        "--study-name",
        type=str,
        default=None,
        help="Optuna study 이름 (기본: ensemble_tuning_YYYYMMDD_HHMMSS)"
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
    
    args = parser.parse_args()
    
    # Study 이름 생성
    if args.study_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.study_name = f"ensemble_tuning_{timestamp}"
    
    # Storage URL 설정 (PostgreSQL 단일 DB 정책)
    if args.storage is None:
        args.storage = os.getenv(
            "DATABASE_URL",
            "postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db"
        )
    
    # run_id 생성 (데이터 분리 정책)
    run_id = str(uuid.uuid4())
    env = "tuner"
    
    logger.info("=" * 80)
    logger.info("🚀 Ensemble 파라미터 튜닝 시작")
    logger.info("=" * 80)
    logger.info(f"Study 이름: {args.study_name}")
    logger.info(f"Trials: {args.trials}")
    logger.info(f"Window: {args.window}시간")
    logger.info(f"Storage: {args.storage}")
    logger.info(f"Base Config: {args.base_config}")
    logger.info(f"Env: {env}")
    logger.info(f"Run ID: {run_id}")
    logger.info("=" * 80)
    
    try:
        # ConfigOverlay 초기화
        logger.info("📝 ConfigOverlay 초기화...")
        config_overlay = ConfigOverlay(
            base_config_path=args.base_config,
            namespace="fa",
            env=env,
            run_id=run_id
        )
        logger.info("✅ ConfigOverlay 초기화 완료")
        
        # EnsembleTuner 초기화
        logger.info("🔧 EnsembleTuner 초기화...")
        tuner = EnsembleTuner(
            study_name=args.study_name,
            storage=args.storage,
            window_hours=args.window,
            config_overlay=config_overlay
        )
        logger.info("✅ EnsembleTuner 초기화 완료")
        
        # 최적화 실행
        logger.info(f"🎯 최적화 시작 ({args.trials} trials)...")
        best_params = tuner.optimize(n_trials=args.trials)
        
        logger.info("=" * 80)
        logger.info("✅ 최적화 완료!")
        logger.info("=" * 80)
        logger.info(f"📊 Best 파라미터:")
        for key, value in best_params.items():
            if isinstance(value, float):
                logger.info(f"  - {key}: {value:.4f}")
            else:
                logger.info(f"  - {key}: {value}")
        
        logger.info(f"📈 Best 값: {tuner.get_best_value():.4f}")
        logger.info("=" * 80)
        
        # 오버레이 파일 확인
        overlay_dir = project_root / "configs" / "overlays"
        overlay_files = list(overlay_dir.glob(f"*{args.study_name}*.yml"))
        if overlay_files:
            logger.info(f"✅ 오버레이 파일 생성 확인:")
            for f in overlay_files:
                logger.info(f"  - {f.name}")
        else:
            logger.warning("⚠️ 오버레이 파일이 생성되지 않았습니다.")
        
        logger.info("=" * 80)
        logger.info("🎉 튜닝 실행 완료!")
        logger.info("=" * 80)
        
        return 0
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ 튜닝 실행 실패: {e}")
        logger.error("=" * 80)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
