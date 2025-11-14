#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run Backtest Script (PHASE8)
=============================
단일 전략 백테스트 실행 및 scorecard 생성

Usage:
    python scripts/run_backtest.py \\
        --mode backtest_clean \\
        --strategy scalping \\
        --symbol BTCUSDT \\
        --timeframe 5m \\
        --days 3

Output:
    artifacts/backtest_clean/{run_id}/
        ├─ effective_config.yml
        ├─ scorecard.csv
        ├─ scorecard.md
        └─ trades.log
"""
import sys
import argparse
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.config_loader import load_config_with_mode, generate_run_id, save_effective_config
from common.config_validation import validate_config
from execution.data_sources.backtest import BacktestDataSource
from analytics.scorecard import ScorecardGenerator


def parse_args():
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description='PHASE8: 단일 전략 백테스트 실행',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        required=True,
        choices=['backtest_clean', 'backtest', 'paper', 'live'],
        help='실행 모드 (PHASE8에서는 backtest_clean 권장)'
    )
    
    parser.add_argument(
        '--strategy',
        type=str,
        required=True,
        help='전략 이름 (예: scalping, daytrade, swing)'
    )
    
    parser.add_argument(
        '--symbol',
        type=str,
        required=True,
        help='심볼 (예: BTCUSDT)'
    )
    
    parser.add_argument(
        '--timeframe',
        type=str,
        default='5m',
        help='타임프레임 (예: 5m, 15m, 1h)'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=None,
        help='최근 N일 데이터 (예: 3)'
    )
    
    parser.add_argument(
        '--timerange',
        type=str,
        default=None,
        help='날짜 범위 (예: 2023-04-01:2023-04-05)'
    )
    
    parser.add_argument(
        '--data-path',
        type=str,
        default=None,
        help='데이터 파일 경로 (기본값: data/{symbol}_{timeframe}.csv)'
    )
    
    return parser.parse_args()


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("🚀 PHASE8 Backtest Runner")
    print("=" * 60)
    
    # 1. CLI 인자 파싱
    args = parse_args()
    
    print(f"\n📋 설정:")
    print(f"  - Mode: {args.mode}")
    print(f"  - Strategy: {args.strategy}")
    print(f"  - Symbol: {args.symbol}")
    print(f"  - Timeframe: {args.timeframe}")
    if args.days:
        print(f"  - Days: {args.days}")
    if args.timerange:
        print(f"  - Timerange: {args.timerange}")
    
    # 2. Config 로드 (병합 순서)
    print(f"\n🔧 Config 로드 및 병합...")
    cfg = load_config_with_mode(mode=args.mode)
    
    # 3. Config 검증
    print(f"\n✓ Config 검증...")
    try:
        validate_config(cfg)
    except Exception as e:
        print(f"❌ Config 검증 실패: {e}")
        sys.exit(1)
    
    # 4. run_id 생성
    run_id = generate_run_id()
    print(f"\n🆔 Run ID: {run_id}")
    
    # 5. effective_config.yml 스냅샷 저장
    print(f"\n💾 Effective Config 저장...")
    snapshot_path = save_effective_config(cfg, args.mode, run_id)
    print(f"  - {snapshot_path}")
    
    # 6. 데이터 로드
    print(f"\n📊 데이터 로드...")
    data_path = args.data_path or f"data/{args.symbol}_{args.timeframe}.csv"
    
    if not Path(data_path).exists():
        print(f"❌ 데이터 파일 없음: {data_path}")
        print(f"\n💡 Tip: 먼저 데이터를 다운로드하세요.")
        sys.exit(1)
    
    ds = BacktestDataSource(data_path)
    df = ds.load_slice(days=args.days, timerange=args.timerange)
    
    print(f"  - 로드 완료: {len(df)} rows")
    print(f"  - 기간: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
    
    # 7. 백테스트 실행 (더미 - 실제 백테스트 엔진 연동 필요)
    print(f"\n⚙️  백테스트 실행...")
    print(f"  ⚠️  [TODO] 실제 백테스트 엔진 연동 필요")
    print(f"  ⚠️  현재는 더미 거래 데이터로 scorecard 생성")
    
    # 더미 거래 데이터 (실제 구현 시 제거)
    dummy_trades = [
        {'pnl_pct': 2.5, 'status': 'closed', 'exit_reason': 'tp'},
        {'pnl_pct': -1.2, 'status': 'closed', 'exit_reason': 'sl'},
        {'pnl_pct': 3.1, 'status': 'closed', 'exit_reason': 'tp'},
        {'pnl_pct': -0.8, 'status': 'closed', 'exit_reason': 'sl'},
        {'pnl_pct': 1.9, 'status': 'closed', 'exit_reason': 'tp'},
    ]
    
    # 8. Scorecard 생성
    print(f"\n📈 Scorecard 생성...")
    output_dir = Path(f"artifacts/{args.mode}/{run_id}")
    
    generator = ScorecardGenerator(
        strategy_name=args.strategy,
        symbol=args.symbol,
        timeframe=args.timeframe
    )
    
    scorecard = generator.generate(dummy_trades, output_dir)
    
    # 9. 결과 요약
    print(f"\n" + "=" * 60)
    print(f"✅ 백테스트 완료!")
    print(f"=" * 60)
    print(f"\n📁 산출물:")
    print(f"  - {snapshot_path}")
    print(f"  - {output_dir / 'scorecard.csv'}")
    print(f"  - {output_dir / 'scorecard.md'}")
    
    print(f"\n📊 주요 지표:")
    print(f"  - Trades: {scorecard['trades_closed']}")
    print(f"  - Winrate: {scorecard['winrate']}%")
    print(f"  - PF: {scorecard['profit_factor']}")
    print(f"  - Max DD: {scorecard['max_drawdown']}%")
    print(f"  - Loss>8%: {scorecard['loss_over_8pct']}")
    
    print(f"\n💡 다음 단계:")
    print(f"  1. scorecard.md 확인: {output_dir / 'scorecard.md'}")
    print(f"  2. 합격 기준 충족 여부 확인")
    print(f"  3. 다른 전략으로 반복 테스트")
    
    print(f"\n" + "=" * 60)


if __name__ == "__main__":
    main()
