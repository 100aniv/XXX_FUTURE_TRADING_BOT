#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE21-1A: Strategy Execution & Report Generation
===================================================
7 strategies x 15-minute quick tests
Auto report generation and PHASE_ROADMAP update
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

# Strategy configurations
STRATEGIES = [
    {"name": "scalping", "timeframe": "3m", "expected_frequency": "high"},
    {"name": "breakout", "timeframe": "15m", "expected_frequency": "low"},
    {"name": "reversion", "timeframe": "5m", "expected_frequency": "medium"},
    {"name": "trend", "timeframe": "1h", "expected_frequency": "very_low"},
    {"name": "swing", "timeframe": "1h", "expected_frequency": "very_low"},
    {"name": "swing_bb", "timeframe": "5m", "expected_frequency": "low"},
    {"name": "daytrade", "timeframe": "15m", "expected_frequency": "medium"},
]

TEST_DURATION_MINUTES = 15  # Quick test per strategy
MONITOR_INTERVAL_SEC = 60   # Check every minute


def safe_print(msg):
    """Windows console safe print"""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def run_clean_state():
    """Execute Clean-State"""
    safe_print("\n[CLEAN] Running Clean-State...")
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    result = subprocess.run(
        [sys.executable, "scripts/clean_state_complete.py"],
        cwd=project_root,
        capture_output=True,
        env=env
    )
    
    if result.returncode == 0:
        safe_print("[CLEAN] OK")
        return True
    else:
        safe_print(f"[CLEAN] FAILED")
        return False


def test_strategy(strategy_name, timeframe):
    """
    Test single strategy for 15 minutes
    
    Returns:
        dict: Test result
    """
    safe_print(f"\n{'='*70}")
    safe_print(f"STRATEGY: {strategy_name.upper()} ({timeframe})")
    safe_print(f"START: {datetime.now().strftime('%H:%M:%S')}")
    safe_print(f"{'='*70}")
    
    # Clean-State
    if not run_clean_state():
        return {
            "strategy": strategy_name,
            "timeframe": timeframe,
            "status": "FAILED",
            "reason": "Clean-State failed",
            "trades": 0
        }
    
    # Initial count
    test_start = datetime.now()
    initial_count = count_paper_trades(strategy_id=strategy_name, since=test_start)
    safe_print(f"[COUNT] Initial: {initial_count}")
    
    # Config
    config_path = project_root / "configs" / "paper" / f"phase21_{strategy_name}_solo.yml"
    if not config_path.exists():
        return {
            "strategy": strategy_name,
            "timeframe": timeframe,
            "status": "FAILED",
            "reason": "Config not found",
            "trades": 0
        }
    
    # Run engine
    cmd = [sys.executable, "scripts/run_paper.py", "--config", str(config_path)]
    safe_print(f"[RUN] Starting ({TEST_DURATION_MINUTES}min)...")
    
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    process = subprocess.Popen(
        cmd,
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1,
        env=env
    )
    
    # Monitor
    start_time = time.time()
    max_runtime = TEST_DURATION_MINUTES * 60
    last_count = initial_count
    
    while (time.time() - start_time) < max_runtime:
        # Check process alive
        if process.poll() is not None:
            safe_print(f"[INFO] Process ended early")
            break
        
        # Wait
        time.sleep(MONITOR_INTERVAL_SEC)
        elapsed = int(time.time() - start_time)
        
        # Check trades
        current_count = count_paper_trades(strategy_id=strategy_name, since=test_start)
        delta = current_count - initial_count
        
        if current_count > last_count:
            safe_print(f"[{elapsed}s] Trade: {current_count} (delta: +{delta})")
            last_count = current_count
        else:
            safe_print(f"[{elapsed}s] Count: {current_count} (delta: {delta})")
    
    # Final count
    final_count = count_paper_trades(strategy_id=strategy_name, since=test_start)
    delta = final_count - initial_count
    stats = get_paper_trade_stats(strategy_id=strategy_name, since=test_start)
    
    # Terminate
    try:
        process.terminate()
        process.wait(timeout=10)
    except:
        try:
            process.kill()
        except:
            pass
    
    # Determine status
    if delta >= 1:
        status = "OK"
        reason = f"{delta} trades in {TEST_DURATION_MINUTES}min"
    else:
        status = "NOT_MEANINGFUL"
        reason = f"0 trades in {TEST_DURATION_MINUTES}min (may need longer test or different market conditions)"
    
    safe_print(f"\n[RESULT] {strategy_name.upper()}: {status} ({delta} trades)")
    safe_print(f"{'='*70}")
    
    return {
        "strategy": strategy_name,
        "timeframe": timeframe,
        "status": status,
        "reason": reason,
        "trades": delta,
        "stats": stats,
        "test_duration_min": TEST_DURATION_MINUTES,
        "start_time": test_start.isoformat(),
        "end_time": datetime.now().isoformat()
    }


def main():
    """Main execution"""
    safe_print("\n" + "="*70)
    safe_print("PHASE21-1A: Single Strategy Tests (15min Quick)")
    safe_print("="*70)
    safe_print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    safe_print(f"Strategies: {len(STRATEGIES)}")
    safe_print(f"Duration per strategy: {TEST_DURATION_MINUTES} minutes")
    safe_print(f"Estimated total: {len(STRATEGIES) * TEST_DURATION_MINUTES} minutes (~{len(STRATEGIES) * TEST_DURATION_MINUTES // 60}h)")
    safe_print("="*70)
    
    results = []
    
    for idx, strat in enumerate(STRATEGIES, 1):
        safe_print(f"\n[{idx}/{len(STRATEGIES)}] {strat['name'].upper()}")
        
        result = test_strategy(strat['name'], strat['timeframe'])
        result['expected_frequency'] = strat['expected_frequency']
        results.append(result)
        
        # Wait before next
        if idx < len(STRATEGIES):
            safe_print("\n[WAIT] 10s...")
            time.sleep(10)
    
    # Summary
    safe_print("\n" + "="*70)
    safe_print("ALL TESTS COMPLETE")
    safe_print("="*70)
    safe_print(f"End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    safe_print("\nResults Summary:")
    
    ok_count = 0
    for result in results:
        status = result['status']
        trades = result['trades']
        
        safe_print(f"  [{status}] {result['strategy'].upper()}: {trades} trades ({result['timeframe']})")
        
        if status == "OK":
            ok_count += 1
    
    safe_print(f"\nMeaningful strategies: {ok_count}/{len(STRATEGIES)}")
    safe_print("="*70)
    
    # Save results
    docs_dir = project_root / "docs" / "PHASE21"
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = docs_dir / "phase21_1a_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    safe_print(f"\nResults saved to: {results_file}")
    
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
