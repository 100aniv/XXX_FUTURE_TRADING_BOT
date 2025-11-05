#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 트레이딩 시스템 (Unified Trading System)
==============================================
단일 진입점 - 모든 모드 지원

설정:
- .env 파일에서 TRADING_MODE, BACKTEST_PERIOD 등 설정
- data/backtest_config.yaml에서 기간 프리셋 관리
- strategy_params.yaml에서 전략 파라미터 관리

사용법:
  python main.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from common.logger import setup_logger
from common.config import load_config
from common.database import test_db_connection

logger = setup_logger(__name__, log_type="application")


def main():
    """메인 함수 (엔트리포인트)"""
    mode = os.getenv('TRADING_MODE', 'paper').lower()
    
    logger.info("="*80)
    logger.info(f"🚀 트레이딩 시스템 시작")
    logger.info(f"   모드: {mode.upper()}")
    logger.info("="*80)
    
    if mode not in ['backtest', 'paper', 'live']:
        logger.error(f"❌ 알 수 없는 모드: {mode}")
        logger.error("   지원 모드: backtest, paper, live")
        sys.exit(1)
    
    from execution.engine import TradingEngine
    
    # 모드별 실행 (로직은 engine에 있음)
    if mode == 'backtest':
        TradingEngine.run_all_backtests()
    
    elif mode in ['paper', 'live']:
        # 실시간 트레이딩 모드 (페이퍼/라이브) → 로직은 engine에
        TradingEngine.run_realtime_mode(mode)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⏹️  사용자 중단")
    except Exception as e:
        logger.error(f"❌ 치명적 에러: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
