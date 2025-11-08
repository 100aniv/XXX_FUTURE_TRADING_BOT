#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 트레이딩 시스템 (Unified Trading System)
==============================================
단일 진입점 - Feed/Broker 어댑터 교체 방식

설정:
- .env: TRADING_MODE, 심볼, 타임프레임
- strategy_params.yaml: 전략 파라미터

사용법:
  python main.py

"""
import os
import sys
import atexit
from dotenv import load_dotenv

load_dotenv()

from common.logger import setup_logger
from common.messaging import tg, system_shutdown_alert
from common.database import test_db_connection
from common.config_loader import load_config
from common.symbol_manager import load_symbols_from_config

logger = setup_logger(__name__, log_type="application")


def main():
    """메인 함수"""
    # 설정 로드
    CFG = load_config()
    logger.info("🚨🚨🚨 [FORCE DEBUG] main() 함수 시작됨")
    logger.info("✅ config.yml 로드 완료")
    
    # ⭐ config.yml에서 mode 읽기 (환경변수보다 우선)
    mode = CFG.get('mode', os.getenv('TRADING_MODE', 'paper')).lower()
    
    logger.info("="*80)
    logger.info(f"🚀 트레이딩 시스템 시작: 모드={mode.upper()}")
    logger.info("="*80)

    # Telegram: START + DB 상태
    try:
        tg(f"🚀 START [{mode.upper()}] Trading system", CFG)
        if test_db_connection():
            tg("✅ DB 연결 성공", CFG)
        else:
            tg("❌ DB 연결 실패 (거래/튜닝 기록 불가)", CFG)
    except Exception as e:
        logger.error(f"❌ 텔레그램 알림 오류: {e}")
    
    # Telegram: STOP on exit (PR12 #9)
    def _on_exit():
        try:
            strategy = (CFG.get('strategy', {}).get('selector') or 'ensemble')
            system_shutdown_alert(mode, strategy, CFG)
        except Exception:
            pass
    atexit.register(_on_exit)
    
    if mode not in ['backtest', 'paper', 'live']:
        logger.error(f"❌ 알 수 없는 모드: {mode}")
        sys.exit(1)
    
    # ⭐ 심볼 로드 (symbol_manager 모듈 활용)
    symbols = load_symbols_from_config(CFG)
    
    # Telegram: 심볼 로드 완료
    symbol_mode = CFG.get('symbols', {}).get('mode', 'manual')
    try:
        tg(f"✅ 심볼 로드 완료: {len(symbols)}개 ({symbol_mode} 모드)", CFG)
    except Exception:
        pass
    
    # ⭐ PR7-2: 환경변수로 앙상블 모드 오버라이드
    use_ensemble_env = os.getenv('USE_ENSEMBLE', '').lower() in ('true', '1', 'yes')
    strategy_selector_env = os.getenv('STRATEGY_SELECTOR', '').lower()
    
    # ✅ 전략 선택 및 타임프레임 동기화
    if use_ensemble_env:
        # 앙상블 모드: 환경변수 우선
        use_ensemble = True
        strategy_selector = None
        logger.info("⭐ 앙상블 모드 (환경변수 USE_ENSEMBLE=true)")
    elif strategy_selector_env and strategy_selector_env != 'null':
        # 개별 전략: 환경변수 우선
        use_ensemble = False
        strategy_selector = strategy_selector_env
        logger.info(f"⭐ 개별 전략 모드: {strategy_selector} (환경변수)")
    else:
        # config.yml 사용
        use_ensemble = CFG.get('strategy', {}).get('use_ensemble', False)
        strategy_selector = CFG.get('strategy', {}).get('selector')
        if not use_ensemble and not strategy_selector:
            logger.error("❌ config.yml에 strategy.selector 설정 또는 use_ensemble=true 필요")
            sys.exit(1)
        logger.info(f"⭐ 설정: {'앙상블' if use_ensemble else f'개별 전략 ({strategy_selector})'} (config.yml)")
    
    timeframe = CFG.get('strategies', {}).get(strategy_selector, {}).get('timeframe', CFG.get('timeframe', '5m')) if strategy_selector else CFG.get('timeframe', '5m')
    
    # ✅ config 구성: engine에서 config_merger가 처리하므로 최소한만 추가
    config = CFG  # 전체 config 직접 전달 (복사 불필요)
    config['symbols_list'] = symbols  # 심볼 리스트
    config['symbol'] = symbols[0] if symbols else 'BTCUSDT'  # 첫 심볼 (하위 호환)
    # mode는 이미 CFG에 있음
    
    # 전략 & Ensemble 로드
    from strategies import ensemble, load_strategies
    from execution.adapters import create_adapters
    
    strategies = load_strategies(config=CFG)
    
    # ⭐ Feed, Broker, Clock 생성 (adapters 모듈 활용)
    feed, broker, clock = create_adapters(mode, symbols, CFG, logger)
    
    # 추가 로깅 (paper/live 전용)
    if mode in ['paper', 'live']:
        logger.info(f"   심볼 목록: {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")
        initial_capital = config.get('capital', {}).get('initial', 10000)
        logger.info(f"   자산: {initial_capital:,.0f} USDT")
        
        # 일일 손실 한도 (설정에서 로드)
        daily_loss_pct = CFG.get('risk', {}).get('profiles', {}).get(mode, {}).get('max_daily_loss_pct')
        if daily_loss_pct is None:
            daily_loss_pct = CFG.get('risk', {}).get('max_daily_loss_pct', 2.0)
        if daily_loss_pct > 1:
            daily_loss_pct = daily_loss_pct / 100.0
        daily_loss_limit = initial_capital * daily_loss_pct
        logger.info(f"   일일 손실 한도: {daily_loss_limit:,.0f} USDT ({daily_loss_pct*100:.1f}%)")
        
        # Telegram: WebSocket 연결 완료
        try:
            base_timeframe = (CFG.get('feed', {}) or {}).get('base_timeframe', timeframe)
            tg(f"🔗 WebSocket 연결 완료\n구독: {len(symbols)}개 심볼 (base={base_timeframe}, anchor={timeframe})", CFG)
        except Exception:
            pass
    
    # ⭐ 공통 실행 (모드 무관)
    logger.info("🔍 [MAIN DEBUG] engine.run() 호출 직전")
    from execution import engine
    logger.info("🔍 [MAIN DEBUG] engine 모듈 임포트 완료")
    engine.run(feed, broker, clock, strategies, ensemble if use_ensemble else None, config)
    logger.info("🔍 [MAIN DEBUG] engine.run() 호출 완료")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("⏹️ 사용자 중단")
    except Exception as e:
        logger.error(f"❌ 치명적 에러: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
