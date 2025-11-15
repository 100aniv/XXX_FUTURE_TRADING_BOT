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
from common.logger import setup_logger
from analytics.scorecard import ScorecardGenerator

logger = setup_logger(__name__, log_type="application")


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
        choices=['backtest_clean', 'backtest_raw', 'backtest', 'paper', 'live'],
        help='실행 모드 (PHASE8: backtest_clean, PHASE9: backtest_raw 연구용)'
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
        '--use-db',
        action='store_true',
        default=False,
        help='백테스트 모드에서 DB 사용 여부 (기본: False, CSV만 사용)'
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        default=None,
        help='시작 날짜 (예: 2024-10-01, days보다 우선)'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        default=None,
        help='종료 날짜 (예: 2024-10-31, days보다 우선)'
    )
    
    parser.add_argument(
        '--timerange',
        type=str,
        default=None,
        help='날짜 범위 (예: 2023-04-01:2023-04-05) [deprecated, use --start-date/--end-date]'
    )
    
    parser.add_argument(
        '--data-path',
        type=str,
        default=None,
        help='데이터 파일 경로 (기본값: data/{symbol}_{timeframe}.csv)'
    )
    
    parser.add_argument(
        '--overlay-config',
        type=str,
        default=None,
        help='오버레이 설정 파일 경로 (튜닝용, YAML)'
    )
    
    return parser.parse_args()


