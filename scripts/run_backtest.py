#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE23-3: Backtest Thin Wrapper
=================================
Legacy CLI 호환용 얇은 래퍼 - engine.run_v2() 호출만 담당

Usage:
    python scripts/run_backtest.py --config configs/backtest/xxx.yml
    python scripts/run_backtest.py --config configs/backtest/xxx.yml --clean-state

Design:
    - Config 로딩 + run_v2(mode='backtest') 호출만
    - 엔진 로직/전략 로딩/어댑터 생성은 engine이 담당
    - 레거시 호환: 이전 CLI 인자는 미지원 (config 파일로 전환 권장)
"""
import sys
import argparse
import yaml
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.logger import setup_logger
from common.config_loader import generate_run_id

logger = setup_logger("run_backtest")


def parse_args():
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description='PHASE23-3: Backtest Thin Wrapper (run_v2 호출)',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--config',
        type=str,
        required=True,
        help='Config YAML 파일 경로 (예: configs/backtest/xxx.yml)'
    )
    
    parser.add_argument(
        '--clean-state',
        action='store_true',
        help='Redis/DB 상태 초기화'
    )
    
    return parser.parse_args()


def main():
    """메인 진입점"""
    logger.info("=" * 80)
    logger.info("🚀 PHASE23-3 Backtest Thin Wrapper")
    logger.info("=" * 80)
    
    args = parse_args()
    
    # 1. Config 로딩
    try:
        # base.yml 로드
        base_config_path = Path("configs/base.yml")
        if base_config_path.exists():
            with open(base_config_path, 'r', encoding='utf-8') as f:
                base_cfg = yaml.safe_load(f)
        else:
            base_cfg = {}
            logger.warning("⚠️  base.yml 없음, custom config만 사용")
        
        # custom config 로드
        with open(args.config, 'r', encoding='utf-8') as f:
            custom_cfg = yaml.safe_load(f)
        
        # Deep merge
        def deep_merge(base, custom):
            merged = base.copy()
            for key, value in custom.items():
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = deep_merge(merged[key], value)
                else:
                    merged[key] = value
            return merged
        
        config = deep_merge(base_cfg, custom_cfg)
        
        # Run ID & Mode 설정
        run_id = generate_run_id()
        config['run_id'] = run_id
        config['mode'] = 'backtest'
        config['env'] = 'backtest'
        
        logger.info(f"✅ Config 로딩 완료: {args.config}")
        logger.info(f"🆔 Run ID: {run_id}")
        
    except Exception as e:
        logger.error(f"❌ Config 로딩 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    # 2. Engine 호출
    from execution.engine import run_v2
    
    try:
        run_v2(
            mode='backtest',
            config=config,
            clean_state=args.clean_state
        )
        
        logger.info("=" * 80)
        logger.info("✅ BACKTEST 실행 완료")
        logger.info("=" * 80)
        return 0
        
    except KeyboardInterrupt:
        logger.warning("⚠️  사용자 중단")
        return 130
    except Exception as e:
        logger.error(f"❌ 실행 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    main()
