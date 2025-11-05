#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 트레이딩 시스템 (Unified Trading System)
==============================================
단일 진입점 - 모든 모드 지원

모드:
- TRADING_MODE=backtest → 백테스트
- TRADING_MODE=paper    → 페이퍼 트레이딩
- TRADING_MODE=live     → 라이브 트레이딩
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from common.logger import setup_logger
from common.config import load_config

logger = setup_logger(__name__, log_type="application")


def main():
    """메인 함수"""
    mode = os.getenv('TRADING_MODE', 'paper').lower()
    
    logger.info(f"🎯 모드: {mode.upper()}")
    
    if mode not in ['backtest', 'paper', 'live']:
        logger.error(f"❌ 알 수 없는 모드: {mode}")
        logger.error("   지원 모드: backtest, paper, live")
        sys.exit(1)
    
    # TradingEngine 초기화
    from execution.engine import TradingEngine
    
    if mode == 'backtest':
        # 백테스트 설정
        CFG = load_config()
        from pathlib import Path
        
        symbol = CFG.get('symbols', ['BTCUSDT'])[0]
        start_date = CFG.get('backtest_start_date', '2024-07-01')
        end_date = CFG.get('backtest_end_date', '2024-10-17')
        data_path = Path("data") / f"{symbol}_5m_{start_date}_{end_date}.csv"
        
        if not data_path.exists():
            logger.error(f"❌ 데이터 파일 없음: {data_path}")
            sys.exit(1)
        
        engine = TradingEngine(
            mode='backtest',
            data_path=str(data_path),
            initial_capital=CFG.get('equity_usdt', 10000),
            fee_rate=0.0004,
            slippage_pct=0.0005,
        )
        
        # 백테스트 실행
        from strategies import scalping, daytrade, swing, trend, reversion, breakout
        from common.strategy_config import load_strategy_params
        
        strategy_modules = {
            'scalping': scalping,
            'daytrade': daytrade,
            'swing': swing,
            'trend': trend,
            'reversion': reversion,
            'breakout': breakout,
        }
        
        strategy_params = load_strategy_params()
        
        selected_strategy = os.getenv('STRATEGY_SELECTOR', 'all')
        strategies_to_run = [selected_strategy] if selected_strategy != 'all' else list(strategy_modules.keys())
        
        for strategy_name in strategies_to_run:
            logger.info(f"\n{'='*80}")
            logger.info(f"📊 {strategy_name.upper()} 백테스트")
            logger.info(f"{'='*80}")
            
            strategy_module = strategy_modules[strategy_name]
            strategy_config = strategy_params[strategy_name]
            
            trades, metrics = engine.run_backtest(strategy_module, strategy_config)
            
            logger.info(f"✅ {strategy_name.upper()}: {metrics['total_trades']}건, 승률 {metrics['win_rate']:.2%}")
    
    elif mode == 'paper':
        # 페이퍼 트레이딩 설정
        engine = TradingEngine(
            mode='paper',
            exchange='binance',
            api_key=os.getenv('BINANCE_API_KEY'),
            api_secret=os.getenv('BINANCE_SECRET'),
            fee_rate=0.0004,
        )
        
        # 페이퍼 트레이딩 실행
        engine.run_paper()
    
    elif mode == 'live':
        # 라이브 트레이딩 설정
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_SECRET')
        
        if not api_key or not api_secret:
            logger.error("❌ BINANCE_API_KEY, BINANCE_SECRET 환경변수 필요")
            sys.exit(1)
        
        engine = TradingEngine(
            mode='live',
            exchange='binance',
            api_key=api_key,
            api_secret=api_secret,
            fee_rate=0.0004,
        )
        
        # 라이브 트레이딩 실행
        engine.run_live()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"❌ 치명적 에러: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
