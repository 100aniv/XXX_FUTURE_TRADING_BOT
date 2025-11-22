#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE21-1A: Single Strategy Smoke Tests (1h each, 7 strategies)
===============================================================
Ensemble OFF, Paper Mode
Meaningfulness check based on trade delta
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

from scripts.trade_counter import (
    get_paper_trade_count,
    get_paper_trades_by_strategy,
)

# 전략 목록
STRATEGIES = [
    "scalping",
    "breakout",
    "reversion",
    "trend",
    "swing",
    "swing_bb",
    "daytrade",
]

# 의미 있는 거래 수 기준
MIN_MEANINGFUL_TRADES = 1  # 최소 1건 이상 거래 발생


def safe_print(msg):
    """안전한 출력"""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def run_clean_state():
    """Clean-State 초기화"""
    safe_print("\n[CLEAN] Running Clean-State...")
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    result = subprocess.run(
        [sys.executable, "scripts/phase20_clean_state.py"],
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


def run_single_strategy(strategy_name):
    """
    단일 전략 1시간 테스트
    Returns: dict with test results
    """
    safe_print(f"\n{'='*70}")
    safe_print(f"STRATEGY: {strategy_name.upper()}")
    safe_print(f"START: {datetime.now().strftime('%H:%M:%S')}")
    safe_print(f"{'='*70}")
    
    # 1. Clean-State
    if not run_clean_state():
        return {
            "strategy": strategy_name,
            "status": "FAILED",
            "reason": "Clean-State failed",
            "initial_trades": -1,
            "final_trades": -1,
            "delta": -1,
            "meaningful": False
        }
    
    # 2. Get initial count
    initial_count = get_paper_trade_count()
    safe_print(f"[COUNT] Initial: {initial_count} trades")
    
    # 3. Run paper trading
    config_path = f"configs/paper/phase21_{strategy_name}_solo.yml"
    cmd = [sys.executable, "scripts/run_paper.py", "--config", config_path]
    
    safe_print(f"[RUN] Config: {config_path}")
    safe_print(f"[RUN] Starting engine (1h wall-clock)...")
    
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
    
    # 4. Monitor first 5 minutes (300s) - per-minute
    safe_print("\n[MONITOR] First 5 minutes...")
    start_time = time.time()
    last_count = initial_count
    error_detected = False
    
    for minute in range(5):
        time.sleep(60)
        elapsed = int(time.time() - start_time)
        
        # Check process
        if process.poll() is not None:
            safe_print(f"[ERROR] Process died at {elapsed}s")
            error_detected = True
            break
        
        # Check trades
        current_count = get_paper_trade_count()
        delta = current_count - initial_count
        
        if current_count > last_count:
            safe_print(f"[{elapsed}s] Trade: {current_count} (delta: +{delta})")
            last_count = current_count
        else:
            safe_print(f"[{elapsed}s] Count: {current_count} (delta: {delta})")
    
    safe_print(f"[MONITOR] First 5min complete")
    
    if error_detected:
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()
        
        return {
            "strategy": strategy_name,
            "status": "FAILED",
            "reason": "Process died during first 5min",
            "initial_trades": initial_count,
            "final_trades": get_paper_trade_count(),
            "delta": get_paper_trade_count() - initial_count,
            "meaningful": False
        }
    
    # 5. Wait remaining time (55 min, check every 5 min)
    safe_print("[WAIT] Remaining 55 minutes...")
    for i in range(11):
        time.sleep(300)  # 5 minutes
        elapsed_total = int(time.time() - start_time)
        current_count = get_paper_trade_count()
        
        if process.poll() is not None:
            safe_print(f"[WARN] Process ended at {elapsed_total}s")
            break
        
        safe_print(f"[{elapsed_total}s / 3600s] Running... (trades: {current_count})")
    
    # 6. Final results
    final_count = get_paper_trade_count()
    delta = final_count - initial_count
    
    # Determine meaningfulness
    meaningful = (delta >= MIN_MEANINGFUL_TRADES)
    
    safe_print(f"\n{'='*70}")
    safe_print(f"COMPLETE: {strategy_name.upper()}")
    safe_print(f"END: {datetime.now().strftime('%H:%M:%S')}")
    safe_print(f"Initial: {initial_count} | Final: {final_count} | Delta: {delta}")
    safe_print(f"Meaningful: {'YES' if meaningful else 'NO'}")
    safe_print(f"{'='*70}")
    
    # Terminate process
    try:
        process.terminate()
        process.wait(timeout=10)
    except:
        try:
            process.kill()
        except:
            pass
    
    return {
        "strategy": strategy_name,
        "status": "PASS",
        "reason": None,
        "initial_trades": initial_count,
        "final_trades": final_count,
        "delta": delta,
        "meaningful": meaningful
    }


def main():
    """Main execution"""
    safe_print("\n" + "="*70)
    safe_print("PHASE21-1A: Single Strategy Smoke Tests")
    safe_print("="*70)
    safe_print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    safe_print(f"Strategies: {len(STRATEGIES)}")
    safe_print(f"Runtime per strategy: 1 hour")
    safe_print(f"Estimated total: {len(STRATEGIES)} hours")
    safe_print("="*70)
    
    results = []
    
    for idx, strategy in enumerate(STRATEGIES, 1):
        safe_print(f"\n[{idx}/{len(STRATEGIES)}] {strategy.upper()}")
        
        result = run_single_strategy(strategy)
        results.append(result)
        
        # Wait before next
        if idx < len(STRATEGIES):
            safe_print("\n[WAIT] 10s before next strategy...")
            time.sleep(10)
    
    # Summary
    safe_print("\n" + "="*70)
    safe_print("ALL TESTS COMPLETE")
    safe_print("="*70)
    safe_print(f"End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    safe_print("\nResults:")
    
    meaningful_count = 0
    for result in results:
        status = "PASS" if result['status'] == "PASS" else "FAIL"
        meaningful_str = "YES" if result['meaningful'] else "NO"
        delta = result['delta']
        
        safe_print(f"  [{status}] {result['strategy'].upper()}: delta={delta}, meaningful={meaningful_str}")
        
        if result['meaningful']:
            meaningful_count += 1
    
    safe_print(f"\nMeaningful tests: {meaningful_count}/{len(STRATEGIES)}")
    safe_print("="*70)
    
    # Save results to JSON
    results_file = project_root / "docs" / "PHASE21" / "phase21_1a_results.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    
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
