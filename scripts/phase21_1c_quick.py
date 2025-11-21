#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE21-1C Quick Test: 7 Strategies × 5min Each
================================================
"""
import os
import sys
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.force_clean_paper_trades import get_conn

STRATEGIES = [
    {"name": "scalping", "timeframe": "3m"},
    {"name": "breakout", "timeframe": "15m"},
    {"name": "reversion", "timeframe": "5m"},
    {"name": "trend", "timeframe": "1h"},
    {"name": "swing", "timeframe": "1h"},
    {"name": "swing_bb", "timeframe": "5m"},
    {"name": "daytrade", "timeframe": "15m"},
]

TEST_DURATION_MIN = 5


def safe_print(msg):
    try:
        print(msg)
    except:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def clean_paper_trades():
    """Clean paper trades"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM trading.trades WHERE mode='paper'")
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return deleted


def count_paper_trades(strategy_id=None):
    """Count paper trades"""
    conn = get_conn()
    cur = conn.cursor()
    
    if strategy_id:
        cur.execute("SELECT COUNT(*) FROM trading.trades WHERE mode='paper' AND strategy_id=%s", (strategy_id,))
    else:
        cur.execute("SELECT COUNT(*) FROM trading.trades WHERE mode='paper'")
    
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count


def get_trade_stats(strategy_id=None):
    """Get trade statistics"""
    conn = get_conn()
    cur = conn.cursor()
    
    if strategy_id:
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN side='LONG' THEN 1 ELSE 0 END) as long_count,
                SUM(CASE WHEN side='SHORT' THEN 1 ELSE 0 END) as short_count,
                COALESCE(SUM(pnl_gross), 0) as total_pnl,
                COALESCE(AVG(pnl_gross), 0) as avg_pnl
            FROM trading.trades 
            WHERE mode='paper' AND strategy_id=%s
        """, (strategy_id,))
    else:
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN side='LONG' THEN 1 ELSE 0 END) as long_count,
                SUM(CASE WHEN side='SHORT' THEN 1 ELSE 0 END) as short_count,
                COALESCE(SUM(pnl_gross), 0) as total_pnl,
                COALESCE(AVG(pnl_gross), 0) as avg_pnl
            FROM trading.trades 
            WHERE mode='paper'
        """)
    
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    return {
        "total": row[0],
        "long": row[1] or 0,
        "short": row[2] or 0,
        "pnl_total": float(row[3]),
        "pnl_avg": float(row[4])
    }


def test_strategy(strategy_name, timeframe):
    """Test single strategy for 5 minutes"""
    safe_print(f"\n{'='*70}")
    safe_print(f"[{datetime.now().strftime('%H:%M:%S')}] Testing: {strategy_name.upper()} ({timeframe})")
    safe_print(f"{'='*70}")
    
    # Clean state
    deleted = clean_paper_trades()
    safe_print(f"[CLEAN] Deleted {deleted} paper trades")
    
    # Config path
    config_path = project_root / "configs" / "paper" / f"phase21_{strategy_name}_solo.yml"
    if not config_path.exists():
        return {
            "strategy": strategy_name,
            "timeframe": timeframe,
            "status": "CONFIG_NOT_FOUND",
            "trades": 0,
            "stats": {}
        }
    
    # Start test
    test_start = datetime.now()
    
    cmd = [
        sys.executable,
        "scripts/run_paper.py",
        "--config", str(config_path),
        "--duration-hours", str(TEST_DURATION_MIN / 60.0)
    ]
    
    safe_print(f"[RUN] Starting {strategy_name}...")
    
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
    
    # Wait for duration
    start_time = time.time()
    max_runtime = TEST_DURATION_MIN * 60 + 30  # +30s buffer
    
    while (time.time() - start_time) < max_runtime:
        if process.poll() is not None:
            safe_print(f"[INFO] Process ended early")
            break
        time.sleep(30)
        elapsed = int(time.time() - start_time)
        current_count = count_paper_trades(strategy_id=strategy_name)
        safe_print(f"[{elapsed}s] Trades: {current_count}")
    
    # Terminate
    try:
        process.terminate()
        process.wait(timeout=10)
    except:
        try:
            process.kill()
        except:
            pass
    
    # Get results
    final_count = count_paper_trades(strategy_id=strategy_name)
    stats = get_trade_stats(strategy_id=strategy_name)
    
    # Classify
    if final_count >= 3:
        status = "ACTIVE"
    elif final_count >= 1:
        status = "LOW_FREQ"
    else:
        status = "NO_TRADES"
    
    safe_print(f"\n[RESULT] {strategy_name.upper()}: {status}")
    safe_print(f"  Trades: {final_count}")
    safe_print(f"  LONG: {stats['long']}, SHORT: {stats['short']}")
    safe_print(f"  PnL: ${stats['pnl_total']:.2f} (avg: ${stats['pnl_avg']:.2f})")
    safe_print(f"{'='*70}")
    
    return {
        "strategy": strategy_name,
        "timeframe": timeframe,
        "status": status,
        "trades": final_count,
        "stats": stats,
        "test_duration_min": TEST_DURATION_MIN,
        "test_start": test_start.isoformat(),
        "test_end": datetime.now().isoformat()
    }


def main():
    """Main execution"""
    safe_print("\n" + "="*70)
    safe_print("PHASE21-1C: Quick Strategy Tests (5min Each)")
    safe_print("="*70)
    safe_print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    safe_print(f"Total duration: ~{len(STRATEGIES) * TEST_DURATION_MIN}min")
    safe_print("="*70)
    
    results = []
    
    for idx, strat in enumerate(STRATEGIES, 1):
        safe_print(f"\n[{idx}/{len(STRATEGIES)}] {strat['name'].upper()}")
        result = test_strategy(strat['name'], strat['timeframe'])
        results.append(result)
        
        if idx < len(STRATEGIES):
            safe_print("\n[WAIT] 10s before next strategy...")
            time.sleep(10)
    
    # Summary
    safe_print("\n" + "="*70)
    safe_print("TEST COMPLETE")
    safe_print("="*70)
    
    active = sum(1 for r in results if r['status'] == 'ACTIVE')
    low_freq = sum(1 for r in results if r['status'] == 'LOW_FREQ')
    no_trades = sum(1 for r in results if r['status'] == 'NO_TRADES')
    
    for result in results:
        safe_print(f"  [{result['status']}] {result['strategy'].upper()} ({result['timeframe']}): {result['trades']} trades")
    
    safe_print(f"\nClassification:")
    safe_print(f"  ACTIVE: {active}")
    safe_print(f"  LOW_FREQ: {low_freq}")
    safe_print(f"  NO_TRADES: {no_trades}")
    safe_print("="*70)
    
    # Save results
    docs_dir = project_root / "docs" / "PHASE21"
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = docs_dir / "phase21_1c_quick_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    safe_print(f"\nResults saved: {results_file}")
    
    return results


if __name__ == "__main__":
    try:
        results = main()
        sys.exit(0)
    except KeyboardInterrupt:
        safe_print("\n\nInterrupted")
        sys.exit(1)
    except Exception as e:
        safe_print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
