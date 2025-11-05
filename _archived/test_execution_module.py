#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Execution Module Test
======================
execution/ 모듈 단독 테스트
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# 환경변수 설정
os.environ['STRATEGY_SELECTOR'] = 'ensemble'
os.environ['TRADING_MODE'] = 'paper'
os.environ['EQUITY_USDT'] = '10000'
os.environ['RISK_PER_TRADE'] = '0.01'

from common.logger import setup_logger
from common.database import get_db_connection, test_db_connection
from common.config import load_config, validate_config
from execution import TradingExecutor, PositionSizer, RiskManager, PositionTracker
from execution import manager

logger = setup_logger(__name__, log_type="test")

def test_execution_module():
    """execution 모듈 테스트"""
    
    logger.info("="*60)
    logger.info("execution/ 모듈 테스트 시작")
    logger.info("="*60)
    
    # 1. Config 테스트
    logger.info("\n[1/7] Config 로드 및 검증...")
    try:
        config = load_config()
        validate_config(config)
        logger.info(f"✅ Config: strategy={config['strategy_selector']}, mode={config['trading_mode']}")
    except Exception as e:
        logger.error(f"❌ Config 실패: {e}")
        return False
    
    # 2. DB 연결 테스트
    logger.info("\n[2/7] DB 연결 테스트...")
    try:
        test_db_connection()
        logger.info("✅ DB 연결 성공")
    except Exception as e:
        logger.error(f"❌ DB 연결 실패: {e}")
        return False
    
    # 3. TradingExecutor 초기화 테스트
    logger.info("\n[3/7] TradingExecutor 초기화...")
    try:
        executor = TradingExecutor(mode='paper')
        logger.info(f"✅ TradingExecutor 초기화 완료 (모드: {executor.get_mode()})")
    except Exception as e:
        logger.error(f"❌ TradingExecutor 초기화 실패: {e}")
        return False
    
    # 4. PositionSizer 테스트
    logger.info("\n[4/7] PositionSizer 테스트...")
    try:
        sizer = PositionSizer()
        test_signal = {
            'entry_price': 67000.0,
            'sl_price': 66500.0,
            'confidence': 0.8,
            'symbol': 'BTCUSDT'
        }
        qty, meta = sizer.calculate(test_signal)
        logger.info(f"✅ PositionSizer: qty={qty:.3f}, meta={meta}")
    except Exception as e:
        logger.error(f"❌ PositionSizer 실패: {e}")
        return False
    
    # 5. RiskManager 테스트
    logger.info("\n[5/7] RiskManager 테스트...")
    try:
        risk_mgr = RiskManager()
        test_signal = {
            'symbol': 'BTCUSDT',
            'entry_price': 67000.0,
            'sl_price': 66500.0
        }
        allowed, reason = risk_mgr.check_order(test_signal, 0.5)
        logger.info(f"✅ RiskManager: allowed={allowed}, reason={reason}")
    except Exception as e:
        logger.error(f"❌ RiskManager 실패: {e}")
        return False
    
    # 6. PositionTracker 테스트
    logger.info("\n[6/7] PositionTracker 테스트...")
    try:
        tracker = PositionTracker(mode='paper')
        tracker.track_new_position(
            symbol='BTCUSDT',
            side='LONG',
            entry=67000.0,
            sl=66500.0,
            tp=68000.0,
            qty=0.5,
            timestamp=1700000000000
        )
        positions = tracker.get_active_positions()
        logger.info(f"✅ PositionTracker: {len(positions)}개 포지션 추적 중")
    except Exception as e:
        logger.error(f"❌ PositionTracker 실패: {e}")
        return False
    
    # 7. manager 함수들 테스트
    logger.info("\n[7/7] execution.manager 함수들 테스트...")
    try:
        # fetch_ensemble_decisions 테스트
        decisions = manager.fetch_ensemble_decisions()
        logger.info(f"  - fetch_ensemble_decisions(): {len(decisions)}개")
        
        # fetch_strategy_signals 테스트
        signals = manager.fetch_strategy_signals('trend')
        logger.info(f"  - fetch_strategy_signals('trend'): {len(signals)}개")
        
        logger.info("✅ manager 함수들 정상 동작")
    except Exception as e:
        logger.error(f"❌ manager 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    logger.info("\n" + "="*60)
    logger.info("✅ 모든 테스트 통과!")
    logger.info("="*60)
    return True

if __name__ == "__main__":
    try:
        success = test_execution_module()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n테스트 중단")
        sys.exit(1)
    except Exception as e:
        logger.error(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
