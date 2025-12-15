#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-2: 7D Smoke Test Runner (Automated)
- Loads config, runs 7D backtest with phase35_ensemble_v1
- Heartbeat output every 30 seconds
- Saves results to reports/backtest/phase35/
"""
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from execution.engine import run_v2
from common.logger import setup_logger
import yaml

logger = setup_logger('phase35_7d_smoke', log_type='application')


def load_config(config_path: str) -> dict:
    """Load and validate config"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Ensure required keys
    if 'lookback' not in config:
        config['lookback'] = 1000
    if 'equity' not in config:
        config['equity'] = 10000
    
    return config


def run_7d_smoke_test(run_number: int = 1):
    """
    Run 7D Smoke Test
    
    Args:
        run_number: Run number (1 or 2 for repeatability)
    """
    logger.info("=" * 80)
    logger.info(f"🚀 PHASE35-2: 7D Smoke Test RUN-{run_number}")
    logger.info("=" * 80)
    
    # Load config
    config_path = Path(__file__).parent.parent.parent / "configs" / "phase35" / "ensemble_v1.yaml"
    logger.info(f"📄 Loading config: {config_path}")
    config = load_config(str(config_path))
    
    # Generate run ID
    run_id = f"phase35_7d_run{run_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    config['run_id'] = run_id
    
    # Set 7D date range (from config backtest.smoke_test)
    smoke_config = config.get('backtest', {}).get('smoke_test', {})
    start_date = smoke_config.get('start_date', '2024-12-01')
    end_date = smoke_config.get('end_date', '2024-12-08')
    
    config['start_date'] = start_date
    config['end_date'] = end_date
    
    logger.info(f"🆔 Run ID: {run_id}")
    logger.info(f"📅 Date Range: {start_date} ~ {end_date}")
    logger.info(f"🎯 Strategy: phase35_ensemble_v1")
    logger.info("=" * 80)
    
    # Run backtest
    start_time = time.time()
    
    try:
        logger.info("🔥 Starting backtest...")
        
        # Call run_v2 engine
        run_v2(
            mode='backtest',
            config=config,
            clean_state=True
        )
        
        elapsed = time.time() - start_time
        logger.info("=" * 80)
        logger.info(f"✅ Backtest completed in {elapsed:.1f}s")
        logger.info(f"📊 Results saved to: reports/backtest/phase35/{run_id}/")
        logger.info("=" * 80)
        
        return run_id, elapsed
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error("=" * 80)
        logger.error(f"❌ Backtest FAILED after {elapsed:.1f}s")
        logger.error(f"Error: {e}")
        logger.error("=" * 80)
        raise


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        run_number = int(sys.argv[1])
    else:
        run_number = 1
    
    try:
        run_id, elapsed = run_7d_smoke_test(run_number)
        print(f"\n✅ SUCCESS: {run_id} completed in {elapsed:.1f}s\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ FAILED: {e}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
