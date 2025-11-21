#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE21-1C: 7-Strategy Single-Strategy Tests (15min Each)
==========================================================
Validates each strategy independently with correct timeframes
"""
import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.trade_counter_v2 import count_paper_trades, get_paper_trade_stats

# Strategy configurations with correct timeframes
STRATEGIES = [
    {"name": "scalping", "timeframe": "3m", "expected": "high"},
    {"name": "breakout", "timeframe": "15m", "expected": "low"},
    {"name": "reversion", "timeframe": "5m", "expected": "medium"},
    {"name": "trend", "timeframe": "1h", "expected": "very_low"},
    {"name": "swing", "timeframe": "1h", "expected": "very_low"},
    {"name": "swing_bb", "timeframe": "5m", "expected": "low"},
    {"name": "daytrade", "timeframe": "15m", "expected": "medium"},
]

TEST_DURATION_MIN = 15  # Quick validation per strategy


def safe_print(msg):
    try:
        print(msg)
    except:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def run_clean_state():
    """Execute clean-state"""
    safe_print("[CLEAN] Running clean-state...")
    result = subprocess.run(
        [sys.executable, "scripts/clean_state_complete.py"],
        cwd=project_root,
        capture_output=True,
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    )
    return result.returncode == 0


def test_strategy(strategy_name, timeframe):
    """
    Test single strategy for 15 minutes
    
    Returns:
        dict: Test result with trades, status, stats
    """
    safe_print(f"\n{'='*70}")
    safe_print(f"STRATEGY: {strategy_name.upper()} ({timeframe}) - {TEST_DURATION_MIN}min")
    safe_print(f"START: {datetime.now().strftime('%H:%M:%S')}")
    safe_print(f"{'='*70}")
    
    # Clean-State
    if not run_clean_state():
        return {
            "strategy": strategy_name,
            "timeframe": timeframe,
            "status": "CLEAN_FAILED",
            "trades": 0
        }
    
    # Record start time & initial trade count
    test_start = datetime.now()
    initial_count = count_paper_trades(strategy_id=strategy_name, since=test_start)
    
    # Use existing solo config (already updated with correct timeframes)
    config_path = project_root / "configs" / "paper" / f"phase21_{strategy_name}_solo.yml"
    if not config_path.exists():
        return {
            "strategy": strategy_name,
            "timeframe": timeframe,
            "status": "CONFIG_NOT_FOUND",
            "trades": 0
        }
    
    # Modify duration to 15min (override in command)
    safe_print(f"[CONFIG] Using: {config_path}")
    
    # Run paper test
    cmd = [
        sys.executable,
        "scripts/run_paper.py",
        "--config", str(config_path),
        "--duration-hours", str(TEST_DURATION_MIN / 60.0)  # 15min = 0.25h
    ]
    
    safe_print(f"[RUN] Starting {strategy_name} (timeframe={timeframe})...")
    
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    
    process = subprocess.Popen(
        cmd,
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        env=env
    )
    
    # Monitor test execution
    start_time = time.time()
    max_runtime = TEST_DURATION_MIN * 60
    last_count = initial_count
    monitor_interval = 60  # Check every minute
    
    while (time.time() - start_time) < max_runtime:
        # Check if process ended early
        if process.poll() is not None:
            safe_print(f"[INFO] Process ended early")
            break
        
        # Wait
        time.sleep(monitor_interval)
        elapsed = int(time.time() - start_time)
        
        # Check trade count
        current_count = count_paper_trades(strategy_id=strategy_name, since=test_start)
        delta = current_count - initial_count
        
        if current_count > last_count:
            safe_print(f"[{elapsed}s] Trades: {current_count} (delta: +{delta})")
            last_count = current_count
        else:
            safe_print(f"[{elapsed}s] Monitoring... (delta: {delta})")
    
    # Get final results
    final_count = count_paper_trades(strategy_id=strategy_name, since=test_start)
    delta = final_count - initial_count
    stats = get_paper_trade_stats(strategy_id=strategy_name, since=test_start)
    
    # Terminate process
    try:
        process.terminate()
        process.wait(timeout=10)
    except:
        try:
            process.kill()
        except:
            pass
    
    # Classify result
    if delta >= 5:
        status = "ACTIVE"
        reason = f"{delta} trades in {TEST_DURATION_MIN}min"
    elif delta >= 1:
        status = "LOW_FREQ"
        reason = f"{delta} trades (may be viable with longer timeframes)"
    else:
        status = "NO_TRADES"
        reason = f"0 trades in {TEST_DURATION_MIN}min (check config/market/conditions)"
    
    safe_print(f"\n[RESULT] {strategy_name.upper()}: {status} ({delta} trades)")
    safe_print(f"{'='*70}")
    
    return {
        "strategy": strategy_name,
        "timeframe": timeframe,
        "status": status,
        "reason": reason,
        "trades": delta,
        "stats": stats,
        "test_duration_min": TEST_DURATION_MIN,
        "start_time": test_start.isoformat(),
        "end_time": datetime.now().isoformat()
    }


def main():
    """Main execution"""
    safe_print("\n" + "="*70)
    safe_print("PHASE21-1C: Single Strategy Validation Tests")
    safe_print("="*70)
    safe_print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    safe_print(f"Strategies: {len(STRATEGIES)}")
    safe_print(f"Duration per strategy: {TEST_DURATION_MIN} minutes")
    safe_print(f"Estimated total: {len(STRATEGIES) * TEST_DURATION_MIN} minutes (~{len(STRATEGIES) * TEST_DURATION_MIN // 60}h {len(STRATEGIES) * TEST_DURATION_MIN % 60}m)")
    safe_print("="*70)
    
    results = []
    
    for idx, strat in enumerate(STRATEGIES, 1):
        safe_print(f"\n[{idx}/{len(STRATEGIES)}] Testing: {strat['name'].upper()}")
        
        result = test_strategy(strat['name'], strat['timeframe'])
        result['expected_frequency'] = strat['expected']
        results.append(result)
        
        # Brief pause between strategies
        if idx < len(STRATEGIES):
            safe_print("\n[WAIT] 10s before next strategy...")
            time.sleep(10)
    
    # Summary
    safe_print("\n" + "="*70)
    safe_print("ALL TESTS COMPLETE")
    safe_print("="*70)
    safe_print(f"End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    safe_print("\nResults Summary:")
    
    active_count = 0
    low_freq_count = 0
    no_trades_count = 0
    
    for result in results:
        status = result['status']
        trades = result['trades']
        tf = result['timeframe']
        
        safe_print(f"  [{status}] {result['strategy'].upper()} ({tf}): {trades} trades")
        
        if status == "ACTIVE":
            active_count += 1
        elif status == "LOW_FREQ":
            low_freq_count += 1
        elif status == "NO_TRADES":
            no_trades_count += 1
    
    safe_print(f"\nClassification:")
    safe_print(f"  ACTIVE: {active_count}/{len(STRATEGIES)}")
    safe_print(f"  LOW_FREQ: {low_freq_count}/{len(STRATEGIES)}")
    safe_print(f"  NO_TRADES: {no_trades_count}/{len(STRATEGIES)}")
    safe_print("="*70)
    
    # Save results to JSON
    docs_dir = project_root / "docs" / "PHASE21"
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = docs_dir / "phase21_1c_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    safe_print(f"\nResults saved: {results_file}")
    
    return results


if __name__ == "__main__":
    try:
        results = main()
        sys.exit(0)
    except KeyboardInterrupt:
        safe_print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        safe_print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
