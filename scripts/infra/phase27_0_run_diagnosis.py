#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE27-0: Trade Activity Diagnosis Runner
===========================================
Drop-off instrumentation을 활성화한 PAPER 실행

Usage:
    python scripts/infra/phase27_0_run_diagnosis.py \
        --config configs/paper/phase27_0_single_symbol_30m.yml \
        --output docs/PHASE27/phase27_0_single_symbol_30m_summary.json
"""

import os
import sys
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

import yaml
from common.logger import setup_logger
from metrics.trade_activity_tracker import TradeActivityTracker

logger = setup_logger(__name__, log_type="application")


def run_preflight_checks() -> bool:
    """
    Pre-flight 체크: DB/Redis/Env 진단
    
    Returns:
        bool: 모든 체크 통과 시 True
    """
    print("\n" + "=" * 80)
    print("  [STEP 1] Pre-flight Checks")
    print("=" * 80)
    
    # 1) Env Config Validator
    print("\n[1/2] Environment & Config Validation...")
    validator_script = project_root / "scripts" / "infra" / "env_config_validator.py"
    
    if validator_script.exists():
        result = subprocess.run(
            [sys.executable, str(validator_script)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"  [✗] Env/Config validation FAILED")
            if result.stderr:
                print(f"      Error: {result.stderr[:500]}")
            return False
        print(f"  [✓] Env/Config validation PASSED")
    else:
        print(f"  [⚠] Validator script not found, skipping...")
    
    # 2) Infra Diagnostics (DB/Redis/Engine)
    print("\n[2/2] Infrastructure Diagnostics (DB/Redis/Engine)...")
    diag_script = project_root / "scripts" / "infra" / "phase24_1_infra_diagnostics.py"
    
    if diag_script.exists():
        result = subprocess.run(
            [sys.executable, str(diag_script)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"  [✗] Infra diagnostics FAILED")
            if result.stderr:
                print(f"      Error: {result.stderr[:500]}")
            return False
        print(f"  [✓] Infra diagnostics PASSED")
    else:
        print(f"  [⚠] Diagnostics script not found, skipping...")
    
    print("\n" + "=" * 80)
    print("  [✓] Pre-flight Checks: ALL PASSED")
    print("=" * 80)
    
    return True


def run_clean_state() -> bool:
    """
    Clean state: DB/Redis 초기화
    
    Returns:
        bool: 성공 시 True
    """
    print("\n" + "=" * 80)
    print("  [STEP 2] Clean State")
    print("=" * 80)
    
    clean_script = project_root / "scripts" / "ops" / "clean_state_complete.py"
    
    if not clean_script.exists():
        print(f"  [⚠] Clean state script not found, skipping...")
        return True
    
    print("\nCleaning Redis/DB state...")
    result = subprocess.run(
        [sys.executable, str(clean_script)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"  [✗] Clean state FAILED")
        if result.stderr:
            print(f"      Error: {result.stderr[:500]}")
        return False
    
    print(f"  [✓] Clean state PASSED")
    print("=" * 80)
    
    return True


def run_paper_with_tracker(config_path: Path, output_json: Path) -> bool:
    """
    PAPER 실행 (activity_tracker 활성화)
    
    Args:
        config_path: Config 파일 경로
        output_json: 출력 JSON 경로
    
    Returns:
        bool: 성공 시 True
    """
    print("\n" + "=" * 80)
    print("  [STEP 3] Run PAPER with Activity Tracker")
    print("=" * 80)
    
    # Config 로드
    print(f"\nLoading config: {config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    run_id = config.get('run_id', 'phase27_0_test')
    duration_hours = config.get('paper', {}).get('duration_hours', 0.5)
    
    print(f"  Run ID: {run_id}")
    print(f"  Duration: {duration_hours:.2f} hours ({duration_hours * 60:.0f} minutes)")
    
    # TradeActivityTracker 생성
    tracker = TradeActivityTracker(
        run_id=run_id,
        duration_minutes=duration_hours * 60
    )
    
    print(f"\n  [✓] TradeActivityTracker initialized")
    
    # 엔진 실행 (간단 버전 - run_paper.py 로직 재사용)
    try:
        # Feed, Broker, Clock 생성
        from execution.adapters import create_adapters
        from execution.engine import run
        from strategies import load_strategies
        
        print("\nInitializing components...")
        
        # 1) Determine symbols
        symbols_list = []
        if config.get('universe', {}).get('enabled'):
            from common.universe_provider import load_universe
            symbols_list = load_universe(config)
            print(f"  [✓] Universe loaded: {len(symbols_list)} symbols")
        else:
            symbol = config.get('symbol', 'BTCUSDT')
            symbols_list = [symbol]
            print(f"  [✓] Single symbol: {symbol}")
        
        # 2) Create adapters (Feed, Broker, Clock)
        mode = config.get('mode', 'paper')
        feed, broker, clock = create_adapters(mode, symbols_list, config, logger)
        print("  [✓] Feed, Broker, Clock created")
        
        # 3) Strategies
        strategies_dict = load_strategies(config)
        print(f"  [✓] Strategies loaded: {list(strategies_dict.keys())}")
        
        # 4) Ensemble (if enabled)
        ensemble_module = None
        if config.get('ensemble', {}).get('enabled'):
            from strategies import ensemble as ensemble_mod
            ensemble_module = ensemble_mod
            print("  [✓] Ensemble module loaded")
        
        print("\n" + "=" * 80)
        print(f"  [🚀] Starting PAPER run ({duration_hours * 60:.0f} minutes)...")
        print("=" * 80)
        
        start_time = time.time()
        
        # ⭐ PHASE27-0: activity_tracker 전달
        run(
            feed=feed,
            broker=broker,
            clock=clock,
            strategies=strategies_dict,
            ensemble_module=ensemble_module,
            config=config,
            symbols=symbols_list if config.get('universe', {}).get('enabled') else None,
            activity_tracker=tracker  # ⭐ PHASE27-0: Drop-off instrumentation
        )
        
        elapsed_time = time.time() - start_time
        tracker.set_duration(elapsed_time / 60)
        
        print("\n" + "=" * 80)
        print(f"  [✓] PAPER run completed ({elapsed_time / 60:.2f} minutes)")
        print("=" * 80)
        
        # Summary 출력
        summary = tracker.get_summary()
        print("\n[Activity Summary]")
        print(f"  Strategy Signals (True): {summary['totals']['strategy_signals_true']}")
        print(f"  Ensemble Tier1: {summary['totals']['ensemble_tier1']}")
        print(f"  Ensemble Tier2: {summary['totals']['ensemble_tier2']}")
        print(f"  Ensemble Skip: {summary['totals']['ensemble_skip']}")
        print(f"  Guard Blocks: {summary['totals']['guard_blocks_total']}")
        print(f"  Orders Submitted: {summary['totals']['orders_submitted']}")
        
        # Survival rate
        survival = tracker.get_signal_survival_rate()
        if survival:
            print(f"\n[Signal Survival Rate]")
            if 'ensemble_survival_rate' in survival:
                print(f"  Strategy → Ensemble: {survival['ensemble_survival_rate']:.1%}")
            if 'guard_survival_rate' in survival:
                print(f"  Ensemble → Guard: {survival['guard_survival_rate']:.1%}")
            if 'order_submission_rate' in survival:
                print(f"  Guard → Order: {survival['order_submission_rate']:.1%}")
        
        # JSON 저장
        print(f"\nSaving results to: {output_json}")
        tracker.save_json(output_json)
        print(f"  [✓] Results saved")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ PAPER run failed: {e}", exc_info=True)
        print(f"\n  [✗] PAPER run FAILED: {e}")
        return False


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='PHASE27-0: Trade Activity Diagnosis Runner'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        required=True,
        help='Config file path'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Output JSON path'
    )
    
    parser.add_argument(
        '--skip-preflight',
        action='store_true',
        help='Skip pre-flight checks (for debugging)'
    )
    
    args = parser.parse_args()
    
    config_path = Path(args.config)
    output_json = Path(args.output)
    
    print("\n" + "=" * 80)
    print("  PHASE27-0: Trade Activity Diagnosis Runner")
    print("=" * 80)
    print(f"  Config: {config_path}")
    print(f"  Output: {output_json}")
    print(f"  Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # STEP 1: Pre-flight checks
    if not args.skip_preflight:
        if not run_preflight_checks():
            print("\n[FAILED] Pre-flight checks failed. Aborting.")
            sys.exit(1)
    else:
        print("\n[SKIPPED] Pre-flight checks (--skip-preflight flag)")
    
    # STEP 2: Clean state
    if not run_clean_state():
        print("\n[FAILED] Clean state failed. Aborting.")
        sys.exit(1)
    
    # STEP 3: Run PAPER with tracker
    if not run_paper_with_tracker(config_path, output_json):
        print("\n[FAILED] PAPER run failed.")
        sys.exit(1)
    
    # Success
    print("\n" + "=" * 80)
    print("  [✓] PHASE27-0 Diagnosis Run: SUCCESS")
    print("=" * 80)
    print(f"  End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
