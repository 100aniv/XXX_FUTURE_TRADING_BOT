#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
백테스트 실행 스크립트
======================
간편하게 백테스트를 실행하고 리포트를 생성하는 통합 스크립트

사용법:
python run_backtest.py --strategy scalping
python run_backtest.py --strategy ensemble
python run_backtest.py --strategy all  # 모든 전략
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
import json

# backtest 모듈 import
from backtest.backtest_engine import BacktestEngine, BacktestConfig

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# 전략별 설정
STRATEGY_CONFIGS = {
    'scalping': {
        'name': 'SCALPING',
        'description': '1분봉 스캘핑',
        'risk_per_trade': 0.015,
        'max_positions': 5,
        'fixed_rr': 1.5,
        'atr_mult_sl': 1.0,
        'atr_mult_tp': 1.5
    },
    'daytrade': {
        'name': 'DAYTRADE',
        'description': '5분봉 단타',
        'risk_per_trade': 0.02,
        'max_positions': 5,
        'fixed_rr': 2.0,
        'atr_mult_sl': 1.2,
        'atr_mult_tp': 2.4
    },
    'swing': {
        'name': 'SWING',
        'description': '15분봉 스윙',
        'risk_per_trade': 0.02,
        'max_positions': 4,
        'fixed_rr': 2.2,
        'atr_mult_sl': 1.5,
        'atr_mult_tp': 3.3
    },
    'trend': {
        'name': 'TREND',
        'description': '1시간봉 추세',
        'risk_per_trade': 0.025,
        'max_positions': 3,
        'fixed_rr': 2.5,
        'atr_mult_sl': 1.5,
        'atr_mult_tp': 3.75
    },
    'reversion': {
        'name': 'REVERSION',
        'description': '5분봉 평균회귀',
        'risk_per_trade': 0.018,
        'max_positions': 4,
        'fixed_rr': 1.8,
        'atr_mult_sl': 1.2,
        'atr_mult_tp': 2.16
    },
    'breakout': {
        'name': 'BREAKOUT',
        'description': '15분봉 돌파',
        'risk_per_trade': 0.02,
        'max_positions': 4,
        'fixed_rr': 2.0,
        'atr_mult_sl': 1.5,
        'atr_mult_tp': 3.0
    },
    'ensemble': {
        'name': 'ENSEMBLE',
        'description': '6개 전략 통합',
        'risk_per_trade': 0.02,
        'max_positions': 5,
        'fixed_rr': 2.0,
        'atr_mult_sl': 1.5,
        'atr_mult_tp': 3.0
    }
}


def check_data_files(start_date: str, end_date: str) -> bool:
    """데이터 파일 존재 확인"""
    data_dir = Path("data")
    
    required_files = [
        f"BTCUSDT_1m_{start_date}_{end_date}.csv",
        f"BTCUSDT_5m_{start_date}_{end_date}.csv",
        f"BTCUSDT_15m_{start_date}_{end_date}.csv",
        f"BTCUSDT_1h_{start_date}_{end_date}.csv",
    ]
    
    missing = []
    for file in required_files:
        if not (data_dir / file).exists():
            missing.append(file)
    
    if missing:
        logger.error("❌ 필요한 데이터 파일이 없습니다:")
        for f in missing:
            logger.error(f"   - {f}")
        logger.error("\n데이터 다운로드를 먼저 실행하세요:")
        logger.error(f"   python backtest/data_downloader.py --start {start_date} --end {end_date}")
        logger.error(f"   python backtest/data_downloader.py --merge")
        return False
    
    logger.info("✅ 데이터 파일 확인 완료")
    return True


