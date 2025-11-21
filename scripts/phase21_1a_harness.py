#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE21-1A: Single Strategy Smoke Test Harness
===============================================
7개 전략 1시간 스모크 테스트 (Ensemble OFF)
의미 있는 테스트만 진행 (조기 종료 로직 포함)

Acceptance Criteria:
- 최소 1건 이상 거래 발생
- 가드/리스크/포트폴리오 정상 동작
- 에러/Traceback 없음
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

# Constants
STRATEGIES = [
    "scalping",
    "breakout",
    "reversion",
    "trend",
    "swing",
    "swing_bb",
    "daytrade",
]

RUNTIME_PER_STRATEGY_MIN = 60
WARMUP_MINUTES = 5
CHECK_INTERVAL_WARMUP = 60    # 1 minute
CHECK_INTERVAL_MAIN = 300     # 5 minutes
MIN_TRADES_THRESHOLD = 1      # Minimum 1 trade in 1 hour


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
        safe_print(f"[CLEAN] FAILED (code: {result.returncode})")
        if result.stderr:
            safe_print(f"[CLEAN] stderr: {result.stderr.decode('utf-8', errors='replace')}")
        return False


def validate_config(config_path: Path, strategy_name: str) -> bool:
    """Validate config file (Ensemble OFF, single strategy ON)"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Check ensemble disabled
        ensemble_enabled = config.get('ensemble', {}).get('enabled', False)
        if ensemble_enabled:
            safe_print(f"[WARN] Ensemble is enabled in {config_path}")
            return False
        
        # Check strategy enabled
        strategy_config = config.get('strategy', {}).get(strategy_name, {})
        if not strategy_config.get('enabled', False):
            safe_print(f"[WARN] {strategy_name} is not enabled in {config_path}")
            return False
        
        return True
        
    except Exception as e:
        safe_print(f"[ERROR] Config validation failed: {e}")
        return False


def run_single_strategy(strategy_name: str) -> dict:
    """
    Run 1-hour smoke test for single strategy
    
    Returns:
        dict: Test result with status, trades, meaningful flag
    """
    safe_print(f"\n{'='*70}")
    safe_print(f"STRATEGY: {strategy_name.upper()}")
    safe_print(f"START: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
            "meaningful": False,
            "start_time": None,
            "end_time": None
        }
    
    # 2. Get initial count
    test_start_time = datetime.now()
    initial_count = count_paper_trades(strategy_id=strategy_name, since=test_start_time)
    safe_print(f"[COUNT] Initial: {initial_count} trades (baseline)")
    
    # 3. Validate config
    config_path = project_root / "configs" / "paper" / f"phase21_{strategy_name}_solo.yml"
    if not config_path.exists():
        safe_print(f"[ERROR] Config not found: {config_path}")
        return {
            "strategy": strategy_name,
            "status": "FAILED",
            "reason": f"Config not found: {config_path}",
            "initial_trades": initial_count,
            "final_trades": initial_count,
            "delta": 0,
            "meaningful": False,
            "start_time": test_start_time.isoformat(),
            "end_time": datetime.now().isoformat()
        }
    
    if not validate_config(config_path, strategy_name):
        return {
            "strategy": strategy_name,
            "status": "FAILED",
            "reason": "Config validation failed (Ensemble ON or strategy disabled)",
            "initial_trades": initial_count,
            "final_trades": initial_count,
            "delta": 0,
            "meaningful": False,
            "start_time": test_start_time.isoformat(),
            "end_time": datetime.now().isoformat()
        }
    
    safe_print(f"[CONFIG] Validated: {config_path}")
    
    # 4. Run paper trading engine
    cmd = [sys.executable, "scripts/run_paper.py", "--config", str(config_path)]
    safe_print(f"[RUN] Starting engine (1h)...")
    safe_print(f"[RUN] Command: {' '.join(cmd)}")
    
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
    
    # 5. Monitor warmup (first 5 minutes)
    safe_print(f"\n[MONITOR] Warmup phase ({WARMUP_MINUTES} minutes, check every 1min)...")
    start_time = time.time()
    last_count = initial_count
    error_detected = False
    no_trades_in_warmup = True
    
    for minute in range(WARMUP_MINUTES):
        time.sleep(CHECK_INTERVAL_WARMUP)
        elapsed = int(time.time() - start_time)
        
        # Check process alive
        if process.poll() is not None:
            safe_print(f"[ERROR] Process died at {elapsed}s")
            error_detected = True
            break
        
        # Check trades
        current_count = count_paper_trades(strategy_id=strategy_name, since=test_start_time)
        delta = current_count - initial_count
        
        if current_count > last_count:
            safe_print(f"[{elapsed}s] Trade: {current_count} (delta: +{delta})")
            last_count = current_count
            no_trades_in_warmup = False
        else:
            safe_print(f"[{elapsed}s] Count: {current_count} (delta: {delta})")
    
    safe_print(f"[MONITOR] Warmup complete ({WARMUP_MINUTES}min)")
    
    # Check warmup result
    if error_detected:
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()
        
        return {
            "strategy": strategy_name,
            "status": "FAILED",
            "reason": "Process died during warmup",
            "initial_trades": initial_count,
            "final_trades": count_paper_trades(strategy_id=strategy_name, since=test_start_time),
            "delta": count_paper_trades(strategy_id=strategy_name, since=test_start_time) - initial_count,
            "meaningful": False,
            "start_time": test_start_time.isoformat(),
            "end_time": datetime.now().isoformat()
        }
    
    # CRITICAL: If no trades in warmup, terminate early
    if no_trades_in_warmup:
        safe_print(f"\n[EARLY_EXIT] No trades in {WARMUP_MINUTES}min warmup -> NOT MEANINGFUL")
        safe_print(f"[EARLY_EXIT] Terminating test for {strategy_name}")
        
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            try:
                process.kill()
            except:
                pass
        
        final_count = count_paper_trades(strategy_id=strategy_name, since=test_start_time)
        
        return {
            "strategy": strategy_name,
            "status": "NOT_MEANINGFUL",
            "reason": f"No trades in {WARMUP_MINUTES}min warmup (early exit)",
            "initial_trades": initial_count,
            "final_trades": final_count,
            "delta": final_count - initial_count,
            "meaningful": False,
            "start_time": test_start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "early_exit": True
        }
    
    # 6. Monitor remaining time (55 minutes, check every 5min)
    remaining_minutes = RUNTIME_PER_STRATEGY_MIN - WARMUP_MINUTES
    num_checks = remaining_minutes // (CHECK_INTERVAL_MAIN // 60)
    
    safe_print(f"[MONITOR] Remaining {remaining_minutes} minutes (check every {CHECK_INTERVAL_MAIN//60}min)...")
    
    for i in range(num_checks):
        time.sleep(CHECK_INTERVAL_MAIN)
        elapsed_total = int(time.time() - start_time)
        current_count = count_paper_trades(strategy_id=strategy_name, since=test_start_time)
        delta = current_count - initial_count
        
        if process.poll() is not None:
            safe_print(f"[INFO] Process ended naturally at {elapsed_total}s")
            break
        
        safe_print(f"[{elapsed_total}s / {RUNTIME_PER_STRATEGY_MIN*60}s] Running... (trades: {current_count}, delta: {delta})")
    
    # 7. Wait for remaining time
    elapsed = time.time() - start_time
    remaining = (RUNTIME_PER_STRATEGY_MIN * 60) - elapsed
    if remaining > 0:
        safe_print(f"[WAIT] Waiting final {int(remaining)}s...")
        time.sleep(remaining)
    
    # 8. Final results
    final_count = count_paper_trades(strategy_id=strategy_name, since=test_start_time)
    delta = final_count - initial_count
    stats = get_paper_trade_stats(strategy_id=strategy_name, since=test_start_time)
    
    # Determine meaningfulness
    meaningful = (delta >= MIN_TRADES_THRESHOLD)
    status = "PASS" if meaningful else "NOT_MEANINGFUL"
    
    safe_print(f"\n{'='*70}")
    safe_print(f"COMPLETE: {strategy_name.upper()}")
    safe_print(f"END: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    safe_print(f"Initial: {initial_count} | Final: {final_count} | Delta: {delta}")
    safe_print(f"Stats: {stats}")
    safe_print(f"Meaningful: {'YES' if meaningful else 'NO'}")
    safe_print(f"Status: {status}")
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
        "status": status,
        "reason": None if meaningful else f"Only {delta} trades in 1 hour",
        "initial_trades": initial_count,
        "final_trades": final_count,
        "delta": delta,
        "meaningful": meaningful,
        "start_time": test_start_time.isoformat(),
        "end_time": datetime.now().isoformat(),
        "stats": stats
    }


def main():
    """Main execution"""
    safe_print("\n" + "="*70)
    safe_print("PHASE21-1A: Single Strategy Smoke Test Harness")
    safe_print("="*70)
    safe_print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    safe_print(f"Strategies: {len(STRATEGIES)}")
    safe_print(f"Runtime per strategy: {RUNTIME_PER_STRATEGY_MIN} minutes")
    safe_print(f"Warmup: {WARMUP_MINUTES} minutes (early exit if 0 trades)")
    safe_print(f"Estimated total: {len(STRATEGIES)} hours (max)")
    safe_print("="*70)
    
    results = []
    
    for idx, strategy in enumerate(STRATEGIES, 1):
        safe_print(f"\n[{idx}/{len(STRATEGIES)}] {strategy.upper()}")
        
        result = run_single_strategy(strategy)
        results.append(result)
        
        # Wait before next strategy
        if idx < len(STRATEGIES):
            safe_print("\n[WAIT] 10s before next strategy...")
            time.sleep(10)
    
    # Summary
    safe_print("\n" + "="*70)
    safe_print("ALL TESTS COMPLETE")
    safe_print("="*70)
    safe_print(f"End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    safe_print("\nResults Summary:")
    
    meaningful_count = 0
    for result in results:
        status = result['status']
        meaningful_str = "YES" if result['meaningful'] else "NO"
        delta = result['delta']
        
        safe_print(f"  [{status}] {result['strategy'].upper()}: delta={delta}, meaningful={meaningful_str}")
        
        if result['meaningful']:
            meaningful_count += 1
    
    safe_print(f"\nMeaningful tests: {meaningful_count}/{len(STRATEGIES)}")
    safe_print("="*70)
    
    # Save results to JSON
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