def main():
    """메인 실행 함수 (PHASE8-2: 실제 엔진 연동)"""
    print("=" * 60)
    print("PHASE8-2 Backtest Runner (Engine Integrated)")
    print("=" * 60)
    
    # 1. CLI 인자 파싱
    args = parse_args()
    
    logger.info(f"📋 설정: mode={args.mode}, strategy={args.strategy}, symbol={args.symbol}, tf={args.timeframe}")
    if args.days:
        logger.info(f"  - Days: {args.days}")
    if args.start_date or args.end_date:
        logger.info(f"  - Period: {args.start_date or 'start'} ~ {args.end_date or 'end'}")
    if args.timerange:
        logger.info(f"  - Timerange: {args.timerange}")
    
    # 2. Config 로드 (병합 순서)
    logger.info("🔧 Config 로드 및 병합...")
    cfg = load_config_with_mode(mode=args.mode)
    
    # Overlay config 병합 (튜닝용)
    if args.overlay_config:
        import yaml
        from common.config_loader import deep_merge
        logger.info(f"🔀 Overlay config 병합: {args.overlay_config}")
        with open(args.overlay_config, 'r', encoding='utf-8') as f:
            overlay = yaml.safe_load(f)
        cfg = deep_merge(cfg, overlay)
        logger.info("✅ Overlay 병합 완료")
        
        # 🔍 디버그: 병합된 전략 파라미터 출력
        if 'strategies' in cfg and args.strategy in cfg['strategies']:
            strategy_cfg = cfg['strategies'][args.strategy]
            logger.info(f"[OVERLAY] Final merged {args.strategy} params:")
            for key, val in strategy_cfg.items():
                if key == "filters" and isinstance(val, dict):
                    logger.info(f"  filters:")
                    for fk, fv in val.items():
                        logger.info(f"    {fk}: {fv}")
                else:
                    logger.info(f"  {key}: {val}")
    
    # CLI 인자로 config 오버라이드
    cfg['mode'] = args.mode
    cfg['symbol'] = args.symbol
    cfg['symbols_list'] = [args.symbol]  # 단일 심볼
    cfg['timeframe'] = args.timeframe
    cfg['strategy'] = {'use_ensemble': False, 'selector': args.strategy}
    
    # ⭐ PHASE9 CRITICAL FIX: 전략 타임프레임을 CLI 타임프레임으로 강제 override
    if 'strategies' not in cfg:
        cfg['strategies'] = {}
    if args.strategy not in cfg['strategies']:
        cfg['strategies'][args.strategy] = {}
    cfg['strategies'][args.strategy]['timeframe'] = args.timeframe
    logger.info(f"✅ 전략 타임프레임 강제 설정: {args.strategy}.timeframe = {args.timeframe}")
    
    # 백테스트 설정 추가
    if 'backtest' not in cfg:
        cfg['backtest'] = {}
    cfg['backtest']['symbol'] = args.symbol
    cfg['backtest']['data_dir'] = 'data'
    if args.data_path:
        cfg['backtest']['data_file'] = args.data_path
    else:
        # ⭐ PHASE9: OOS 데이터 기본값 (PHASE8-5에서 검증된 완벽한 데이터)
        cfg['backtest']['data_file'] = 'BTCUSDT_5m_2024-10-01_2024-12-31_OOS.csv'
    # ⭐ PHASE8-4/5: days, start_date, end_date 파라미터 config에 저장
    if args.days:
        cfg['backtest']['days'] = args.days
    if args.start_date:
        cfg['backtest']['start_date'] = args.start_date
    if args.end_date:
        cfg['backtest']['end_date'] = args.end_date
    
    # 3. Config 검증
    logger.info("✓ Config 검증...")
    try:
        validate_config(cfg)
    except Exception as e:
        logger.error(f"❌ Config 검증 실패: {e}")
        sys.exit(1)
    
    # 4. run_id 생성
    run_id = generate_run_id()
    logger.info(f"🆔 Run ID: {run_id}")
    cfg['run_id'] = run_id  # config에 추가
    
    # 5. effective_config.yml 스냅샷 저장
    logger.info("💾 Effective Config 저장...")
    snapshot_path = save_effective_config(cfg, args.mode, run_id)
    logger.info(f"  - {snapshot_path}")
    
    # 6. 어댑터 생성 (feed, broker, clock)
    logger.info("📊 어댑터 생성...")
    from execution.adapters import create_adapters
    
    try:
        feed, broker, clock = create_adapters(
            mode='backtest',  # adapters에서는 'backtest' 사용
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
    
    # 7. DB 완전 초기화 (backtest 모드 격리) - Optional
    if args.use_db:
        # ⭐ LAZY: DB 사용 시에만 import
        from common.database import get_db_connection
        
        logger.info("=" * 60)
        logger.info(f"🗑️  [DB CLEANUP] {args.mode} 모드 완전 격리 시작")
        logger.info("=" * 60)
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # 1. trading.trades 삭제 전 카운트
                    cur.execute("SELECT COUNT(*) FROM trading.trades WHERE mode = %s", (args.mode,))
                    before_trades = cur.fetchone()[0]
                    logger.info(f"📊 [BEFORE] trading.trades ({args.mode}): {before_trades}개")
                    
                    # 2. trading.trades 삭제
                    cur.execute("DELETE FROM trading.trades WHERE mode = %s", (args.mode,))
                    deleted_trades = cur.rowcount
                    conn.commit()
                    logger.info(f"  ✅ trading.trades 삭제: {deleted_trades}개")
                    
                    # 3. 기타 테이블 정리 시도 (없으면 무시)
                    tables_to_clean = [
                        ('trading.positions', 'mode'),  # 포지션 테이블 (있으면)
                        ('trading.metrics', 'env'),      # 메트릭 테이블 (있으면)
                        ('trading.signals', 'mode'),     # 신호 테이블 (있으면)
                    ]
                    
                    for table_name, mode_column in tables_to_clean:
                        try:
                            # 삭제 전 카운트
                            cur.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {mode_column} = %s", (args.mode,))
                            before_count = cur.fetchone()[0]
                            
                            if before_count > 0:
                                # 삭제
                                cur.execute(f"DELETE FROM {table_name} WHERE {mode_column} = %s", (args.mode,))
                                deleted_count = cur.rowcount
                                conn.commit()
                                logger.info(f"  ✅ {table_name} 삭제: {deleted_count}개")
                        except Exception:
                            # 테이블이 없으면 무시
                            pass
                    
                    # 4. 삭제 후 최종 확인
                    cur.execute("SELECT COUNT(*) FROM trading.trades WHERE mode = %s", (args.mode,))
                    after_trades = cur.fetchone()[0]
                    
                    logger.info("=" * 60)
                    logger.info(f"✅ [AFTER] trading.trades ({args.mode}): {after_trades}개")
                    logger.info(f"✅ [DB CLEANUP] 완전 격리 완료 ({deleted_trades}개 삭제됨)")
                    logger.info("=" * 60)
                    
        except Exception as e:
            logger.error(f"❌ DB 초기화 실패: {e}")
            logger.error("백테스트 계속 진행하지만 결과가 오염될 수 있음")
            import traceback
            logger.error(traceback.format_exc())
    else:
        logger.info("ℹ️  [DB SKIP] --use-db 플래그 없음, DB 연결 생략 (CSV 전용 모드)")
    
    # 8. 전략 로드
    logger.info(f"🎯 전략 로드: {args.strategy}")
    from strategies import load_strategies
    
    strategies = load_strategies(config=cfg)
    if args.strategy not in strategies:
        logger.error(f"❌ 전략 '{args.strategy}' 없음. 사용 가능: {list(strategies.keys())}")
        sys.exit(1)
    
    logger.info(f"  ✅ 전략 로드 완료: {list(strategies.keys())}")
    
    # 9. 백테스트 실행 (실제 엔진)
    logger.info("⚙️  백테스트 엔진 실행...")
    from execution import engine
    
    try:
        # ensemble은 사용하지 않음 (단일 전략만)
        engine.run(
            feed=feed,
            broker=broker,
            clock=clock,
            strategies=strategies,
            ensemble_module=None,  # 단일 전략
            config=cfg
        )
        logger.info("✅ 백테스트 완료")
    except Exception as e:
        logger.error(f"❌ 백테스트 실행 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    # 10. 거래 내역 조회 (DB) - Optional
    logger.info("📊 거래 내역 조회...")
    
    trades = []
    if args.use_db:
        # ⭐ LAZY: DB 사용 시에만 import
        from common.database import get_db_connection
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # backtest_clean 모드로 저장된 CLOSED 거래 조회
                    cur.execute("""
                        SELECT trade_id, symbol, strategy_id, side, 
                               entry_price, quantity, sl_price, tp_price,
                               leverage, ts_open, ts_close, pnl, pnl_pct, status, exit_reason
                        FROM trading.trades
                        WHERE mode = %s AND status = 'CLOSED'
                        ORDER BY ts_close DESC
                    """, (args.mode,))
                    
                    rows = cur.fetchall()
                    for row in rows:
                        trades.append({
                            'trade_id': row[0],
                            'symbol': row[1],
                            'strategy_id': row[2],
                            'side': row[3],
                            'entry_price': float(row[4]) if row[4] else 0,
                            'quantity': float(row[5]) if row[5] else 0,
                            'sl_price': float(row[6]) if row[6] else 0,
                            'tp_price': float(row[7]) if row[7] else 0,
                            'leverage': float(row[8]) if row[8] else 1,
                            'ts_open': row[9],
                            'ts_close': row[10],
                            'pnl': float(row[11]) if row[11] else 0,
                            'pnl_pct': float(row[12]) if row[12] else 0,
                            'status': row[13],
                            'exit_reason': row[14]
                        })
            
            logger.info(f"  ✅ {len(trades)}개 거래 조회 완료 (DB)")
        except Exception as e:
            logger.warning(f"⚠️ DB 조회 실패: {e}")
            logger.warning("엔진 내부 메트릭으로 scorecard 생성")
            trades = []
    else:
        logger.info("  ℹ️  DB 미사용 모드: 엔진 내부 메트릭으로 scorecard 생성")
        trades = []
    
    # 11. Scorecard 생성
    logger.info("📈 Scorecard 생성...")
    output_dir = Path(f"artifacts/{args.mode}/{run_id}")
    
    # ⭐ PHASE8-4: feed 객체에서 실제 사용 기간 정보 추출
    period_info = {}
    if hasattr(feed, 'first_used_ts') and hasattr(feed, 'last_used_ts'):
        if feed.first_used_ts and feed.last_used_ts:
            period_info['start_date'] = feed.first_used_ts.strftime('%Y-%m-%d')
            period_info['end_date'] = feed.last_used_ts.strftime('%Y-%m-%d')
            period_info['actual_days'] = (feed.last_used_ts - feed.first_used_ts).days
            
            logger.info(f"  📅 실제 사용 기간: {period_info['start_date']} ~ {period_info['end_date']} ({period_info['actual_days']}일)")
    
    generator = ScorecardGenerator(
        strategy_name=args.strategy,
        symbol=args.symbol,
        timeframe=args.timeframe,
        period_info=period_info  # 기간 정보 전달
    )
    
    scorecard = generator.generate(trades, output_dir)
    
    # 12. 결과 요약
    logger.info("=" * 60)
    logger.info("✅ 백테스트 완료!")
    logger.info("=" * 60)
    logger.info("\n📁 산출물:")
    logger.info(f"  - {snapshot_path}")
    logger.info(f"  - {output_dir / 'scorecard.csv'}")
    logger.info(f"  - {output_dir / 'scorecard.md'}")
    
    logger.info("\n📊 주요 지표:")
    logger.info(f"  - Trades: {scorecard['trades_closed']}")
    logger.info(f"  - Winrate: {scorecard['winrate']}%")
    logger.info(f"  - PF: {scorecard['profit_factor']}")
    logger.info(f"  - Max DD: {scorecard['max_drawdown']}%")
    logger.info(f"  - Loss>8%: {scorecard['loss_over_8pct']}")
    
    logger.info("\n💡 Scorecard 확인:")
    logger.info(f"  {output_dir / 'scorecard.md'}")
    
    logger.info("=" * 60)
    
    return scorecard


if __name__ == "__main__":
    main()
