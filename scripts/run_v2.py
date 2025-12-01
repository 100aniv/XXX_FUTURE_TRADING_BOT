#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE23-1: Single-Engine Thin Script Wrapper
=============================================
얇은 진입점: Config 로딩 + Adapters 생성 + Engine 호출만 담당

Usage:
    python scripts/run_v2.py --mode paper --config configs/paper/phase22_4_scalping_param_smoke_30m.yml --duration-hours 0.5
    python scripts/run_v2.py --mode backtest --config configs/backtest/base.yml

Design Principles (PHASE23-0 TO-BE Architecture):
    - Script은 orchestration 하지 않음
    - Strategy selection/loading은 엔진이 담당
    - Config는 SSOT로 유지 (script에서 수정 금지)
    - Mode-based adapter creation만 담당
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.logger import setup_logger
from common.config_loader import load_config_with_mode, generate_run_id

logger = setup_logger("run_v2")


def main():
    """메인 진입점"""
    parser = argparse.ArgumentParser(
        description='PHASE23-1: Single-Engine Trading Runner',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('--mode', type=str, required=True, choices=['paper', 'backtest', 'live'],
                        help='실행 모드')
    parser.add_argument('--config', type=str, required=True,
                        help='Config YAML 파일 경로')
    parser.add_argument('--duration-hours', type=float, default=None,
                        help='실행 시간 (hours, None=무제한)')
    parser.add_argument('--clean-state', action='store_true',
                        help='Redis/DB 상태 초기화 (PAPER/LIVE only)')
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info(f"🚀 PHASE23-1 Run V2 시작 - Mode: {args.mode.upper()}")
    logger.info("=" * 80)
    
    # 1. Config 로딩 (SSOT)
    try:
        import yaml
        
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
        
        # Deep merge: base에 custom 덮어쓰기
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
        config['mode'] = args.mode
        config['env'] = args.mode  # env 필드 명시적 설정
        
        # feed.base_timeframe 동기화 (WebSocket collector timeframe 버그 방지)
        if 'timeframe' in config:
            config.setdefault('feed', {})['base_timeframe'] = config['timeframe']
        
        logger.info(f"✅ Config 로딩 완료: {args.config}")
        logger.info(f"🆔 Run ID: {run_id}")
    except Exception as e:
        logger.error(f"❌ Config 로딩 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    # 2. Duration 설정 (CLI 우선, 없으면 config 사용)
    if args.duration_hours is not None:
        config['duration_hours'] = args.duration_hours
    
    # 3. Engine 호출 (Mode-based dispatch)
    from execution.engine import run_v2
    
    try:
        run_v2(
            mode=args.mode,
            config=config,
            clean_state=args.clean_state
        )
        
        logger.info("=" * 80)
        logger.info(f"✅ {args.mode.upper()} 실행 완료")
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
