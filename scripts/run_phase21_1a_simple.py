#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE21-1A: Simple Sequential Strategy Tests
=============================================
간소화된 버전: 각 전략을 순차적으로 직접 실행
"""
import os
import sys
import subprocess
import psycopg2
import time
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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

# DB 설정
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "trading_db",
    "user": "trading_user",
    "password": "trading_pw_2024"
}


def get_trade_count():
    """현재 거래 수"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trading.trades")
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"DB Error: {e}")
        return -1


def clean_state():
    """Clean-State 초기화"""
    print("\n" + "="*60)
    print("Clean-State...")
    print("="*60)
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    result = subprocess.run(
        [sys.executable, "scripts/phase20_clean_state.py"],
        cwd=project_root,
        capture_output=True,
        env=env
    )
    
    if result.returncode == 0:
        print("Clean-State OK")
        return True
    else:
        print(f"Clean-State FAILED (code: {result.returncode})")
        return False


def run_single_strategy(strategy_name):
    """단일 전략 1시간 테스트"""
    print("\n" + "="*70)
    print(f"STRATEGY: {strategy_name.upper()}")
    print(f"START: {datetime.now().strftime('%H:%M:%S')}")
    print("="*70)
    
    # Clean
    if not clean_state():
        return {"status": "FAIL", "reason": "Clean-State failed"}
    
    initial_count = get_trade_count()
    print(f"Initial trades: {initial_count}")
    
    # Run paper trading
    config_path = f"configs/paper/phase21_{strategy_name}_solo.yml"
    cmd = [
        sys.executable,
        "scripts/run_paper.py",
        "--config",
        config_path
    ]
    
    print(f"Command: {' '.join(cmd)}")
    print(f"Config: {config_path}")
    print("\nStarting engine (1 hour wall-clock)...")
    
    # Start process
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
    
    # Monitor first 5 minutes (300s) - per-second
    print("\n[MONITOR] First 5 minutes (per-second)...")
    start_time = time.time()
    last_trades = initial_count
    
    for i in range(300):
        time.sleep(1)
        elapsed = int(time.time() - start_time)
        
        # Check process
        if process.poll() is not None:
            print(f"\n[ERROR] Process died at {elapsed}s!")
            stdout, _ = process.communicate()
            print(f"Last output:\n{stdout[-2000:]}")
            return {"status": "FAIL", "reason": f"Process died at {elapsed}s"}
        
        # Check trades
        current_trades = get_trade_count()
        if current_trades > last_trades:
            print(f"[{elapsed}s] Trade detected: {current_trades} (+{current_trades-last_trades})")
            last_trades = current_trades
        
        # Minute marker
        if elapsed % 60 == 0:
            print(f"[{elapsed}s] Monitoring... (trades: {current_trades})")
    
    print(f"\n[MONITOR] First 5min complete. Trades: {last_trades}")
    print("[WAIT] Remaining 55 minutes...")
    
    # Wait remaining time (check every 5 min)
    for i in range(11):  # 55 / 5 = 11
        time.sleep(300)  # 5 minutes
        elapsed_total = int(time.time() - start_time)
        current_trades = get_trade_count()
        
        if process.poll() is not None:
            print(f"\n[ERROR] Process died at {elapsed_total}s!")
            return {"status": "FAIL", "reason": f"Process died at {elapsed_total}s"}
        
        print(f"[{elapsed_total}s / 3600s] Running... (trades: {current_trades})")
    
    # Final check
    final_trades = get_trade_count()
    trades_gen = final_trades - initial_count
    
    print("\n" + "="*70)
    print(f"COMPLETE: {strategy_name.upper()}")
    print(f"END: {datetime.now().strftime('%H:%M:%S')}")
    print(f"Initial: {initial_count} | Final: {final_trades} | Generated: {trades_gen}")
    print("="*70)
    
    # Terminate
    try:
        process.terminate()
        process.wait(timeout=10)
    except:
        process.kill()
    
    return {
        "status": "PASS" if trades_gen > 0 else "WARN",
        "initial": initial_count,
        "final": final_trades,
        "generated": trades_gen
    }


def main():
    print("\n" + "="*70)
    print("PHASE21-1A: Single Strategy Smoke Tests")
    print("="*70)
    print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Strategies: {len(STRATEGIES)}")
    print(f"Estimated time: {len(STRATEGIES)} hours")
    print("="*70)
    
    results = {}
    
    for idx, strategy in enumerate(STRATEGIES, 1):
        print(f"\n{'#'*70}")
        print(f"# {idx}/{len(STRATEGIES)}: {strategy.upper()}")
        print(f"{'#'*70}")
        
        result = run_single_strategy(strategy)
        results[strategy] = result
        
        print(f"\nResult: {result['status']}")
        if result['status'] == "FAIL":
            print(f"Reason: {result.get('reason', 'Unknown')}")
        
        # Wait before next
        if idx < len(STRATEGIES):
            print("\nWaiting 10s before next strategy...")
            time.sleep(10)
    
    # Summary
    print("\n" + "="*70)
    print("ALL TESTS COMPLETE!")
    print("="*70)
    print(f"End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nResults:")
    for strategy, result in results.items():
        icon = "PASS" if result['status'] == "PASS" else ("WARN" if result['status'] == "WARN" else "FAIL")
        print(f"  [{icon}] {strategy.upper()}: {result.get('generated', 0)} trades")
    print("="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