def run_single_backtest(strategy: str, start_date: str, end_date: str, 
                       capital: float, generate_report: bool = True) -> dict:
    """개별 전략 백테스트 실행"""
    
    if strategy not in STRATEGY_CONFIGS:
        logger.error(f"❌ 알 수 없는 전략: {strategy}")
        logger.error(f"   사용 가능한 전략: {', '.join(STRATEGY_CONFIGS.keys())}")
        return None
    
    config = STRATEGY_CONFIGS[strategy]
    
    logger.info("=" * 80)
    logger.info(f"🚀 백테스트 시작: {config['name']}")
    logger.info(f"   설명: {config['description']}")
    logger.info(f"   기간: {start_date} ~ {end_date}")
    logger.info(f"   자본: {capital:,.0f} USDT")
    logger.info(f"   리스크: {config['risk_per_trade']*100:.1f}% per trade")
    logger.info(f"   RR: {config['fixed_rr']}")
    logger.info("=" * 80)
    
    # BacktestConfig 생성
    bt_config = BacktestConfig(
        strategy=strategy,
        start_date=start_date,
        end_date=end_date,
        initial_capital=capital,
        risk_per_trade=config['risk_per_trade'],
        max_positions=config['max_positions'],
        fixed_rr=config['fixed_rr'],
        atr_mult_sl=config['atr_mult_sl'],
        atr_mult_tp=config['atr_mult_tp'],
        data_dir=str(Path("data"))
    )
    
    # BacktestEngine 생성
    engine = BacktestEngine(bt_config)
    
    # 백테스트 실행 (BTCUSDT, 5m)
    try:
        metrics = engine.run_strategy_backtest(symbol="BTCUSDT", interval="5m")
        
        # 결과 변환
        result = {
            'strategy': strategy,
            'config': config,
            'metrics': {
                'total_trades': metrics.total_trades,
                'winning_trades': metrics.winning_trades,
                'losing_trades': metrics.losing_trades,
                'win_rate': metrics.win_rate,
                'avg_win': metrics.avg_win,
                'avg_loss': metrics.avg_loss,
                'profit_factor': metrics.profit_factor,
                'total_return': metrics.total_return,
                'total_return_pct': metrics.total_return_pct,
                'max_drawdown': metrics.max_drawdown,
                'max_drawdown_pct': metrics.max_drawdown_pct,
                'sharpe_ratio': metrics.sharpe_ratio,
                'sortino_ratio': metrics.sortino_ratio,
                'max_consecutive_wins': metrics.max_consecutive_wins,
                'max_consecutive_losses': metrics.max_consecutive_losses
            },
            'trades': [
                {
                    'trade_id': t.trade_id,
                    'symbol': t.symbol,
                    'side': t.side.value,
                    'entry_time': t.entry_time.isoformat(),
                    'entry_price': t.entry_price,
                    'quantity': t.quantity,
                    'exit_time': t.exit_time.isoformat() if t.exit_time else None,
                    'exit_price': t.exit_price,
                    'exit_reason': t.exit_reason,
                    'pnl': t.pnl,
                    'pnl_pct': t.pnl_pct
                }
                for t in engine.trades
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ 백테스트 실행 오류: {e}")
        import traceback
        traceback.print_exc()
        
        result = {
            'strategy': strategy,
            'config': config,
            'error': str(e),
            'metrics': {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_return_pct': 0.0,
                'sharpe_ratio': 0.0
            }
        }
    
    # 결과 저장
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = results_dir / f"{strategy}_backtest_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    logger.info(f"💾 결과 저장: {output_file}")
    
    # 리포트 생성
    if generate_report:
        logger.info("📊 리포트 생성 중...")
        # TODO: backtest_reporter.py 호출
        logger.info("⚠️  리포트 생성 기능은 백테스트 로직 완성 후 활성화됩니다.")
    
    return result


def run_all_backtests(start_date: str, end_date: str, capital: float):
    """모든 전략 백테스트 실행"""
    logger.info("=" * 80)
    logger.info("🎯 전체 전략 백테스트 시작")
    logger.info("=" * 80)
    
    strategies = ['scalping', 'daytrade', 'swing', 'trend', 'reversion', 'breakout']
    results = {}
    
    for i, strategy in enumerate(strategies, 1):
        logger.info(f"\n[{i}/{len(strategies)}] {strategy.upper()} 백테스트...")
        result = run_single_backtest(strategy, start_date, end_date, capital, 
                                     generate_report=False)
        if result:
            results[strategy] = result
    
    # 앙상블 백테스트
    logger.info(f"\n[7/7] ENSEMBLE 백테스트...")
    ensemble_result = run_single_backtest('ensemble', start_date, end_date, 
                                          capital, generate_report=False)
    if ensemble_result:
        results['ensemble'] = ensemble_result
    
    # 비교 리포트 생성
    generate_comparison_report(results)
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ 전체 백테스트 완료!")
    logger.info("=" * 80)


def generate_comparison_report(results: dict):
    """전략 비교 리포트 생성"""
    logger.info("\n" + "=" * 80)
    logger.info("📊 전략 비교 요약")
    logger.info("=" * 80)
    
    # 테이블 헤더
    print(f"\n{'전략':<12} {'거래수':>8} {'승률':>8} {'수익률':>10} {'샤프':>8}")
    print("-" * 60)
    
    # 각 전략 출력
    for strategy, result in results.items():
        metrics = result['metrics']
        win_rate = metrics.get('win_rate', 0) * 100
        total_return = metrics.get('total_return_pct', 0)
        sharpe = metrics.get('sharpe_ratio', 0)
        total_trades = metrics.get('total_trades', 0)
        
        print(f"{strategy.upper():<12} "
              f"{total_trades:>8} "
              f"{win_rate:>7.2f}% "
              f"{total_return:>9.2f}% "
              f"{sharpe:>8.2f}")
    
    print("-" * 60)
    
    # 비교 리포트 저장
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    comparison_file = reports_dir / f"strategy_comparison_{timestamp}.json"
    
    with open(comparison_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"\n💾 비교 리포트 저장: {comparison_file}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="백테스트 실행 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python run_backtest.py --strategy scalping
  python run_backtest.py --strategy ensemble
  python run_backtest.py --strategy all --start 2024-07-01 --end 2024-10-17
  python run_backtest.py --strategy scalping --capital 50000
        """
    )
    
    parser.add_argument(
        '--strategy',
        required=True,
        choices=list(STRATEGY_CONFIGS.keys()) + ['all'],
        help='백테스트할 전략'
    )
    
    parser.add_argument(
        '--start',
        default='2024-07-01',
        help='시작 날짜 (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end',
        default='2024-10-17',
        help='종료 날짜 (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--capital',
        type=float,
        default=10000,
        help='초기 자본 (USDT)'
    )
    
    parser.add_argument(
        '--no-report',
        action='store_true',
        help='리포트 생성 건너뛰기'
    )
    
    parser.add_argument(
        '--check-data',
        action='store_true',
        help='데이터 파일만 확인'
    )
    
    args = parser.parse_args()
    
    # 데이터 확인
    if args.check_data or args.strategy != 'all':
        if not check_data_files(args.start, args.end):
            sys.exit(1)
        
        if args.check_data:
            logger.info("✅ 데이터 파일 확인 완료!")
            return
    
    # 백테스트 실행
    if args.strategy == 'all':
        run_all_backtests(args.start, args.end, args.capital)
    else:
        run_single_backtest(
            args.strategy,
            args.start,
            args.end,
            args.capital,
            generate_report=not args.no_report
        )


if __name__ == "__main__":
    main()
