#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE16 Paper Trading Runner
=============================
REAL Paper Mode: 실제 엔진 + PaperBroker + WebSocket feed 사용

Usage:
    python scripts/run_paper.py --duration-hours 12
    python scripts/run_paper.py --strategy scalping --symbol BTCUSDT --timeframe 3m --duration-hours 0.05

Output:
    scorecards/paper_phase16/{run_id}/
        ├─ effective_config.yml
        ├─ scorecard.csv
        ├─ scorecard.md
        └─ trades.log
"""
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.config_loader import load_config_with_mode, generate_run_id, save_effective_config
from common.logger import setup_logger
from analytics.scorecard import ScorecardGenerator

logger = setup_logger(__name__, log_type="application")


def parse_args():
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description='PHASE16: Real Paper Trading 실행',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--strategy',
        type=str,
        default='scalping',
        help='전략 이름 (기본: scalping)'
    )
    
    parser.add_argument(
        '--symbol',
        type=str,
        default='BTCUSDT',
        help='심볼 (기본: BTCUSDT)'
    )
    
    parser.add_argument(
        '--timeframe',
        type=str,
        default='3m',
        help='타임프레임 (기본: 3m - PHASE15 Best)'
    )
    
    parser.add_argument(
        '--duration-hours',
        type=float,
        default=12.0,
        help='실행 시간 (시간 단위, 기본: 12.0)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='추가 config 파일 (선택, overlay 방식)'
    )
    
    return parser.parse_args()


def main():
    """메인 함수"""
    args = parse_args()
    
    logger.info("=" * 80)
    logger.info("🚀 PHASE16 Paper Trading - REAL Mode")
    logger.info("=" * 80)
    logger.info(f"📊 Strategy: {args.strategy}")
    logger.info(f"💱 Symbol: {args.symbol}")
    logger.info(f"⏱️  Timeframe: {args.timeframe}")
    logger.info(f"⏳ Duration: {args.duration_hours:.2f} hours")
    logger.info("=" * 80)
    
    # 1. Config 로딩 (paper 모드)
    logger.info("⚙️  Config 로딩...")
    cfg = load_config_with_mode(mode="paper")
    
    # PHASE15 best 파라미터 반영 확인
    scalping_cfg = cfg.get('strategies', {}).get('scalping', {})
    logger.info(f"✅ PHASE15 Best 파라미터:")
    logger.info(f"   RR: {scalping_cfg.get('rr', 'N/A')}")
    logger.info(f"   ATR SL Mult: {scalping_cfg.get('atr_mult_sl', 'N/A')}")
    logger.info(f"   Max Hold: {scalping_cfg.get('max_hold_minutes', 'N/A')}m")
    
    # 2. CLI 오버라이드
    cfg['strategy'] = {'selector': args.strategy}
    cfg['symbol'] = args.symbol
    cfg['timeframe'] = args.timeframe
    
    # Duration 설정 (종료 시간 계산)
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=args.duration_hours)
    cfg['paper'] = cfg.get('paper', {})
    cfg['paper']['start_time'] = start_time.isoformat()
    cfg['paper']['end_time'] = end_time.isoformat()
    cfg['paper']['duration_hours'] = args.duration_hours
    
    logger.info(f"⏰ 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"⏰ 종료 예정: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 3. run_id 생성
    run_id = f"{start_time.strftime('%Y%m%d_%H%M%S')}_phase16"
    logger.info(f"🆔 Run ID: {run_id}")
    cfg['run_id'] = run_id
    
    # 4. effective_config 저장
    logger.info("💾 Effective Config 저장...")
    output_dir = Path(f"scorecards/paper_phase16/{run_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    snapshot_path = output_dir / "effective_config.yml"
    import yaml
    with open(snapshot_path, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)
    logger.info(f"  ✅ {snapshot_path}")
    
    # 5. 어댑터 생성 (REAL Paper Mode)
    logger.info("📊 어댑터 생성...")
    from execution.adapters import create_adapters
    
    try:
        feed, broker, clock = create_adapters(
            mode='paper',  # REAL Paper Mode
            symbols=[args.symbol],
            config=cfg,
            logger=logger
        )
        logger.info(f"  ✅ Feed: {type(feed).__name__}")
        logger.info(f"  ✅ Broker: {type(broker).__name__}")
        logger.info(f"  ✅ Clock: {type(clock).__name__}")
    except Exception as e:
        logger.error(f"❌ 어댑터 생성 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    # 6. 전략 로드
    logger.info(f"🎯 전략 로드: {args.strategy}")
    from strategies import load_strategies
    
    strategies = load_strategies(config=cfg)
    if args.strategy not in strategies:
        logger.error(f"❌ 전략 '{args.strategy}' 없음. 사용 가능: {list(strategies.keys())}")
        sys.exit(1)
    
    logger.info(f"  ✅ 전략 로드 완료: {list(strategies.keys())}")
    
    # 7. Paper Trading 실행 (REAL 엔진)
    logger.info("=" * 80)
    logger.info("🟢 Paper Trading 시작 (REAL Engine)")
    logger.info("=" * 80)
    
    from execution import engine
    
    try:
        # Duration 제한을 위해 config에 종료 조건 추가
        # 엔진이 이를 체크하도록 설정
        cfg['execution'] = cfg.get('execution', {})
        cfg['execution']['max_runtime_hours'] = args.duration_hours
        
        # ensemble은 사용하지 않음 (단일 전략)
        engine.run(
            feed=feed,
            broker=broker,
            clock=clock,
            strategies=strategies,
            ensemble_module=None,
            config=cfg
        )
        logger.info("✅ Paper Trading 완료")
    except KeyboardInterrupt:
        logger.info("⏹️  사용자 중단")
    except Exception as e:
        logger.error(f"❌ Paper Trading 실행 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    # 8. 거래 내역 조회 (Broker)
    logger.info("📊 거래 내역 조회...")
    
    trades = []
    if hasattr(broker, 'closed_trades'):
        trades = broker.closed_trades
        logger.info(f"  ✅ {len(trades)}개 거래 조회 완료 (Broker)")
    else:
        logger.warning("  ⚠️ Broker에 closed_trades 없음")
        trades = []
    
    # 9. Scorecard 생성 (PHASE14/15 표준 포맷)
    logger.info("📈 Scorecard 생성...")
    
    # 기간 정보
    period_info = {
        'start_date': start_time.strftime('%Y-%m-%d'),
        'end_date': datetime.now().strftime('%Y-%m-%d'),
        'actual_hours': (datetime.now() - start_time).total_seconds() / 3600,
        'mode': 'PHASE16_PAPER'
    }
    
    generator = ScorecardGenerator(
        strategy_name=args.strategy,
        symbol=args.symbol,
        timeframe=args.timeframe,
        period_info=period_info
    )
    
    try:
        scorecard = generator.generate(trades, output_dir)
        logger.info(f"  ✅ Scorecard 생성 완료")
    except Exception as e:
        logger.error(f"⚠️ Scorecard 생성 실패: {e}")
        logger.error("거래 내역이 부족하거나 포맷 문제일 수 있습니다")
        scorecard = {
            'trades_closed': len(trades),
            'winrate': 0,
            'profit_factor': 0,
            'max_drawdown': 0
        }
    
    # 10. 결과 요약
    logger.info("=" * 80)
    logger.info("✅ PHASE16 Paper Trading 완료!")
    logger.info("=" * 80)
    logger.info("\n📁 산출물:")
    logger.info(f"  - {snapshot_path}")
    logger.info(f"  - {output_dir / 'scorecard.csv'}")
    logger.info(f"  - {output_dir / 'scorecard.md'}")
    
    logger.info("\n📊 주요 지표:")
    logger.info(f"  - Trades: {scorecard.get('trades_closed', 0)}")
    logger.info(f"  - Winrate: {scorecard.get('winrate', 0)}%")
    logger.info(f"  - PF: {scorecard.get('profit_factor', 0)}")
    logger.info(f"  - Max DD: {scorecard.get('max_drawdown', 0)}%")
    
    logger.info("\n💡 다음 단계:")
    logger.info(f"  1. Scorecard 확인: {output_dir / 'scorecard.md'}")
    logger.info(f"  2. 리포트 생성: python scripts/generate_phase16_report.py --run-id {run_id}")
    logger.info("=" * 80)
    
    return scorecard


if __name__ == "__main__":
    main()
