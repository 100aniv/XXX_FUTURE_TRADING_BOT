#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE22-1: Single-Symbol Ensemble v1 Integration Runner
========================================================
목표: 4개 IMPLEMENTED 전략 (scalping, breakout, reversion, trend) 통합 테스트
Runtime: 30분 wall-clock Paper 테스트
Symbol: BTCUSDT (단일 심볼)

Usage:
    python scripts/run_phase22_ensemble_single_symbol.py
    python scripts/run_phase22_ensemble_single_symbol.py --config configs/paper/phase22_ensemble_single_symbol.yml
    python scripts/run_phase22_ensemble_single_symbol.py --duration-hours 0.5

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
import signal
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.config_loader import load_config_with_mode, generate_run_id, save_effective_config
from common.logger import setup_logger
from common.runtime_context import RuntimeContext
from analytics.scorecard import ScorecardGenerator

logger = setup_logger(__name__, log_type="application")


def parse_args():
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description='PHASE22-1: Single-Symbol Ensemble v1 Integration',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='configs/paper/phase22_ensemble_single_symbol.yml',
        help='Config 파일 경로 (기본: configs/paper/phase22_ensemble_single_symbol.yml)'
    )
    
    parser.add_argument(
        '--duration-hours',
        type=float,
        default=0.5,
        help='실행 시간 (시간 단위, 기본: 0.5 = 30분)'
    )
    
    parser.add_argument(
        '--duration-mode',
        type=str,
        choices=['market_time', 'wall_clock'],
        default='wall_clock',
        help='Duration 평가 기준 (기본: wall_clock)'
    )
    
    parser.add_argument(
        '--clean-state',
        action='store_true',
        default=False,
        help='실행 전 Redis/로그 초기화'
    )
    
    return parser.parse_args()


