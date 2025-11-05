#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trading Execution Script
=========================
매매 실행 스크립트 (리팩토링 완료)

새로운 구조:
- execution 모듈 사용
- TradingExecutor + manager.process_trades()
- while 루프는 여기서 관리

참고: docs/implementation/EXECUTION_MODULE_REFACTORING.md
"""
import os
import time
import sys
import signal
from dotenv import load_dotenv

load_dotenv()

# ============================================
# 환경변수 설정 (선택적 - .env 파일 우선)
# ============================================
# os.environ['DATABASE_URL'] = 'postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db'
# os.environ['STRATEGY_SELECTOR'] = 'ensemble'  # ensemble | trend | reversion | breakout | scalping | daytrade | swing
# os.environ['TRADING_MODE'] = 'paper'  # backtest | paper | live
# os.environ['EQUITY_USDT'] = '10000'
# os.environ['RISK_PER_TRADE'] = '0.01'

# ============================================
# Execution 모듈 import
# ============================================
from execution import TradingExecutor
from execution import manager
from common.logger import setup_logger
from common.database import test_db_connection

logger = setup_logger(__name__, log_type="trading")

# ============================================
# 전역 변수
# ============================================
RUNNING = True


def signal_handler(sig, frame):
    """Ctrl+C 종료 처리"""
    global RUNNING
    logger.info("\n⏹️  종료 신호 수신...")
    RUNNING = False


def main():
    """
    매매 실행 메인 함수
    """
    global RUNNING
    
    # 설정
    strategy = os.getenv('STRATEGY_SELECTOR', 'ensemble')
    mode = os.getenv('TRADING_MODE', 'paper')
    api_key = os.getenv('BINANCE_API_KEY')
    secret = os.getenv('BINANCE_SECRET')
    poll_interval = int(os.getenv('POLL_INTERVAL_SEC', '5'))
    
    logger.info("="*60)
    logger.info("🚀 Trading Execution System 시작")
    logger.info(f"   전략: {strategy}")
    logger.info(f"   모드: {mode}")
    logger.info(f"   폴링 간격: {poll_interval}초")
    logger.info("="*60)
    
    # DB 연결 테스트
    test_db_connection()
    
    # TradingExecutor 초기화
    try:
        executor = TradingExecutor(
            mode=mode,
            binance_api_key=api_key,
            binance_secret=secret
        )
        logger.info("✅ TradingExecutor 초기화 완료\n")
    except Exception as e:
        logger.error(f"❌ TradingExecutor 초기화 실패: {e}")
        sys.exit(1)
    
    # Signal handler 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 메인 루프
    logger.info("🔄 매매 루프 시작...\n")
    
    while RUNNING:
        try:
            # 신호 처리 및 주문 실행 (1 사이클)
            manager.process_trades(executor, strategy)
            
            # 대기
            time.sleep(poll_interval)
            
        except KeyboardInterrupt:
            logger.info("\n⏹️  사용자 중단")
            break
        except Exception as e:
            logger.error(f"❌ 메인 루프 에러: {e}")
            time.sleep(poll_interval)
    
    # 종료
    logger.info("\n" + "="*60)
    logger.info("🛑 Trading Execution System 종료")
    logger.info("="*60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"❌ 치명적 에러: {e}")
        sys.exit(1)
