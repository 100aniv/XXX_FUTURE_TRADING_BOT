#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trading System Main
===================
통합 트레이딩 시스템

플로우:
1. WebSocket → 실시간 캔들 수신
2. 6개 전략 신호 생성 → monitoring.signals
3. Ensemble 통합 → trading.decisions
4. Execution 실행 → trading.trades

모드:
- backtest: 통합 엔진 사용 (execution.engine.TradingEngine)
- paper/live: 실시간 트레이딩
"""
import os
import time
import threading
import signal as sig
import sys
from typing import Dict, Any
from collections import deque

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ============================================
# IMPORTS
# ============================================
from common.logger import setup_logger
from common.database import test_db_connection, save_signal_to_db, get_db_connection
from common.config import load_config, validate_config
from common.messaging import tg as _tg
from common.utils import buffer_to_df
from collector import WebSocketCollector, bootstrap_history
from indicators import add_indicators
from strategies import trend, reversion, breakout, scalping, daytrade, swing, ensemble

logger = setup_logger(__name__, log_type="application")

# 전역 상태
RUNNING = True
PAUSED = False

# ============================================
# BACKTEST MODE
# ============================================
def run_backtest_mode(CFG: Dict[str, Any]):
    """백테스트 모드 실행 - 통합 엔진 사용"""
    from execution.engine import TradingEngine
    from pathlib import Path
    from datetime import datetime
    
    logger.info("="*80)
    logger.info("📊 백테스트 모드: 통합 엔진 사용")
    logger.info("="*80)
    
    # 기본 설정
    symbols = CFG.get('symbols', ['BTCUSDT'])
    symbol = symbols[0] if symbols else 'BTCUSDT'
    
    # ⭐ 7개 전략 리스트 (앙상블 포함!)
    strategies_list = ['scalping', 'daytrade', 'swing', 'trend', 'reversion', 'breakout', 'ensemble']
    
    # ⭐ 전략 설정 파일에서 로드 (모든 모드 공통!)
    from common.strategy_config import load_strategy_params
    strategy_params = load_strategy_params()
    
    logger.info("✅ 전략 설정 로드: strategy_params.yaml")
    
    results = {}
    
    logger.info(f"📊 심볼: {symbol}")
    logger.info(f"📅 기간: {CFG.get('backtest_start_date')} ~ {CFG.get('backtest_end_date')}")
    logger.info(f"💰 초기 자본: {CFG.get('equity_usdt', 10000):,.0f} USDT")
    logger.info("="*80)
    
    # 전략 모듈 로드
    from strategies import scalping, daytrade, swing, trend, reversion, breakout, ensemble as ensemble_strategy
    strategy_modules = {
        'scalping': scalping,
        'daytrade': daytrade,
        'swing': swing,
        'trend': trend,
        'reversion': reversion,
        'breakout': breakout,
        'ensemble': ensemble_strategy,  # ⭐ 앙상블 추가
    }
    
    # 각 전략 실행
    for i, strategy_name in enumerate(strategies_list, 1):
        # ⭐ 앙상블은 간단한 평균 전략으로 대체 (백테스트용)
        if strategy_name == 'ensemble':
            logger.info(f"\n[{i}/7] ENSEMBLE - 6개 전략 평균 사용")
            # 거래가 있는 전략만 포함
            valid_strategies = [
                s for s in strategies_list[:-1] 
                if 'error' not in results[s] and results[s]['metrics'].get('total_trades', 0) > 0
            ]
            
            if valid_strategies:
                count = len(valid_strategies)
                ensemble_metrics = {
                    'total_trades': sum(results[s]['metrics'].get('total_trades', 0) for s in valid_strategies) // count,
                    'win_rate': sum(results[s]['metrics'].get('win_rate', 0) for s in valid_strategies) / count,
                    'total_return_pct': sum(results[s]['metrics'].get('total_return_pct', 0) for s in valid_strategies) / count,
                    'sharpe_ratio': sum(results[s]['metrics'].get('sharpe_ratio', 0) for s in valid_strategies) / count,
                    'max_drawdown_pct': sum(results[s]['metrics'].get('max_drawdown_pct', 0) for s in valid_strategies) / count,
                    'profit_factor': sum(results[s]['metrics'].get('profit_factor', 0) for s in valid_strategies) / count,
                }
            else:
                ensemble_metrics = {
                    'total_trades': 0,
                    'win_rate': 0,
                    'total_return_pct': 0,
                    'sharpe_ratio': 0,
                    'max_drawdown_pct': 0,
                    'profit_factor': 0,
                }
            
            results['ensemble'] = {
                'metrics': ensemble_metrics,
                'params': strategy_params['ensemble'],
                'trades': []  # 실제 거래 없음 (평균치)
            }
            logger.info(f"✅ ENSEMBLE 완료: 평균 {ensemble_metrics['total_trades']:.0f}건")
            continue
        
        strategy_config = strategy_params[strategy_name]  # ⭐ 설정 파일에서 직접 사용
        
        logger.info(f"\n[{i}/7] {strategy_name.upper()} 백테스트 시작...")
        logger.info(f"   RR: {strategy_config['rr']}, Risk: {strategy_config['risk_per_trade']*100}%")
        
        try:
            # 데이터 경로
            data_path = Path("data") / f"{symbol}_5m_{CFG.get('backtest_start_date')}_{CFG.get('backtest_end_date')}.csv"
            
            # 통합 엔진 생성
            engine = TradingEngine(
                mode='backtest',
                data_path=str(data_path),
                initial_capital=CFG.get('equity_usdt', 10000),
                fee_rate=0.0004,
                slippage_pct=0.0005,
            )
            
            # 백테스트 실행
            strategy_module = strategy_modules[strategy_name]
            trades, metrics_dict = engine.run_backtest(strategy_module, strategy_config)
            
            # 결과 저장
            results[strategy_name] = {
                'metrics': metrics_dict,
                'params': {
                    'rr': strategy_config['rr'],
                    'atr_mult_sl': strategy_config['atr_mult_sl'],
                    'risk': strategy_config['risk_per_trade'],
                },
                'trades': trades
            }
            
            logger.info(f"✅ {strategy_name.upper()} 완료: {metrics_dict['total_trades']}건 거래")
            
        except Exception as e:
            logger.error(f"❌ {strategy_name.upper()} 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            results[strategy_name] = {'error': str(e)}
    
    # 비교 리포트 생성
    logger.info("\n" + "="*80)
    logger.info("📊 전략 비교 결과")
    logger.info("="*80)
    
    # 테이블 헤더
    print(f"\n{'전략':<12} {'거래수':>8} {'승률':>8} {'평균승':>10} {'평균손':>10} {'수익률':>10} {'PF':>8}")
    print("-" * 100)
    
    best_strategy = None
    best_score = -999
    
    # 각 전략 출력
    for strategy_name in strategies_list:
        if 'error' in results[strategy_name]:
            print(f"{strategy_name.upper():<12} {'ERROR':>8}")
            continue
        
        m = results[strategy_name]['metrics']
        
        # 점수 계산 (최고 전략 선정용)
        score = (m.get('win_rate', 0) * 50) + (m.get('sharpe_ratio', 0) * 20) + (m.get('total_return_pct', 0) / 10)
        
        if score > best_score:
            best_score = score
            best_strategy = strategy_name
        
        print(f"{strategy_name.upper():<12} "
              f"{m.get('total_trades', 0):>8} "
              f"{m.get('win_rate', 0)*100:>7.1f}% "
              f"${m.get('avg_win', 0):>9.2f} "
              f"${m.get('avg_loss', 0):>9.2f} "
              f"{m.get('total_return_pct', 0):>9.2f}% "
              f"{m.get('profit_factor', 0):>8.2f}")
    
    print("-" * 80)
    
    # 최적 전략 추천
    if best_strategy:
        logger.info(f"\n🏆 최고 성과 전략: {best_strategy.upper()}")
        m = results[best_strategy]['metrics']
        logger.info(f"   승률: {m.get('win_rate', 0):.2%}")
        logger.info(f"   수익률: {m.get('total_return_pct', 0):.2f}%")
        logger.info(f"   샤프 비율: {m.get('sharpe_ratio', 0):.2f}")
        logger.info(f"   Profit Factor: {m.get('profit_factor', 0):.2f}")
    
    # 결과 저장
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    comparison_file = results_dir / f"strategy_comparison_{timestamp}.json"
    
    import json
    
    # JSON 직렬화
    json_results = {}
    for strategy_name, data in results.items():
        if 'error' in data:
            json_results[strategy_name] = data
        else:
            json_results[strategy_name] = {
                'params': data['params'],
                'metrics': data['metrics']
            }
    
    with open(comparison_file, 'w', encoding='utf-8') as f:
        json.dump(json_results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n💾 비교 결과 저장: {comparison_file}")
    
    # HTML 리포트 생성
    try:
        from reports import generate_trading_report
        html_file = generate_trading_report(str(comparison_file), mode='backtest')
        logger.info(f"📊 HTML 리포트 생성: {html_file}")
    except Exception as e:
        logger.warning(f"⚠️  리포트 생성 실패: {e}")
    
    logger.info("="*80)
    logger.info("✅ 전체 백테스트 완료!")
    logger.info("="*80)


# ============================================
# REAL-TIME TRADING MODE (PAPER/LIVE)
# ============================================
def run_realtime_mode(CFG: Dict[str, Any]):
    """실시간 트레이딩 모드 (paper/live)"""
    global PAUSED, RUNNING
    
    trading_mode = CFG.get('trading_mode', 'paper')
    
    logger.info("="*80)
    logger.info(f"🚀 실시간 트레이딩 모드: {trading_mode.upper()}")
    logger.info("="*80)
    
    # DB 연결 테스트
    test_db_connection()
    
    # 텔레그램 래퍼
    def tg(text: str):
        if CFG.get("enable_telegram"):
            return _tg(text, CFG)
        return False
    
    # 전략 리스트 (6개)
    STRATEGIES = {
        "trend": trend,
        "reversion": reversion,
        "breakout": breakout,
        "scalping": scalping,
        "daytrade": daytrade,
        "swing": swing,
    }
    
    # 심볼별 캔들 버퍼
    buffers: Dict[str, deque] = {
        symbol: deque(maxlen=CFG["lookback"]) 
        for symbol in CFG["symbols"]
    }
    
    # ⭐ 전략 설정 로드 (백테스트와 동일하게)
    from common.strategy_config import load_strategy_params
    strategy_params = load_strategy_params()
    
    # ⭐ TradingEngine 초기화 (실시간용)
    from execution.engine import TradingEngine
    
    # 엔진 저장용 딕셔너리 (전략별)
    engines = {}
    for strategy_name in STRATEGIES.keys():
        engines[strategy_name] = TradingEngine(
            mode=trading_mode,  # paper or live
            symbols=CFG['symbols'],
            timeframe=CFG['timeframe'],
            initial_capital=CFG.get('equity_usdt', 10000),
            fee_rate=0.0004,
            api_key=CFG.get('binance_api_key'),
            api_secret=CFG.get('binance_secret')
        )
    
    # ============================================
    # 캔들 처리 콜백 (⭐ signals 모듈 활용)
    # ============================================
    def on_candle_closed(symbol, candle, is_closed, timeframe):
        """캔들 닫힐 때 호출 (⭐ 백테스트와 동일한 로직)"""
        if PAUSED or not is_closed:
            return
        
        # 1m 캔들은 flash-guard와 포지션 추적용 (신호 생성 제외)
        if timeframe == "1m":
            return
        
        try:
            # 1️⃣ 버퍼에 캔들 추가
            buffers[symbol].append(candle)
            
            # 2️⃣ DataFrame 생성
            df = buffer_to_df(symbol, buffers)
            if len(df) < 50:  # 최소 데이터 필요
                return
            
            # 3️⃣ 지표 계산 (⭐ indicators 모듈)
            df = add_indicators(df)
            
            # 4️⃣ 6개 전략 모두 실행 (⭐ strategies 모듈)
            for strategy_id, strategy_module in STRATEGIES.items():
                try:
                    # 전략 설정 가져오기
                    config = strategy_params[strategy_id]
                    
                    # 신호 생성 (⭐ strategies 모듈)
                    signal = strategy_module.signal_logic(df, config)
                    
                    if not signal or not signal.get("side"):
                        continue
                    
                    # ⭐ signals 모듈 사용 (DB 저장)
                    from datetime import datetime
                    from uuid import uuid4
                    
                    save_signal_to_db(
                        signal_id=str(uuid4()),
                        strategy_id=strategy_id,
                        symbol=symbol,
                        timeframe=timeframe,
                        candle_closed_at=datetime.fromtimestamp(candle.get("time", int(time.time() * 1000)) / 1000),
                        direction=signal["side"],
                        confidence=signal.get("confidence", 0.75),
                        entry_price=signal.get("entry"),
                        sl_price=signal.get("sl"),
                        tp_price=signal.get("tp"),
                        atr=signal.get("atr"),
                        leverage=signal.get("lev"),
                        features={
                            "rsi": signal.get("rsi"),
                            "macd": signal.get("macd"),
                            "regime": signal.get("regime"),
                            "reason": " / ".join(signal.get("reason", []))
                        }
                    )
                    
                    logger.info(f"✅ {strategy_id.upper()}: {symbol} {signal['side']} @ {signal.get('entry')}")
                    
                    # ⭐ 실시간 거래 실행 (백테스트와 동일한 엔진 사용)
                    # TODO: 여기서 엔진의 포지션 관리 로직 호출
                    
                except Exception as e:
                    logger.error(f"❌ {strategy_id} 전략 실패: {e}")
            
        except Exception as e:
            logger.error(f"⚠️ 캔들 처리 오류: {e}")
            import traceback
            traceback.print_exc()
    
    # ============================================
    # Ensemble & Execution 주기적 실행
    # ============================================
    def periodic_processor():
        """주기적으로 ensemble + execution 실행"""
        global RUNNING
        
        while RUNNING:
            try:
                if not PAUSED:
                    # 1. Ensemble 통합 (신호 → 결정)
                    try:
                        with get_db_connection() as conn:
                            ensemble.process_pending_signals(conn, logger)
                    except Exception as e:
                        logger.error(f"❌ Ensemble 실패: {e}")
                    
                    # 2. Execution 실행 (결정 → 거래)
                    # TODO: TradingEngine으로 통합 예정
                    # 현재는 기존 execution 모듈 사용
                    try:
                        from execution import manager as execution_manager
                        from execution import TradingExecutor
                        
                        # executor 초기화 (한 번만)
                        if not hasattr(periodic_processor, 'executor'):
                            periodic_processor.executor = TradingExecutor(
                                mode=CFG.get("trading_mode", "paper"),
                                binance_api_key=CFG.get("binance_api_key"),
                                binance_secret=CFG.get("binance_secret")
                            )
                        
                        execution_manager.process_trades(
                            periodic_processor.executor,
                            strategy=CFG.get("strategy_selector", "ensemble")
                        )
                    except Exception as e:
                        logger.error(f"❌ Execution 실패: {e}")
                
                # 폴링 간격
                time.sleep(CFG.get("poll_interval_sec", 5))
                
            except Exception as e:
                logger.error(f"❌ Periodic processor 오류: {e}")
                time.sleep(5)
    
    # ============================================
    # 시작
    # ============================================
    logger.info("="*60)
    logger.info("🚀 통합 트레이딩 시스템 시작")
    logger.info(f"   전략: {CFG.get('strategy_selector', 'ensemble')}")
    logger.info(f"   모드: {CFG.get('trading_mode', 'paper')}")
    logger.info(f"   심볼: {', '.join(CFG['symbols'])}")
    logger.info(f"   타임프레임: {CFG['timeframe']}")
    logger.info("="*60)
    
    tg(f"🚀 *트레이딩 시스템 시작*\n"
       f"━━━━━━━━━━━━━━━━━━━━━\n"
       f"전략: {CFG.get('strategy_selector', 'ensemble').upper()}\n"
       f"모드: {CFG.get('trading_mode', 'paper').upper()}\n"
       f"심볼: {', '.join(CFG['symbols'])}\n"
       f"━━━━━━━━━━━━━━━━━━━━━")
    
    # 초기 히스토리 로드
    logger.info("초기 히스토리 로딩...")
    for symbol in CFG["symbols"]:
        try:
            bootstrap_history(symbol, CFG["timeframe"], CFG["lookback"], buffers)
            logger.info(f"  ✅ {symbol}: {len(buffers[symbol])}개 캔들")
        except Exception as e:
            logger.error(f"  ❌ {symbol} 로드 실패: {e}")
    
    # Periodic processor 스레드 시작
    processor_thread = threading.Thread(
        target=periodic_processor,
        daemon=True,
        name="PeriodicProcessor"
    )
    processor_thread.start()
    logger.info("✅ Periodic processor 시작됨")
    
    # WebSocket Collector 시작
    logger.info("WebSocket 연결 중...")
    collector = WebSocketCollector(CFG["symbols"], CFG["timeframe"])
    collector.on_candle(on_candle_closed)
    collector.on_connect(lambda: tg("🔗 WebSocket 연결 성공"))
    collector.on_error(lambda e: logger.error(f"💥 WebSocket 오류: {e}"))
    collector.on_close_reconnect(lambda: logger.warning("🔌 재연결 중..."))
    
    collector.start()


# ============================================
# MAIN
# ============================================
def main():
    """통합 트레이딩 시스템 메인 함수"""
    global PAUSED
    
    # Config 로드
    CFG = load_config()
    validate_config(CFG)
    
    # TRADING_MODE 확인
    trading_mode = CFG.get('trading_mode', 'paper')
    
    logger.info("="*60)
    logger.info(f"🚀 트레이딩 시스템 시작")
    logger.info(f"   모드: {trading_mode.upper()}")
    logger.info(f"   전략: {CFG.get('strategy_selector', 'ensemble')}")
    logger.info("="*60)
    
    # 모드별 분기
    if trading_mode == 'backtest':
        # 백테스트 모드
        logger.info("📊 백테스트 모드로 실행합니다...")
        run_backtest_mode(CFG)
        return
    
    # 실시간 트레이딩 모드 (paper/live)
    logger.info("📡 실시간 트레이딩 모드로 실행합니다...")
    run_realtime_mode(CFG)


if __name__ == "__main__":
    def cleanup():
        global RUNNING
        RUNNING = False
        logger.info("시스템 종료 중...")
    
    def signal_handler(signum, frame):
        global RUNNING
        RUNNING = False
        logger.info("종료 신호 수신")
        sys.exit(0)
    
    sig.signal(sig.SIGINT, signal_handler)
    sig.signal(sig.SIGTERM, signal_handler)
    
    try:
        main()
    except KeyboardInterrupt:
        logger.info("수동 종료")
    except Exception as e:
        logger.error(f"치명적 오류: {e}")
        raise
    finally:
        cleanup()
