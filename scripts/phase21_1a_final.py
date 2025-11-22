#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE21-1A: Final Execution (5min Quick Tests)
===============================================
7 strategies x 5-minute tests = 35 minutes total
Fast validation of signal generation capability
"""
import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime, timedelta
import json
import yaml

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.trade_counter_v2 import count_paper_trades, get_paper_trade_stats

STRATEGIES = [
    {"name": "scalping", "tf": "3m"},
    {"name": "breakout", "tf": "15m"},
    {"name": "reversion", "tf": "5m"},
    {"name": "trend", "tf": "1h"},
    {"name": "swing", "tf": "1h"},
    {"name": "swing_bb", "tf": "5m"},
    {"name": "daytrade", "tf": "15m"},
]

TEST_MINUTES = 5


def safe_print(msg):
    try:
        print(msg)
    except:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def run_clean_state():
    safe_print("\n[CLEAN] Clean-State...")
    result = subprocess.run(
        [sys.executable, "scripts/clean_state_complete.py"],
        cwd=project_root,
        capture_output=True,
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    )
    return result.returncode == 0


def create_quick_config(strategy_name, timeframe):
    """Create 5-minute config from 1h template"""
    base_config = project_root / "configs" / "paper" / f"phase21_{strategy_name}_solo.yml"
    quick_config = project_root / "configs" / "paper" / f"phase21_{strategy_name}_quick.yml"
    
    with open(base_config, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    
    # Override duration to 5 minutes
    cfg['duration_hours'] = TEST_MINUTES / 60.0
    cfg['timeframe'] = timeframe
    cfg['feed']['timeframes'] = [timeframe]
    
    with open(quick_config, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)
    
    return quick_config


def test_strategy(name, tf):
    safe_print(f"\n{'='*60}")
    safe_print(f"{name.upper()} ({tf}) - {TEST_MINUTES}min test")
    safe_print(f"{'='*60}")
    
    if not run_clean_state():
        return {"strategy": name, "tf": tf, "status": "CLEAN_FAILED", "trades": 0}
    
    start = datetime.now()
    initial = count_paper_trades(strategy_id=name, since=start)
    
    # Create quick config
    config_path = create_quick_config(name, tf)
    safe_print(f"[CONFIG] {config_path}")
    
    # Run
    cmd = [sys.executable, "scripts/run_paper.py", "--config", str(config_path)]
    safe_print(f"[RUN] Starting...")
    
    proc = subprocess.Popen(
        cmd,
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    )
    
    # Monitor
    runtime = TEST_MINUTES * 60
    start_time = time.time()
    checks = 0
    
    while (time.time() - start_time) < runtime:
        if proc.poll() is not None:
            break
        time.sleep(30)  # Check every 30s
        checks += 1
        
        current = count_paper_trades(strategy_id=name, since=start)
        delta = current - initial
        elapsed = int(time.time() - start_time)
        safe_print(f"[{elapsed}s] Trades: {delta}")
    
    # Final
    final = count_paper_trades(strategy_id=name, since=start)
    delta = final - initial
    stats = get_paper_trade_stats(strategy_id=name, since=start)
    
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except:
        try:
            proc.kill()
        except:
            pass
    
    status = "OK" if delta >= 1 else "NOT_MEANINGFUL"
    safe_print(f"[RESULT] {name.upper()}: {status} ({delta} trades)")
    
    return {
        "strategy": name,
        "timeframe": tf,
        "status": status,
        "trades": delta,
        "stats": stats,
        "start": start.isoformat(),
        "end": datetime.now().isoformat(),
        "test_minutes": TEST_MINUTES
    }


def main():
    safe_print("\n" + "="*60)
    safe_print(f"PHASE21-1A: {len(STRATEGIES)} Strategies x {TEST_MINUTES}min")
    safe_print(f"Total: ~{len(STRATEGIES) * TEST_MINUTES} minutes")
    safe_print("="*60)
    
    results = []
    
    for idx, s in enumerate(STRATEGIES, 1):
        safe_print(f"\n[{idx}/{len(STRATEGIES)}] {s['name'].upper()}")
        result = test_strategy(s['name'], s['tf'])
        results.append(result)
        
        if idx < len(STRATEGIES):
            safe_print("\n[WAIT] 5s...")
            time.sleep(5)
    
    # Summary
    safe_print("\n" + "="*60)
    safe_print("ALL TESTS COMPLETE")
    safe_print("="*60)
    
    ok = sum(1 for r in results if r['status'] == 'OK')
    for r in results:
        safe_print(f"  [{r['status']}] {r['strategy'].upper()}: {r['trades']} trades ({r['timeframe']})")
    
    safe_print(f"\nMeaningful: {ok}/{len(STRATEGIES)}")
    
    # Save
    docs_dir = project_root / "docs" / "PHASE21"
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = docs_dir / "phase21_1a_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    safe_print(f"\nSaved: {results_file}")
    
    return results


if __name__ == "__main__":
    try:
        results = main()
    except KeyboardInterrupt:
        safe_print("\nInterrupted")
        sys.exit(1)
