#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE21-1A: Quick Test (5 minutes per strategy)
================================================
하네스 검증용 빠른 테스트
"""
import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime
import json
import yaml

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.trade_counter_v2 import count_paper_trades, get_paper_trade_stats

# Quick test constants
STRATEGIES = ["scalping", "breakout"]  # Only 2 strategies for quick test
RUNTIME_PER_STRATEGY_MIN = 5  # 5 minutes
WARMUP_MINUTES = 2
CHECK_INTERVAL_WARMUP = 60
MIN_TRADES_THRESHOLD = 0  # Allow 0 for quick test


def safe_print(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def run_clean_state():
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
        safe_print(f"[CLEAN] FAILED (code: {result.returncode})")
        return False


def run_single_strategy(strategy_name: str) -> dict:
    safe_print(f"\n{'='*70}")
    safe_print(f"STRATEGY: {strategy_name.upper()} (QUICK TEST: {RUNTIME_PER_STRATEGY_MIN}min)")
    safe_print(f"START: {datetime.now().strftime('%H:%M:%S')}")
    safe_print(f"{'='*70}")
    
    # Clean-State
    if not run_clean_state():
        return {"strategy": strategy_name, "status": "FAILED", "reason": "Clean-State failed"}
    
    # Initial count
    test_start_time = datetime.now()
    initial_count = count_paper_trades(strategy_id=strategy_name, since=test_start_time)
    safe_print(f"[COUNT] Initial: {initial_count}")
    
    # Config
    config_path = project_root / "configs" / "paper" / f"phase21_{strategy_name}_solo.yml"
    if not config_path.exists():
        return {"strategy": strategy_name, "status": "FAILED", "reason": "Config not found"}
    
    safe_print(f"[CONFIG] {config_path}")
    
    # Run engine
    cmd = [sys.executable, "scripts/run_paper.py", "--config", str(config_path)]
    safe_print(f"[RUN] Starting...")
    
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
    
    # Monitor warmup
    safe_print(f"\n[MONITOR] Warmup {WARMUP_MINUTES}min...")
    start_time = time.time()
    
    for minute in range(WARMUP_MINUTES):
        time.sleep(CHECK_INTERVAL_WARMUP)
        elapsed = int(time.time() - start_time)
        
        if process.poll() is not None:
            safe_print(f"[WARN] Process ended at {elapsed}s")
            break
        
        current_count = count_paper_trades(strategy_id=strategy_name, since=test_start_time)
        delta = current_count - initial_count
        safe_print(f"[{elapsed}s] Count: {current_count} (delta: {delta})")
    
    safe_print(f"[MONITOR] Warmup complete")
    
    # Wait remaining time
    remaining = (RUNTIME_PER_STRATEGY_MIN * 60) - (time.time() - start_time)
    if remaining > 0:
        safe_print(f"[WAIT] {int(remaining)}s...")
        time.sleep(remaining)
    
    # Final count
    final_count = count_paper_trades(strategy_id=strategy_name, since=test_start_time)
    delta = final_count - initial_count
    
    safe_print(f"\n[RESULT] Delta: {delta} trades")
    
    # Terminate
    try:
        process.terminate()
        process.wait(timeout=5)
    except:
        try:
            process.kill()
        except:
            pass
    
    return {
        "strategy": strategy_name,
        "status": "PASS" if delta >= MIN_TRADES_THRESHOLD else "NOT_MEANINGFUL",
        "initial_trades": initial_count,
        "final_trades": final_count,
        "delta": delta,
        "meaningful": delta >= MIN_TRADES_THRESHOLD
    }


def main():
    safe_print("\n" + "="*70)
    safe_print("PHASE21-1A: Quick Test (5min per strategy)")
    safe_print("="*70)
    safe_print(f"Strategies: {STRATEGIES}")
    safe_print(f"Runtime: {RUNTIME_PER_STRATEGY_MIN} minutes each")
    safe_print("="*70)
    
    results = []
    
    for idx, strategy in enumerate(STRATEGIES, 1):
        safe_print(f"\n[{idx}/{len(STRATEGIES)}] {strategy.upper()}")
        result = run_single_strategy(strategy)
        results.append(result)
        
        if idx < len(STRATEGIES):
            safe_print("\n[WAIT] 10s...")
            time.sleep(10)
    
    # Summary
    safe_print("\n" + "="*70)
    safe_print("QUICK TEST COMPLETE")
    safe_print("="*70)
    
    for result in results:
        safe_print(f"  [{result['status']}] {result['strategy'].upper()}: delta={result['delta']}")
    
    safe_print("\n[INFO] Quick test validates harness functionality")
    safe_print("[INFO] For full test, run: python scripts/phase21_1a_harness.py")
    safe_print("="*70)
    
    return results


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        safe_print("\n\nInterrupted")
        sys.exit(1)
