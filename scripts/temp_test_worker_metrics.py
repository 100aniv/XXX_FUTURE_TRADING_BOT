#!/usr/bin/env python3
"""Worker 메트릭 추출 테스트"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from database import get_db_connection
from tuning.cluster.worker import TuningWorker
from datetime import datetime
import time

# 최근 job_id 가져오기
with get_db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT job_id, run_id
            FROM tuning.jobs
            WHERE status = 'COMPLETED'
            ORDER BY updated_at DESC
            LIMIT 1
        """)
        result = cur.fetchone()
        job_id, run_id = result

print(f"Testing metrics extraction for:")
print(f"  job_id: {job_id}")
print(f"  run_id: {run_id}\n")

# 메트릭 추출 로직을 직접 실행
start_time = datetime.now()
runtime_sec = 180.0

try:
    # Worker의 _extract_metrics_from_db 로직을 직접 실행
    import numpy as np
    
    sql_trades_detailed = """
    SELECT
        pnl,
        pnl_pct,
        ts_close as exit_time
    FROM trading.trades
    WHERE trial_id = %s
      AND status = 'CLOSED'
    ORDER BY ts_close ASC
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_trades_detailed, (job_id,))
            trades_rows = cur.fetchall()
    
    print(f"Found {len(trades_rows)} trades\n")
    
    trades = [
        {
            'pnl': row[0],
            'pnl_pct': row[1],
            'exit_time': row[2]
        }
        for row in trades_rows
    ]
    
    trade_count = len(trades)
    
    if trade_count == 0:
        print("⚠️ No trades found")
        metrics = {}
    else:
        # 메트릭 계산
        win_count = sum(1 for t in trades if t['pnl'] > 0)
        lose_count = trade_count - win_count
        win_rate = win_count / trade_count if trade_count > 0 else 0.0
        
        total_pnl = sum(t['pnl'] for t in trades)
        avg_win = np.mean([t['pnl'] for t in trades if t['pnl'] > 0]) if win_count > 0 else 0.0
        avg_lose = np.mean([t['pnl'] for t in trades if t['pnl'] <= 0]) if lose_count > 0 else 0.0
        
        avg_pnl_pct = np.mean([t['pnl_pct'] for t in trades]) if trade_count > 0 else 0.0
        
        metrics = {
            'trade_count': trade_count,
            'pnl': round(total_pnl, 2),
            'pnl_pct': round(avg_pnl_pct, 2),
            'win_count': win_count,
            'lose_count': lose_count,
            'win_rate': round(win_rate, 4),
            'avg_win': round(avg_win, 2),
            'avg_lose': round(avg_lose, 2),
        }
    
    print("✅ 메트릭 추출 성공!")
    print(f"  trade_count: {metrics.get('trade_count')}")
    print(f"  pnl: {metrics.get('pnl')}")
    print(f"  sharpe: {metrics.get('sharpe_ratio')}")
    print(f"  win_rate: {metrics.get('win_rate')}")
    
except Exception as e:
    print(f"❌ 메트릭 추출 실패: {e}")
    import traceback
    traceback.print_exc()
