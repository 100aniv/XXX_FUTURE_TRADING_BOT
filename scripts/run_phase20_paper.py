#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE20-1: Ensemble ON Paper Smoke Test Runner
=================================================
Ensemble 모드로 Paper 테스트 실행

Usage:
    python scripts/run_phase20_paper.py [--config CONFIG_FILE]
    python scripts/run_phase20_paper.py --config configs/paper/ensemble_paper_5min.yml
"""
import sys
import signal
import time
import argparse
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.config_loader import load_config_with_mode
from common.logger import setup_logger
from common.runtime_context import RuntimeContext
from analytics.scorecard import ScorecardGenerator

logger = setup_logger(__name__, log_type="application")


def parse_args():
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(description='PHASE20-1: Ensemble Paper Test')
    parser.add_argument(
        '--config',
        type=str,
        default='configs/paper/ensemble_paper_smoke.yml',
        help='Config 파일 경로 (기본: ensemble_paper_smoke.yml)'
    )
    return parser.parse_args()


def main():
    """메인 함수"""
    args = parse_args()
    
    logger.info("=" * 80)
    logger.info("🚀 PHASE20-1: Ensemble ON Paper Test")
    logger.info("=" * 80)
    
    # 1. Config 로딩
    logger.info("⚙️  Config 로딩...")
    config_path = project_root / args.config
    
    if not config_path.exists():
        logger.error(f"❌ Config 파일 없음: {config_path}")
        sys.exit(1)
    
    cfg = load_config_with_mode(base_path=str(config_path))
    
    # mode 확인
    if cfg.get('mode') != 'paper':
        logger.warning(f"⚠️  mode를 'paper'로 강제 설정 (현재: {cfg.get('mode')})")
        cfg['mode'] = 'paper'
    
    # ensemble.enabled 확인
    if not cfg.get('ensemble', {}).get('enabled', False):
        logger.error("❌ ensemble.enabled가 false입니다. Config를 확인하세요.")
        sys.exit(1)
    
    logger.info(f"✅ Ensemble 모드: {cfg.get('ensemble', {}).get('enabled')}")
    logger.info(f"✅ Ensemble 전략: {cfg.get('ensemble', {}).get('strategies', [])}")
    logger.info(f"✅ Symbol: {cfg.get('symbol')}")
    logger.info(f"✅ Timeframe: {cfg.get('timeframe')}")
    logger.info(f"✅ Duration: {cfg.get('paper', {}).get('duration_hours')} hours")
    logger.info("=" * 80)
    
    # 2. RuntimeContext 설정
    ctx = RuntimeContext()
    ctx.run_id = cfg.get('run_id', f"phase20_paper_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    ctx.env = 'paper'
    
    # Config에 ctx 주입
    cfg['runtime_context'] = ctx
    
    # Graceful Shutdown 핸들러 등록
    def signal_handler(signum, frame):
        logger.warning(f"⚠️  Signal {signum} 수신, Graceful Shutdown 시작...")
        ctx.request_shutdown()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 3. 어댑터 생성 (Feed, Broker, Clock)
    logger.info("📊 어댑터 생성...")
    from execution.adapters import create_adapters
    
    try:
        feed, broker, clock = create_adapters(
            mode='paper',
            symbols=[cfg.get('symbol', 'BTCUSDT')],
            config=cfg,
            logger=logger
        )
        logger.info(f"  ✅ Feed: {type(feed).__name__}")
        logger.info(f"  ✅ Broker: {type(broker).__name__}")
        logger.info(f"  ✅ Clock: {type(clock).__name__}")
    except Exception as e:
        logger.error(f"❌ 어댑터 생성 실패: {e}", exc_info=True)
        sys.exit(1)
    
    # 4. 전략 로드 (Ensemble 모드에서는 엔진 내부에서 처리)
    logger.info("🎯 전략 준비...")
    from strategies import load_strategies
    
    strategies = load_strategies(config=cfg)
    logger.info(f"  ✅ 전략 로드 완료: {list(strategies.keys())}")
    
    # 5. 엔진 실행
    logger.info("=" * 80)
    logger.info("🟢 Ensemble Paper Trading 시작")
    logger.info("=" * 80)
    start_time = time.time()
    
    try:
        from execution import engine
        
        # 엔진 실행 (Ensemble 모드)
        engine.run(
            feed=feed,
            broker=broker,
            clock=clock,
            strategies=strategies,
            ensemble_module=None,  # 엔진 내부에서 Ensemble 초기화
            config=cfg
        )
        
        logger.info("✅ 엔진 실행 완료")
        
    except KeyboardInterrupt:
        logger.warning("⚠️  사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"❌ 엔진 실행 실패: {e}", exc_info=True)
        sys.exit(1)
    
    # 4. 실행 시간 요약
    elapsed = time.time() - start_time
    logger.info("=" * 80)
    logger.info(f"⏱️  총 실행 시간: {elapsed/60:.2f}분")
    logger.info("=" * 80)
    
    # 5. Scorecard 생성 (선택)
    try:
        logger.info("📊 Scorecard 생성 중...")
        scorecard_gen = ScorecardGenerator(cfg)
        scorecard_dir = scorecard_gen.generate()
        logger.info(f"✅ Scorecard 저장: {scorecard_dir}")
    except Exception as e:
        logger.warning(f"⚠️  Scorecard 생성 실패: {e}")
    
    logger.info("=" * 80)
    logger.info("✅ PHASE20-1 Paper Smoke Test 완료!")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
