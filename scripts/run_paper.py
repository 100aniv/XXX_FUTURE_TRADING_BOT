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
import signal  # PHASE18-3: Signal handling
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.config_loader import load_config_with_mode, generate_run_id, save_effective_config
from common.logger import setup_logger
from common.runtime_context import RuntimeContext  # PHASE18-3: Graceful Shutdown
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
        '--duration-mode',
        type=str,
        choices=['market_time', 'wall_clock'],
        default='market_time',
        help='Duration 평가 기준 (기본: market_time / REAL PAPER는 wall_clock 권장)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='추가 config 파일 (선택, overlay 방식)'
    )
    
    parser.add_argument(
        '--clean-state',
        action='store_true',
        default=False,
        help='실행 전 Redis/로그 초기화 (PHASE18-1)'
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
    
    # 0. Clean-State 초기화 (PHASE18-1)
    if args.clean_state:
        logger.info("🔧 Clean-State 초기화 중...")
        import subprocess
        init_script = project_root / "scripts" / "ops" / "init_clean_state.py"
        result = subprocess.run(
            [sys.executable, str(init_script)],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info("✅ Clean-State 초기화 완료")
        else:
            logger.warning(f"⚠️ Clean-State 초기화 실패 (계속 진행)")
            if result.stderr:
                logger.warning(f"   Error: {result.stderr[:200]}")
    
    # 1. Config 로딩 (paper 모드)
    logger.info("⚙️  Config 로딩...")
    
    # ⭐ PHASE21: --config 인자 지원
    if args.config:
        import yaml
        logger.info(f"📝 Custom config 로딩: {args.config}")
        
        # ⭐ PHASE21-1B: base.yml과 merge하여 누락된 필수 키 채우기
        # 1. base.yml 로드
        base_config_path = Path("configs/base.yml")
        if base_config_path.exists():
            with open(base_config_path, 'r', encoding='utf-8') as f:
                base_cfg = yaml.safe_load(f)
        else:
            base_cfg = {}
            logger.warning("⚠️ base.yml 없음, custom config만 사용")
        
        # 2. custom config 로드
        with open(args.config, 'r', encoding='utf-8') as f:
            custom_cfg = yaml.safe_load(f)
        
        # 3. Deep merge: base에 custom 덮어쓰기
        def deep_merge(base, custom):
            """Deep merge two dicts: base에 custom 덮어쓰기"""
            merged = base.copy()
            for key, value in custom.items():
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = deep_merge(merged[key], value)
                else:
                    merged[key] = value
            return merged
        
        cfg = deep_merge(base_cfg, custom_cfg)
        logger.info("✅ base.yml + custom config merge 완료")
        
        # ⭐ PHASE21-1B: feed.base_timeframe 동기화 (collector timeframe 버그 수정)
        # Custom config의 timeframe을 feed.base_timeframe에도 반영하여
        # WebSocket collector가 올바른 timeframe을 사용하도록 함
        if 'timeframe' in cfg:
            if 'feed' not in cfg:
                cfg['feed'] = {}
            cfg['feed']['base_timeframe'] = cfg['timeframe']
            logger.info(f"✅ feed.base_timeframe 동기화: {cfg['timeframe']}")
    else:
        cfg = load_config_with_mode(mode="paper")
    
    # ⭐ CRITICAL: mode를 paper로 강제 설정
    cfg['mode'] = 'paper'
    
    # ⭐ CRITICAL: Redis 환경변수를 실제 값으로 대체
    if 'monitoring' in cfg and 'redis' in cfg['monitoring']:
        redis_cfg = cfg['monitoring']['redis']
        if isinstance(redis_cfg.get('host'), str) and redis_cfg['host'].startswith('${'):
            redis_cfg['host'] = 'localhost'
        if isinstance(redis_cfg.get('port'), str) and str(redis_cfg['port']).startswith('${'):
            redis_cfg['port'] = 6379
        elif isinstance(redis_cfg.get('port'), int):
            pass  # 이미 정수면 OK
        else:
            redis_cfg['port'] = 6379
    
    # ⭐ PHASE16+: Paper 테스트용 완화 설정 자동 오버레이
    paper_test_config_path = Path("configs/scalping/paper_testing.yml")
    if paper_test_config_path.exists():
        logger.info("📝 Paper 테스트 설정 로드 중...")
        import yaml
        with open(paper_test_config_path, 'r', encoding='utf-8') as f:
            paper_overlay = yaml.safe_load(f)
        
        # Deep merge (portfolio, execution, risk, strategies)
        for section in ['portfolio', 'execution', 'risk', 'strategies']:
            if section in paper_overlay:
                if section not in cfg:
                    cfg[section] = {}
                cfg[section].update(paper_overlay[section])
        
        logger.info(f"  ✅ Portfolio cooldown: {cfg.get('portfolio', {}).get('symbol_cooldown_seconds', 'N/A')}s")
        logger.info(f"  ✅ Max positions: {cfg.get('risk', {}).get('max_positions', 'N/A')}")
    else:
        logger.warning(f"⚠️  Paper 테스트 설정 없음: {paper_test_config_path}")
    
    # PHASE15 best 파라미터 반영 확인
    scalping_cfg = cfg.get('strategies', {}).get('scalping', {})
    logger.info(f"✅ PHASE15 Best 파라미터:")
    logger.info(f"   RR: {scalping_cfg.get('rr', 'N/A')}")
    logger.info(f"   ATR SL Mult: {scalping_cfg.get('atr_mult_sl', 'N/A')}")
    logger.info(f"   Max Hold: {scalping_cfg.get('max_hold_minutes', 'N/A')}m")
    
    # 2. CLI 오버라이드 (config 파일이 없거나 CLI 인자가 명시된 경우)
    if not args.config:
        # Default behavior: Use CLI args
        cfg['strategy'] = {'selector': args.strategy}
        cfg['symbol'] = args.symbol
        cfg['timeframe'] = args.timeframe
    else:
        # Config file provided: Use config values unless CLI explicitly overrides
        if 'strategy' not in cfg:
            cfg['strategy'] = {}
        
        # ⭐ PHASE21-1B: strategy.selected → strategy.selector 변환
        # base.yml의 selector: null 케이스도 처리
        if 'selected' in cfg.get('strategy', {}):
            if cfg['strategy'].get('selector') is None:
                cfg['strategy']['selector'] = cfg['strategy']['selected']
                logger.info(f"✅ strategy.selected → strategy.selector: {cfg['strategy']['selector']}")
        
        if 'symbols' in cfg and isinstance(cfg['symbols'], list):
            # Config has symbols list, use first one for backward compat
            cfg['symbol'] = cfg['symbols'][0]
        elif 'symbol' not in cfg:
            cfg['symbol'] = args.symbol
    
    # ⭐ PHASE18-2: env 명시적 설정 (네임스페이스용)
    cfg['env'] = 'paper'
    
    # Duration 설정 (종료 시간 계산)
    # ⭐ PHASE21: config 파일의 duration_hours 우선 사용
    duration_hours = cfg.get('duration_hours', args.duration_hours)
    duration_mode = cfg.get('duration_mode', args.duration_mode)
    
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=duration_hours)
    cfg['paper'] = cfg.get('paper', {})
    cfg['paper']['start_time'] = start_time.isoformat()
    cfg['paper']['end_time'] = end_time.isoformat()
    cfg['paper']['duration_hours'] = duration_hours
    cfg['paper']['duration_mode'] = duration_mode  # ⭐ PHASE16+: Duration 모드 설정
    cfg['paper']['clean_start'] = True  # ⭐ PHASE16+: 깨끗한 시작 (기존 포지션 무시)
    
    logger.info(f"⏰ 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"⏰ 종료 예정: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📍 Duration 모드: {args.duration_mode} ({args.duration_hours:.2f}h)")
    
    # 3. run_id 생성 (⭐ PHASE18-2: generate_run_id 사용)
    run_id = generate_run_id()
    logger.info(f"🆔 Run ID: {run_id}")
    cfg['run_id'] = run_id
    
    # ⭐ PHASE18-3: Runtime Context 생성 및 Signal Handler 등록
    runtime_ctx = RuntimeContext()
    runtime_ctx.run_id = run_id
    runtime_ctx.env = 'paper'
    cfg['runtime_context'] = runtime_ctx
    
    shutdown_requested = [False]  # mutable state for signal handler
    
    def signal_handler(signum, frame):
        sig_name = 'SIGINT' if signum == signal.SIGINT else f'Signal {signum}'
        if shutdown_requested[0]:
            logger.warning(f"🚨 강제 종료 (두 번째 시그널: {sig_name})")
            sys.exit(1)
        
        logger.info(f"🛑 Shutdown signal received: {sig_name}")
        shutdown_requested[0] = True
        reason = runtime_ctx.request_shutdown(reason=sig_name)
        logger.info(f"✅ Graceful shutdown requested: {reason}")
    
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    logger.info("✅ Signal handlers registered (SIGINT, SIGTERM)")
    
    # ⭐ PHASE18-4: 모니터링 시스템 초기화
    from common.monitoring import setup_monitoring
    try:
        setup_monitoring(runtime_ctx, cfg)
        logger.info("✅ 모니터링 시스템 초기화 완료")
    except Exception as e:
        logger.warning(f"⚠️ 모니터링 시스템 초기화 실패: {e}")
    
    # 4. effective_config 저장
    logger.info("💾 Effective Config 저장...")
    output_dir = Path(f"scorecards/paper_phase16/{run_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    snapshot_path = output_dir / "effective_config.yml"
    import yaml
    # ⭐ PHASE18-3: runtime_context는 직렬화 불가 (threading.Event 포함)
    cfg_snapshot = {k: v for k, v in cfg.items() if k != 'runtime_context'}
    with open(snapshot_path, 'w', encoding='utf-8') as f:
        yaml.dump(cfg_snapshot, f, default_flow_style=False, allow_unicode=True)
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
    
    # ⭐ PHASE16+: Paper 모드 포트폴리오 초기화
    # 기존 포지션이 있으면 모두 청산 (깨끗한 시작)
    if hasattr(broker, 'open_positions') and broker.open_positions:
        logger.warning(f"⚠️  기존 포지션 {len(broker.open_positions)}개 감지")
        logger.info("🔄 Paper 모드: 기존 포지션 초기화 중...")
        try:
            # 모든 포지션 청산
            for symbol, position in list(broker.open_positions.items()):
                logger.info(f"  - {symbol}: {position.get('qty', 0)} 청산")
            broker.open_positions.clear()
            logger.info(f"  ✅ 포트폴리오 초기화 완료 (0개)")
        except Exception as e:
            logger.warning(f"  ⚠️  포트폴리오 초기화 실패: {e}")
    
    # 6. 전략 로드
    # ⭐ PHASE21-1C: config 파일 사용 시 cfg['strategy']['selector'] 우선
    actual_strategy = cfg.get('strategy', {}).get('selector') or args.strategy
    logger.info(f"🎯 전략 로드: {actual_strategy}")
    from strategies import load_strategies
    
    strategies = load_strategies(config=cfg)
    if actual_strategy not in strategies:
        logger.error(f"❌ 전략 '{actual_strategy}' 없음. 사용 가능: {list(strategies.keys())}")
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
        logger.info("⏹️  사용자 중단 (KeyboardInterrupt)")
        runtime_ctx.request_shutdown(reason="KeyboardInterrupt")
    except Exception as e:
        logger.error(f"❌ Paper Trading 실행 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        # ⭐ PHASE18-3: 리소스 정리 (Graceful Shutdown)
        logger.info("🧹 리소스 정리 시작...")
        
        # ⭐ PHASE18-4: 모니터링 시스템 중지
        if runtime_ctx and runtime_ctx.monitor_registry:
            try:
                runtime_ctx.monitor_registry.stop_all()
                logger.info("  ✅ 모니터링 중지 완료")
            except Exception as e:
                logger.warning(f"  ⚠️ 모니터링 중지 실패: {e}")
        
        if hasattr(feed, 'stop'):
            try:
                feed.stop()
                logger.info("  ✅ Feed 중지 완료")
            except Exception as e:
                logger.warning(f"  ⚠️ Feed 중지 실패: {e}")
        logger.info("✅ Shutdown complete")
    
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