def main():
    """메인 함수"""
    args = parse_args()
    
    logger.info("=" * 80)
    logger.info("🚀 PHASE22-1: Single-Symbol Ensemble v1 Integration")
    logger.info("=" * 80)
    logger.info(f"📝 Config: {args.config}")
    logger.info(f"⏳ Duration: {args.duration_hours:.2f} hours ({args.duration_hours * 60:.0f}min)")
    logger.info(f"📍 Duration Mode: {args.duration_mode}")
    logger.info("=" * 80)
    
    # 0. Clean-State 초기화 (optional)
    if args.clean_state:
        logger.info("🔧 Clean-State 초기화 중...")
        import subprocess
        init_script = project_root / "scripts" / "ops" / "init_clean_state.py"
        if init_script.exists():
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
        else:
            logger.warning("⚠️ init_clean_state.py 없음, skip")
    
    # 1. Config 로딩
    logger.info("⚙️  Config 로딩...")
    
    if args.config and Path(args.config).exists():
        import yaml
        logger.info(f"📝 Custom config 로딩: {args.config}")
        
        # base.yml 로드
        base_config_path = Path("configs/base.yml")
        if base_config_path.exists():
            with open(base_config_path, 'r', encoding='utf-8') as f:
                base_cfg = yaml.safe_load(f)
        else:
            base_cfg = {}
            logger.warning("⚠️ base.yml 없음, custom config만 사용")
        
        # custom config 로드
        with open(args.config, 'r', encoding='utf-8') as f:
            custom_cfg = yaml.safe_load(f)
        
        # Deep merge
        def deep_merge(base, custom):
            merged = base.copy()
            for key, value in custom.items():
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = deep_merge(merged[key], value)
                else:
                    merged[key] = value
            return merged
        
        cfg = deep_merge(base_cfg, custom_cfg)
        logger.info("✅ base.yml + custom config merge 완료")
        
        # feed.base_timeframe 동기화
        if 'timeframe' in cfg:
            if 'feed' not in cfg:
                cfg['feed'] = {}
            cfg['feed']['base_timeframe'] = cfg['timeframe']
            logger.info(f"✅ feed.base_timeframe 동기화: {cfg['timeframe']}")
    else:
        cfg = load_config_with_mode(mode="paper")
        logger.warning(f"⚠️ Config 파일 없음 ({args.config}), 기본 config 사용")
    
    # mode를 paper로 강제 설정
    cfg['mode'] = 'paper'
    cfg['env'] = 'paper'
    
    # Redis 환경변수를 실제 값으로 대체
    if 'monitoring' in cfg and 'redis' in cfg['monitoring']:
        redis_cfg = cfg['monitoring']['redis']
        if isinstance(redis_cfg.get('host'), str) and redis_cfg['host'].startswith('${'):
            redis_cfg['host'] = 'localhost'
        if isinstance(redis_cfg.get('port'), str) and str(redis_cfg['port']).startswith('${'):
            redis_cfg['port'] = 6379
        elif isinstance(redis_cfg.get('port'), int):
            pass
        else:
            redis_cfg['port'] = 6379
    
    # Ensemble 설정 확인
    ensemble_cfg = cfg.get('ensemble', {})
    if ensemble_cfg.get('enabled'):
        strategies = ensemble_cfg.get('strategies', [])
        logger.info(f"🎯 Ensemble 모드 활성화")
        logger.info(f"   전략 수: {len(strategies)}")
        logger.info(f"   전략 목록: {', '.join(strategies)}")
    else:
        logger.warning("⚠️ Ensemble 모드가 비활성화되어 있습니다!")
    
    # Duration 설정
    duration_hours = cfg.get('paper', {}).get('duration_hours', args.duration_hours)
    duration_mode = cfg.get('paper', {}).get('duration_mode', args.duration_mode)
    
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=duration_hours)
    
    if 'paper' not in cfg:
        cfg['paper'] = {}
    cfg['paper']['start_time'] = start_time.isoformat()
    cfg['paper']['end_time'] = end_time.isoformat()
    cfg['paper']['duration_hours'] = duration_hours
    cfg['paper']['duration_mode'] = duration_mode
    cfg['paper']['clean_start'] = True
    
    logger.info(f"⏰ 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"⏰ 종료 예정: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"⏳ 예상 실행 시간: {duration_hours * 60:.0f}분")
    
    # run_id 생성
    run_id = cfg.get('run_id') or generate_run_id()
    logger.info(f"🆔 Run ID: {run_id}")
    cfg['run_id'] = run_id
    
    # Runtime Context 생성 및 Signal Handler 등록
    runtime_ctx = RuntimeContext()
    runtime_ctx.run_id = run_id
    runtime_ctx.env = 'paper'
    cfg['runtime_context'] = runtime_ctx
    
    shutdown_requested = [False]
    
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
    
    # Output directory 생성
    output_dir = Path("scorecards") / "paper_phase22_1" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 Output 디렉토리: {output_dir}")
    
    # Effective config 저장
    snapshot_path = output_dir / "effective_config.yml"
    import yaml
    cfg_snapshot = {k: v for k, v in cfg.items() if k != 'runtime_context'}
    with open(snapshot_path, 'w', encoding='utf-8') as f:
        yaml.dump(cfg_snapshot, f, default_flow_style=False, allow_unicode=True)
    logger.info(f"💾 Effective config 저장: {snapshot_path}")
    
    # 2. 어댑터 생성
    logger.info("📊 어댑터 생성...")
    from execution.adapters import create_adapters
    
    symbol = cfg.get('symbol', 'BTCUSDT')
    
    try:
        feed, broker, clock = create_adapters(
            mode='paper',
            symbols=[symbol],
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
    
    # 3. 전략 로드
    logger.info("🎯 전략 로드...")
    from strategies import load_strategies
    
    strategies = load_strategies(config=cfg)
    logger.info(f"  ✅ 전략 로드 완료: {list(strategies.keys())}")
    
    # 4. Ensemble Module 생성 (Ensemble 모드인 경우)
    ensemble_module = None
    if ensemble_cfg.get('enabled'):
        logger.info("🎯 Ensemble Aggregator 생성...")
        try:
            from common.ensemble import EnsembleAggregator, ScoreEngine
            from common.registry.strategy_registry import StrategyRegistry
            
            # Registry와 ScoreEngine 생성
            registry = StrategyRegistry()
            score_engine = ScoreEngine()
            
            # Ensemble Aggregator 생성
            ensemble_module = EnsembleAggregator(
                registry=registry,
                score_engine=score_engine
            )
            logger.info("  ✅ Ensemble Aggregator 생성 완료")
        except Exception as e:
            logger.warning(f"⚠️ Ensemble Aggregator 생성 실패: {e}")
            logger.warning("  ℹ️  Ensemble 없이 개별 전략으로 실행합니다")
            ensemble_module = None
    
    # 5. 엔진 실행
    logger.info("=" * 80)
    logger.info("🟢 Paper Trading 시작 (REAL Engine)")
    logger.info("=" * 80)
    
    from execution import engine
    
    try:
        # Duration 제한 설정
        cfg['execution'] = cfg.get('execution', {})
        cfg['execution']['max_runtime_hours'] = duration_hours
        
        # 엔진 실행
        engine.run(
            feed=feed,
            broker=broker,
            clock=clock,
            strategies=strategies,
            ensemble_module=ensemble_module,
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
        # 리소스 정리
        logger.info("🧹 리소스 정리 시작...")
        
        if runtime_ctx and hasattr(runtime_ctx, 'monitor_registry') and runtime_ctx.monitor_registry:
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
    
    # 6. 거래 내역 조회
    logger.info("📊 거래 내역 조회...")
    
    trades = []
    if hasattr(broker, 'closed_trades'):
        trades = broker.closed_trades
        logger.info(f"  ✅ {len(trades)}개 거래 조회 완료")
    else:
        logger.warning("  ⚠️ Broker에 closed_trades 없음")
    
    # 7. Scorecard 생성
    logger.info("📈 Scorecard 생성...")
    
    period_info = {
        'start_date': start_time.strftime('%Y-%m-%d'),
        'end_date': datetime.now().strftime('%Y-%m-%d'),
        'actual_hours': (datetime.now() - start_time).total_seconds() / 3600,
        'mode': 'PHASE22-1_ENSEMBLE_V1'
    }
    
    try:
        generator = ScorecardGenerator(
            strategy_name='ensemble_v1',
            symbol=symbol,
            timeframe=cfg.get('timeframe', '5m'),
            period_info=period_info
        )
        scorecard = generator.generate(trades, output_dir)
        logger.info(f"✅ Scorecard 저장: {output_dir}")
    except Exception as e:
        logger.error(f"⚠️ Scorecard 생성 실패: {e}")
    
    # 8. 결과 요약
    logger.info("=" * 80)
    logger.info("📋 PHASE22-1 실행 완료")
    logger.info("=" * 80)
    logger.info(f"🆔 Run ID: {run_id}")
    logger.info(f"📁 Output: {output_dir}")
    logger.info(f"📊 거래 수: {len(trades)}")
    logger.info(f"⏱️  실행 시간: {(datetime.now() - start_time).total_seconds() / 60:.1f}분")
    logger.info("=" * 80)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
