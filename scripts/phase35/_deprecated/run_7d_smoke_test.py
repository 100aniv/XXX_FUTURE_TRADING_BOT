#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-2: 7-Day Smoke Test Runner
===================================

AC-BT0~BT3 검증을 위한 7일 백테스트 자동 실행

Usage:
    python scripts/phase35/run_7d_smoke_test.py [run_number]
"""
import sys
import yaml
from pathlib import Path
from datetime import datetime

# Project root 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger("run_7d_smoke_test")


def run_backtest(run_number: int = 1):
    """7일 스모크 테스트 실행"""
    logger.info("=" * 80)
    logger.info(f"PHASE35-2: 7-Day Smoke Test - Run #{run_number}")
    logger.info("=" * 80)
    logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Config 로딩
    try:
        # base.yml 로드
        base_config_path = project_root / "configs" / "base.yml"
        if base_config_path.exists():
            with open(base_config_path, 'r', encoding='utf-8') as f:
                base_cfg = yaml.safe_load(f)
        else:
            base_cfg = {}
            logger.warning("⚠️  base.yml 없음")
        
        # ensemble_v1.yaml 로드
        config_path = project_root / "configs" / "phase35" / "ensemble_v1.yaml"
        if not config_path.exists():
            logger.error(f"❌ Config not found: {config_path}")
            return 1
        
        with open(config_path, 'r', encoding='utf-8') as f:
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
        
        # Run ID 생성 (run_number 포함)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"phase35_7d_run{run_number}_{timestamp}"
        config['run_id'] = run_id
        config['mode'] = 'backtest'
        config['env'] = 'backtest'
        
        # Backtest 설정 (smoke_test 기준)
        smoke_cfg = config.get('backtest', {}).get('smoke_test', {})
        config['start_date'] = smoke_cfg.get('start_date', '2024-12-01')
        config['end_date'] = smoke_cfg.get('end_date', '2024-12-08')
        config['initial_capital'] = smoke_cfg.get('initial_capital', 10000)
        
        logger.info(f"✅ Config 로딩 완료")
        logger.info(f"🆔 Run ID: {run_id}")
        logger.info(f"📅 Period: {config['start_date']} ~ {config['end_date']}")
        logger.info(f"💰 Capital: ${config['initial_capital']}")
        
    except Exception as e:
        logger.error(f"❌ Config 로딩 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    # Engine 실행
    from execution.engine import run_v2
    
    try:
        run_v2(
            mode='backtest',
            config=config,
            clean_state=False
        )
        
        logger.info("=" * 80)
        logger.info(f"✅ Run #{run_number} 완료")
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


def main():
    """메인 함수"""
    # CLI 인자에서 run_number 가져오기
    run_number = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    
    exit_code = run_backtest(run_number)
    
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Exit Code: {exit_code}")
    logger.info("=" * 80)
    
    if exit_code == 0:
        logger.info("")
        logger.info("📊 Next Steps:")
        logger.info("1. Check results: reports/backtest/")
        logger.info("2. Review DecisionTrace")
        logger.info("3. Verify AC-BT0~BT3 criteria")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
