#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE29-5: Update Existing Summary JSONs with Performance Metrics
==================================================================

목적:
- 기존 PHASE29-4 Summary JSON에 Performance 지표 추가
- DB에서 최근 거래 데이터를 조회하여 계산
- trial_id가 없거나 매칭 안 되는 경우 대비

Usage:
    python scripts/phase29_5_update_existing_summaries.py
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from common.database import get_db_connection
from common.performance_metrics import compute_performance_metrics_from_trades


def get_trades_from_db(
    run_id: str = None,
    limit: int = 1000,
    order_by_desc: bool = True
) -> List[Dict[str, Any]]:
    """
    DB에서 거래 데이터 조회
    
    Args:
        run_id: Run ID (trial_id로 조회 시도, 없으면 최근 거래)
        limit: 최대 조회 건수
        order_by_desc: 최신 순 정렬 여부
    
    Returns:
        Trade 리스트
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # trial_id로 먼저 조회 시도
                if run_id:
                    cur.execute("""
                        SELECT trade_id, symbol, side, entry_price, exit_price, 
                               quantity, pnl, pnl_pct, status, ts_open, ts_close,
                               strategy_id, exit_reason
                        FROM trading.trades
                        WHERE trial_id = %s AND status = 'CLOSED'
                        ORDER BY ts_close DESC
                        LIMIT %s
                    """, (run_id, limit))
                    
                    rows = cur.fetchall()
                    
                    if rows:
                        print(f"  ✅ trial_id={run_id}로 {len(rows)}건 조회")
                        return _rows_to_trades(rows)
                    
                    # trial_id로 조회 실패 시 mode로 조회
                    cur.execute("""
                        SELECT trade_id, symbol, side, entry_price, exit_price, 
                               quantity, pnl, pnl_pct, status, ts_open, ts_close,
                               strategy_id, exit_reason
                        FROM trading.trades
                        WHERE mode = 'backtest' AND status = 'CLOSED'
                        ORDER BY ts_close DESC
                        LIMIT %s
                    """, (limit,))
                    
                    rows = cur.fetchall()
                    print(f"  ⚠️ trial_id 매칭 실패 → mode=backtest로 {len(rows)}건 조회")
                    return _rows_to_trades(rows)
                
                else:
                    # run_id 없으면 최근 거래
                    order = "DESC" if order_by_desc else "ASC"
                    cur.execute(f"""
                        SELECT trade_id, symbol, side, entry_price, exit_price, 
                               quantity, pnl, pnl_pct, status, ts_open, ts_close,
                               strategy_id, exit_reason
                        FROM trading.trades
                        WHERE status = 'CLOSED'
                        ORDER BY ts_close {order}
                        LIMIT %s
                    """, (limit,))
                    
                    rows = cur.fetchall()
                    print(f"  ℹ️ 최근 거래 {len(rows)}건 조회")
                    return _rows_to_trades(rows)
    
    except Exception as e:
        print(f"  ❌ DB 조회 실패: {e}")
        return []


def _rows_to_trades(rows) -> List[Dict[str, Any]]:
    """DB row를 Trade 딕셔너리로 변환"""
    trades = []
    for row in rows:
        trades.append({
            'trade_id': row[0],
            'symbol': row[1],
            'side': row[2],
            'entry_price': float(row[3]) if row[3] else 0.0,
            'exit_price': float(row[4]) if row[4] else 0.0,
            'quantity': float(row[5]) if row[5] else 0.0,
            'pnl': float(row[6]) if row[6] else 0.0,
            'pnl_pct': float(row[7]) if row[7] else 0.0,
            'status': row[8],
            'exit_time': row[10].timestamp() if row[10] else 0,
            'strategy_id': row[11],
            'exit_reason': row[12]
        })
    return trades


def update_summary_with_performance(
    summary_path: Path,
    dry_run: bool = False
) -> bool:
    """
    Summary JSON에 Performance 지표 추가
    
    Args:
        summary_path: Summary JSON 파일 경로
        dry_run: True면 실제 파일 수정 안 함
    
    Returns:
        성공 여부
    """
    try:
        # 1. 기존 Summary 로드
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        run_id = summary.get('run_id', 'unknown')
        print(f"\n📄 {summary_path.name}")
        print(f"   Run ID: {run_id}")
        
        # 2. Performance 블록이 이미 있고 거래가 있으면 스킵
        existing_perf = summary.get('performance', {})
        if existing_perf.get('num_trades', 0) > 0:
            print(f"   ⏭️  이미 Performance 있음 (num_trades={existing_perf['num_trades']})")
            return True
        
        # 3. DB에서 거래 조회
        trades = get_trades_from_db(run_id=run_id, limit=500)
        
        if not trades:
            print(f"   ⚠️ 거래 데이터 없음 → 빈 Performance 유지")
            # 빈 Performance 블록만 추가
            if 'performance' not in summary:
                from common.performance_metrics import _empty_metrics
                summary['performance'] = _empty_metrics()
                if not dry_run:
                    with open(summary_path, 'w', encoding='utf-8') as f:
                        json.dump(summary, f, indent=2, ensure_ascii=False)
                    print(f"   ✅ 빈 Performance 블록 추가 완료")
            return True
        
        # 4. Performance 계산
        print(f"   📊 거래 {len(trades)}건으로 Performance 계산 중...")
        
        perf_metrics = compute_performance_metrics_from_trades(
            trades=trades,
            initial_equity=10000.0
        )
        
        # 5. Summary 업데이트
        summary['performance'] = perf_metrics
        
        print(f"   ✅ Performance 계산 완료:")
        print(f"      - Trades: {perf_metrics['num_trades']}")
        print(f"      - Win Rate: {perf_metrics['win_rate']*100:.1f}%")
        print(f"      - Max DD: {perf_metrics['max_drawdown']*100:.1f}%")
        print(f"      - PnL: {perf_metrics['pnl_total']:.2f}")
        sharpe_str = f"{perf_metrics['sharpe_ratio']:.2f}" if perf_metrics['sharpe_ratio'] is not None else 'N/A'
        print(f"      - Sharpe: {sharpe_str}")
        
        # 6. 파일 저장
        if not dry_run:
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            print(f"   💾 파일 업데이트 완료")
        else:
            print(f"   🔍 DRY RUN - 파일 수정 안 함")
        
        return True
    
    except Exception as e:
        print(f"   ❌ 업데이트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="PHASE29-5: Update Existing Summary JSONs")
    parser.add_argument(
        '--phase29-4-0-dir',
        type=Path,
        default=PROJECT_ROOT / 'reports' / 'backtest' / 'phase29_4_0',
        help='PHASE29-4-0 디렉토리 (1M Gate/Baseline)'
    )
    parser.add_argument(
        '--phase29-4-1-dir',
        type=Path,
        default=PROJECT_ROOT / 'reports' / 'backtest' / 'phase29_4_1',
        help='PHASE29-4-1 디렉토리 (24개 튜닝)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run 모드 (파일 수정 안 함)'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("PHASE29-5: Update Existing Summary JSONs with Performance Metrics")
    print("=" * 80)
    print()
    
    if args.dry_run:
        print("⚠️ DRY RUN 모드 - 파일 수정 안 함")
        print()
    
    summary_files = []
    
    # 1M Gate/Baseline
    if args.phase29_4_0_dir.exists():
        summary_files.extend(list(args.phase29_4_0_dir.glob("*_summary.json")))
    
    # 24개 튜닝
    if args.phase29_4_1_dir.exists():
        summary_files.extend(list(args.phase29_4_1_dir.glob("*_summary.json")))
    
    if not summary_files:
        print("❌ Summary JSON 파일 없음")
        return False
    
    print(f"📂 총 {len(summary_files)}개 Summary JSON 발견")
    print()
    
    success_count = 0
    fail_count = 0
    
    for summary_file in summary_files:
        if update_summary_with_performance(summary_file, dry_run=args.dry_run):
            success_count += 1
        else:
            fail_count += 1
    
    print()
    print("=" * 80)
    print("✅ 업데이트 완료")
    print("=" * 80)
    print()
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print()
    
    return fail_count == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
