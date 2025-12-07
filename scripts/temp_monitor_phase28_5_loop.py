#!/usr/bin/env python3
"""PHASE28-5 진행 상황 연속 모니터링"""
import sys
import time
from pathlib import Path
from datetime import datetime
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection

def get_progress():
    """진행 상황 조회"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Runs
            cur.execute("""
                SELECT COUNT(*), 
                       SUM(total_jobs), 
                       SUM(completed_jobs),
                       SUM(failed_jobs)
                FROM tuning.runs
                WHERE run_id LIKE 'phase28_5_%'
            """)
            run_row = cur.fetchone()
            
            # Best result
            cur.execute("""
                SELECT 
                    sharpe_ratio,
                    pnl,
                    trade_count,
                    win_rate
                FROM tuning.results
                WHERE run_id LIKE 'phase28_5_%' 
                  AND trade_count >= 5
                ORDER BY sharpe_ratio DESC
                LIMIT 1
            """)
            best_row = cur.fetchone()
    
    return {
        'total_runs': run_row[0] if run_row else 0,
        'total_jobs': run_row[1] if run_row else 0,
        'completed': run_row[2] if run_row else 0,
        'failed': run_row[3] if run_row else 0,
        'best_sharpe': best_row[0] if best_row else None,
        'best_pnl': best_row[1] if best_row else None,
        'best_trades': best_row[2] if best_row else None,
        'best_winrate': best_row[3] if best_row else None,
    }

def main():
    """메인 모니터링 루프"""
    print("=" * 80)
    print("🔍 PHASE28-5 Local Grid Search Round 1 - Continuous Monitor")
    print("=" * 80)
    print("Press Ctrl+C to stop\n")
    
    try:
        iteration = 0
        while True:
            iteration += 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            progress = get_progress()
            
            total = progress['total_jobs']
            completed = progress['completed']
            failed = progress['failed']
            running = total - completed - failed
            pct = (completed / total * 100) if total > 0 else 0
            
            print(f"\n[{timestamp}] Iteration {iteration}")
            print(f"  Runs: {progress['total_runs']}")
            print(f"  Progress: {completed}/{total} ({pct:.1f}%)")
            print(f"  Running: {running}, Failed: {failed}")
            
            if progress['best_sharpe'] is not None:
                print(f"  Best: Sharpe={progress['best_sharpe']:.4f}, "
                      f"PnL={progress['best_pnl']:.2f}, "
                      f"Trades={progress['best_trades']}, "
                      f"Win%={progress['best_winrate']*100:.1f}%")
            
            # 완료 체크
            if total > 0 and completed == total:
                print("\n" + "=" * 80)
                print("✅ All trials completed!")
                print("=" * 80)
                break
            
            # 60초 대기
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")

if __name__ == '__main__':
    main()
