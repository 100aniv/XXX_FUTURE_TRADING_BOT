#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE36-2 S6: Live Trading Thin Wrapper
========================================
REAL Live Mode용 얇은 래퍼 - engine.run_v2() 호출만 담당

Usage:
    python scripts/run_live.py --config configs/live/xxx.yml
    python scripts/run_live.py --config configs/live/xxx.yml --duration-hours 2
    python scripts/run_live.py --config configs/live/xxx.yml --clean-state

Design:
    - Config 로딩 + run_v2(mode='live') 호출만
    - 엔진 로직/전략 로딩/어댑터 생성은 engine이 담당
    - Shadow Mode 지원: execution.shadow_mode=true → 주문 제출 0
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

logger = setup_logger("run_live")


def parse_args():
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description='PHASE36-2 S6: Live Trading Thin Wrapper (run_v2 호출)',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--config',
        type=str,
        required=True,
        help='Config YAML 파일 경로 (예: configs/live/xxx.yml)'
    )
    
    parser.add_argument(
        '--duration-hours',
        type=float,
        default=None,
        help='실행 시간 (hours, None=config 또는 무제한)'
    )
    
    parser.add_argument(
        '--clean-state',
        action='store_true',
        help='Redis/DB 상태 초기화'
    )
    
    parser.add_argument(
        '--shadow',
        action='store_true',
        help='Shadow Mode 활성화 (주문 제출 0, 텔레메트리만)'
    )
    
    return parser.parse_args()


def main():
    """메인 진입점"""
    logger.info("=" * 80)
    logger.info("🚀 PHASE36-2 S6 Live Trading Thin Wrapper")
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
        config['mode'] = 'live'
        config['env'] = 'live'
        
        # feed.base_timeframe 동기화
        if 'timeframe' in config:
            config.setdefault('feed', {})['base_timeframe'] = config['timeframe']
        
        # Shadow Mode 설정 (CLI 우선)
        if args.shadow:
            config.setdefault('execution', {})['shadow_mode'] = True
            logger.warning("🔇 SHADOW MODE 활성화: 주문 제출 차단 (텔레메트리만)")
        
        logger.info(f"✅ Config 로딩 완료: {args.config}")
        logger.info(f"🆔 Run ID: {run_id}")
        logger.info(f"🔧 Mode: live {'(SHADOW)' if config.get('execution', {}).get('shadow_mode') else ''}")
        
    except Exception as e:
        logger.error(f"❌ Config 로딩 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    # 2. Duration 설정 (CLI 우선)
    if args.duration_hours is not None:
        config['duration_hours'] = args.duration_hours
    
    # 3. Engine 호출
    from execution.engine import run_v2
    
    try:
        run_v2(
            mode='live',
            config=config,
            clean_state=args.clean_state
        )
        
        logger.info("=" * 80)
        logger.info("✅ LIVE 실행 완료")
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
    sys.exit(main())
