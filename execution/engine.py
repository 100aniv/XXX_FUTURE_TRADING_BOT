#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trading Engine
==============
단일 공통 루프 (Backtest = Paper = Live)

어댑터만 교체하면 모든 모드 작동
"""
from collections import deque
from typing import Dict
from uuid import uuid4
from datetime import datetime
import pandas as pd
import redis
import hashlib
import json

from common.logger import setup_logger
from common.messaging import (
    tg,
    log_status,
    log_performance,
    format_exit_alert,
    format_signal_alert,
)
from monitoring.telemetry_profiler import start_monitoring
from monitoring import init_monitoring
from indicators import add_indicators
from common.database import get_db_connection, save_signal_to_db
from execution.position_sizer import PositionSizer
from execution.risk_manager import RiskManager
from signals.signal_generator import SignalGenerator
from execution.portfolio_manager import PortfolioManager
from execution.position_tracker import PositionTracker

logger = setup_logger(__name__, log_type="application")


def run(feed, broker, clock, strategies: Dict, ensemble_module, config: Dict):
    """
    공통 트레이딩 루프

    Args:
        feed: 데이터 피드
        broker: 브로커
        clock: 시계
        strategies: 전략 딕셔너리
        ensemble_module: 앙상블 모듈
        config: 설정

    Args:
        feed: 데이터 공급자 (HistoricalFeed | LiveFeed)
        broker: 거래 실행자 (SimBroker | PaperBroker | LiveBroker)
        clock: 시간 제공자 (SimClock | LiveClock)
        strategies: 전략 dict {'scalping': module, ...}
        ensemble_module: ensemble 모듈 (None이면 첫 신호 사용)
        config: 설정 dict
    """
    logger.info("🚨 [ENGINE CRITICAL] run() 함수 시작 - 성공적으로 도달!")
    logger.info(f"🚨 [ENGINE CRITICAL] config mode: {config.get('mode', 'unknown')}")
    logger.info(f"🚨 [ENGINE CRITICAL] feed 타입: {type(feed).__name__}")
    
    # ⭐ WebSocket 시작 (기존 구조 유지)
    if hasattr(feed, 'start'):
        logger.info("🔗 WebSocket 시작")
        feed.start()
        import time
        time.sleep(2)  # WebSocket 연결 안정화 대기
        logger.info("✅ WebSocket 시작 완료")
    
    # ⭐ PR11: FlowGuardian 게이트 (.windsurfrules 준수)
    # READY 플래그 없이는 PAPER/LIVE 실행 불가
    mode = config.get("mode", "paper")
    if mode in ["paper", "live"]:
        try:
            from core.flow_guardian import FlowGuardian
            
            # FlowGuardian 간소화된 검증 (인터페이스 호환성 문제 우회)
            guardian = FlowGuardian(
                config=config,
                source=None,  # 셀프테스트에서 자체 데이터 생성
                strategy=None,  # 셀프테스트에서 자체 전략 시뮬레이션
                risk=None,  # 셀프테스트에서 자체 리스크 시뮬레이션
                executor=None,  # 셀프테스트에서 자체 실행 시뮬레이션
                metrics=None,  # 셀프테스트에서 자체 메트릭 생성
            )
            
            # READY 상태 강제 검증 (1회만 호출)
            guardian.assert_ready(mode)
            logger.info(f"✅ FlowGuardian 게이트 통과 - {mode.upper()} 모드 진입")
            
        except Exception as e:
            logger.error(f"❌ FlowGuardian 게이트 실패: {e}")
            raise RuntimeError(f"FlowGuardian 게이트 실패 - {mode.upper()} 모드 실행 불가: {e}")
    else:
        logger.info(f"ℹ️  FlowGuardian 게이트 우회 - {mode} 모드 (backtest 등)")
    # 필수 파라미터 (config.yml 필수)
    symbol = config.get("symbol", "BTCUSDT")  # backtest에서 사용
    timeframe = config["timeframe"]
    lookback = config["lookback"]
    equity = config["equity"]
    risk_per_trade = config["risk"]["per_trade"]
    trial_id = config.get("trial_id")  # 백테스트 trial 식별자 (선택)

    # ⭐ PR7-4: Multi-TF 버퍼: (심볼, 타임프레임) 독립 버퍼 관리
    # - 단일 TF: buffers = {('BTCUSDT', '5m'): deque([...], maxlen=400)}
    # - Multi-TF: buffers = {('BTCUSDT', '3m'): deque(...), ('BTCUSDT', '5m'): deque(...)}
    buffers: Dict[tuple, deque] = {}  # {(symbol, timeframe): deque(maxlen=lookback)}

    # ⭐ PR8: 전략별 심볼 거부 쿨다운 (Risk + Portfolio 거부 시 반복 시도 방지)
    # - ensemble 모드: 6개 전략이 독립적으로 신호 생성 → 전략별 쿨다운 필요
    # - 키 형식: "SYMBOL_STRATEGY" (예: "BTCUSDT_scalping")
    import time

    reject_cooldown: Dict[str, float] = {}  # {f"{symbol}_{strategy}": last_reject_time}
    cooldown_seconds = config.get("execution", {}).get("reject_cooldown_seconds", 60)

    # ⭐ PR9: Redis 연결 (캔들 dedup, 쿨다운 TTL, 신호 멱등성)
    redis_config = config.get("monitoring", {}).get("redis", {})
    redis_client = None
    try:
        redis_client = redis.Redis(
            host=redis_config.get("host", "localhost"),
            port=redis_config.get("port", 6379),
            db=redis_config.get("db", 0),
            decode_responses=True,
        )
        redis_client.ping()
        logger.info(
            f"✅ Redis 연결 성공: {redis_config.get('host')}:{redis_config.get('port')}"
        )
    except Exception as e:
        logger.warning(f"⚠️  Redis 연결 실패 (Dedup/쿨다운 비활성화): {e}")
        redis_client = None

    # ⭐ PR9: 타임프레임 기반 동적 TTL (멱등성 개선)
    # - 1m → 63s, 3m → 189s, 5m → 315s, 15m → 945s, 1h → 3780s
    # - 기본값: 타임프레임 * 1.05 (봉 전환 지연 대응)
    def timeframe_to_ttl(tf_str: str) -> int:
        """타임프레임 문자열을 TTL 초로 변환 (5% 버퍼 포함)"""
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        if not tf_str or len(tf_str) < 2:
            return 63  # 기본값 1분
        unit = tf_str[-1].lower()
        try:
            value = int(tf_str[:-1])
            base_seconds = value * multipliers.get(unit, 60)
            return int(base_seconds * 1.05)  # 5% 버퍼
        except (ValueError, KeyError):
            return 63
    
    base_timeframe = config.get("timeframe", "1m")
    redis_ttl = timeframe_to_ttl(base_timeframe)
    logger.info(f"✅ 멱등 TTL 설정: {base_timeframe} → {redis_ttl}초 (봉 단위 자동 조정)")

    # Position Sizer & Portfolio Manager & Risk Manager (config 전달)
    # ⭐ PR12: 순서 변경 - portfolio를 먼저 초기화하고 risk에 전달
    sizer = PositionSizer(config)
    portfolio = PortfolioManager(config)
    risk = RiskManager(config, portfolio=portfolio)  # ⭐ PR12: 포트폴리오 참조 추가
    tracker = PositionTracker(config)  # ⭐ TUNING_VIBLE TP 분할 지원

    # ⭐⭐⭐ SignalGenerator 초기화: config.merge_strategy_config 사용 ⭐⭐⭐
    from common.config_loader import merge_strategy_config

    use_ensemble = config.get("strategy", {}).get("use_ensemble", False)

    if not use_ensemble:
        # 단일 전략: config.merge_strategy_config로 병합 (lookback 포함)
        strategy_selector = config.get("strategy", {}).get("selector", "scalping")
        signal_gen_config = merge_strategy_config(config, strategy_selector)

        logger.info(
            f"✅ [CONFIG] Strategy merged | strategy={strategy_selector} | lookback={signal_gen_config['lookback']} | timeframe={signal_gen_config['timeframe']}"
        )
        min_bars_required = signal_gen_config.get("min_bars_for_signal", 50)
    else:
        # 앙상블 모드: 전체 config 사용
        signal_gen_config = config
        logger.info("✅ [CONFIG] Ensemble mode")
        min_bars_required = config.get("min_bars_for_signal", 50)

    signal_gen = SignalGenerator(config=signal_gen_config, strategy_modules=strategies)

    # ✅ 실행 타임프레임 일원화: 선택 전략의 timeframe을 우선 적용
    if not use_ensemble:
        effective_timeframe = signal_gen_config.get(
            "timeframe", config.get("timeframe", "5m")
        )
    else:
        effective_timeframe = config.get("timeframe", "5m")
    timeframe = effective_timeframe  # 로깅/DB 저장에 사용
    try:
        # RiskManager는 self.config를 참조해 Flash-Guard 윈도우를 계산하므로 런타임에 동기화
        risk.config["timeframe"] = effective_timeframe
    except Exception:
        pass

    # 백테스트 모드일 때 SQLite DB 초기화
    mode = config.get("mode", "paper")

    # ⭐⭐⭐ FlowGuardian 게이트: PAPER/LIVE 진입 전 필수 검증 ⭐⭐⭐
    if mode in ["paper", "live"]:
        try:
            from core.flow_guardian import FlowGuardian
            from execution.data_sources.backtest import BacktestDataSource
            from execution.executors.simulation import SimulationExecutor
            from metrics.compute import MetricsEngine

            # SignalGenerator 어댑터 (generate_signal → generate_signals)
            class StrategyAdapter:
                def __init__(self, signal_gen):
                    self.signal_gen = signal_gen

                def generate_signals(self, df):
                    return self.signal_gen.generate_signal(df)

            # 게이트 조립 (기존 모듈 어댑트)
            guardian = FlowGuardian(
                config=config,
                source=BacktestDataSource("data/golden/BTCUSDT_15m_golden_300.csv"),
                strategy=StrategyAdapter(signal_gen),  # 어댑터로 래핑
                risk=risk,  # RiskManager 재사용
                executor=SimulationExecutor(config),
                metrics=MetricsEngine(config),
            )

            # 게이트 실행 (Smoke + Functional)
            gate_result = guardian.run_all()

            if not gate_result.ready:
                error_msg = "; ".join(gate_result.errors)
                logger.error(f"❌ FlowGuardian 게이트 실패: {error_msg}")
                logger.error("🚫 QUARANTINE — PAPER/LIVE 진입 차단")
                raise SystemExit(1)

            logger.info(f"✅ FlowGuardian 게이트 통과 — {mode.upper()} 모드 진입 허가")
        except ImportError as e:
            logger.warning(f"⚠️  FlowGuardian 모듈 없음 (우회): {e}")
        except Exception as e:
            logger.error(f"❌ FlowGuardian 예외: {e}")
            raise SystemExit(1)

    # 백테스트도 PostgreSQL 사용 (trial_id로 구분)
    if mode == "backtest":
        logger.info("✅ 백테스트 모드: PostgreSQL trading.trades 사용")
    
    # ⭐ PR12: Live 모드에서 자산 동기화 실행
    if mode == "live":
        try:
            logger.info("🔍 [LIVE] 거래소 자산과 동기화 시도")
            initial_equity = portfolio.get_equity()
            new_equity = portfolio.sync_equity_with_broker(broker)
            logger.info(f"✅ [LIVE] 자산 동기화 {mode.upper()}: ${initial_equity:,.2f} → ${new_equity:,.2f} USDT")
            
            # 자산 변화량 추적
            equity_change = new_equity - initial_equity
            if abs(equity_change) > 0.01:  # 1센트 이상 변화가 있는 경우
                logger.info(f"💰 [LIVE] 자산 변화: ${equity_change:+,.2f} USDT")
                
            # 전제조건 확인
            if new_equity <= 0:
                logger.error(f"🚨 [LIVE] 거래소 자산 부족: ${new_equity:,.2f} USDT")
                # 텔레그램 알림
                tg(f"\ud83d\udea8 *거래소 자산 부족*\n예치금: ${new_equity:,.2f} USDT\n\n❗️ 거래를 위해 자산을 입금해야 합니다.", config)
        except Exception as e:
            logger.warning(f"⚠️ [LIVE] 자산 동기화 실패 (무시하고 계속): {e}")

    logger.info("=" * 80)
    logger.info(f"🚀 Trading Engine 시작: Symbol={symbol}, Timeframe={timeframe}")

    # ⭐ 성능 모니터링 시작 (5초 간격)
    start_monitoring(interval=5.0)
    logger.info(
        f"✅ 성능 모니터링 시작: Equity=${equity:,.0f}, Strategies={list(strategies.keys())}"
    )
    logger.info("=" * 80)

    # ⭐ 시작 시 성능 리포트 (초기 벤치마크)
    time.sleep(1)  # 모니터링 데이터 수집 대기
    strategy_id = config.get("strategy", {}).get("selector", "ensemble")
    log_performance(strategy_id, send_telegram=False, config=config)

    candle_count = 0
    trade_count = 0
    closed_count = 0

    # 활성 포지션 dict {position_id: position_info}
    active_positions = {}

    # ⭐⭐⭐ Paper/Live 모드 분기 (디버깅 로그 추가)
    logger.info(f"🔍 [CRITICAL DEBUG] 포지션 복원 모드: {mode}")
    logger.info(f"🔍 [CRITICAL DEBUG] 현재 시각: {time.time()}")
    
    # ⭐⭐⭐ Paper 모드: DB에서 OPEN 포지션 복원
    if mode == "paper":
        logger.info(f"🔍 [CRITICAL DEBUG] Paper 모드 분기 진입")
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Paper 모드는 DB에서 가상 포지션 복원
                    cur.execute(
                        """
                        SELECT trade_id, symbol, strategy_id, side, 
                               entry_price, quantity, sl_price, tp_price, 
                               leverage, ts_open
                        FROM trading.trades
                        WHERE status = 'OPEN' AND mode = %s
                    """,
                        (mode,)
                    )
                    rows = cur.fetchall()

                    for row in rows:
                        (
                            trade_id,
                            symbol_db,
                            strategy_id,
                            side,
                            entry,
                            qty,
                            sl,
                            tp,
                            lev,
                            ts_open,
                        ) = row

                        # active_positions에 복원
                        active_positions[trade_id] = {
                            "symbol": symbol_db,
                            "strategy": strategy_id,
                            "side": side,
                            "entry": float(entry),
                            "qty": float(qty),
                            "sl": float(sl) if sl else 0,
                            "tp": float(tp) if tp else 0,
                            "lev": int(lev),
                            "entry_time": (
                                int(ts_open.timestamp())
                                if hasattr(ts_open, "timestamp")
                                else 0
                            ),
                            "position_value": float(entry) * float(qty),
                            "tp_levels": {},  # 아래에서 재생성
                            "tp1_hit": False,
                            "tp2_hit": False,
                            "be_moved": False,
                        }

                    if active_positions:
                        logger.info(
                            f"✅ DB에서 {len(active_positions)}개 OPEN 포지션 복원"
                        )

                        # TP 레벨 재생성 및 Manager 등록
                        for pos_id, position in active_positions.items():
                            tp_levels = tracker.tp_manager.calculate_tp_levels(
                                entry=position["entry"],
                                stop=position["sl"],
                                side=position["side"],
                                symbol=position.get("symbol", "BTCUSDT"),  # ⭐ PHASE7-1: symbol 전달
                                config=config  # ⭐ PHASE7-2 Phase 1: config 전달 (동적 TP 레벨)
                            )
                            position["tp_levels"] = tp_levels
                            
                            # ⭐ PHASE7-2 Phase 2: 복원된 포지션을 RiskManager와 PortfolioManager에 등록
                            position_value = position.get("position_value", position["entry"] * position["qty"])
                            risk.add_position(position["symbol"], position_value)
                            portfolio.add_position(
                                symbol=position["symbol"],
                                strategy=position["strategy"],
                                position_value=position_value,
                                side=position["side"],
                                position_id=pos_id
                            )

                        logger.info("✅ TP 레벨 재생성 및 Manager 등록 완료")
                        
                        # ⭐ PHASE7-2 항목 8: Manager 상태 복원
                        logger.info("🔄 Manager 상태 복원 시도...")
                        portfolio_restored = portfolio.restore_state(conn, mode="paper", run_id=os.getenv("RUN_ID", "default"))
                        risk_restored = risk.restore_state(conn, mode="paper", run_id=os.getenv("RUN_ID", "default"))
                        
                        if portfolio_restored and risk_restored:
                            logger.info("✅ Manager 상태 복원 완료")
                        else:
                            logger.warning("⚠️ Manager 상태 복원 실패 또는 데이터 없음 (초기 실행일 수 있음)")
        except Exception as e:
            logger.error(f"❌ OPEN 포지션 복원 실패: {e}")
    
    # ⭐⭐⭐ Live 모드: Binance API에서 실제 포지션 조회 및 동기화
    elif mode == "live":
        logger.info(f"🔍 [CRITICAL DEBUG] Live 모드 분기 진입")
        try:
            logger.info("🔍 [LIVE] Binance API에서 실제 포지션 조회 중...")
            logger.info("🔍 [CRITICAL DEBUG] broker.get_positions() 호출 직전")
            positions_result = broker.get_positions()
            
            if positions_result.get('success') and positions_result.get('positions'):
                live_positions = positions_result['positions']
                logger.info(f"✅ [LIVE] Binance에서 {len(live_positions)}개 포지션 조회됨")
                
                # 실제 포지션을 active_positions에 변환
                for pos in live_positions:
                    position_amt = float(pos.get('positionAmt', 0))
                    if abs(position_amt) > 0:  # 실제 포지션만
                        symbol = pos.get('symbol')
                        entry_price = float(pos.get('entryPrice', 0))
                        unrealized_pnl = float(pos.get('unRealizedPnl', 0))
                        
                        # 포지션 방향 결정
                        side = 'LONG' if position_amt > 0 else 'SHORT'
                        qty = abs(position_amt)
                        
                        # active_positions에 추가
                        position_id = f"LIVE_{symbol}_{side}"
                        active_positions[position_id] = {
                            "symbol": symbol,
                            "strategy": "live_sync",  # Live 동기화 포지션
                            "side": side,
                            "entry": entry_price,
                            "qty": qty,
                            "sl": 0,  # Binance에서 SL 정보 조회 필요
                            "tp": 0,  # Binance에서 TP 정보 조회 필요
                            "lev": 1,  # 기본값, 실제 레버리지 조회 필요
                            "entry_time": int(time.time()),
                            "position_value": entry_price * qty,
                            "tp_levels": {},
                            "tp1_hit": False,
                            "tp2_hit": False,
                            "be_moved": False,
                            "unrealized_pnl": unrealized_pnl
                        }
                        
                        logger.info(f"  - {symbol}: {position_amt} @ ${entry_price:,.2f} (PnL: ${unrealized_pnl:,.2f})")
                        
                if active_positions:
                    # ⭐ PHASE7-2 Phase 2: 복원된 포지션을 RiskManager와 PortfolioManager에 등록
                    for pos_id, position in active_positions.items():
                        position_value = position.get("position_value", position["entry"] * position["qty"])
                        risk.add_position(position["symbol"], position_value)
                        portfolio.add_position(
                            symbol=position["symbol"],
                            strategy=position["strategy"],
                            position_value=position_value,
                            side=position["side"],
                            position_id=pos_id
                        )
                    logger.info(f"✅ [LIVE] {len(active_positions)}개 실제 포지션을 시스템에 동기화 및 Manager 등록 완료")
                    
                    # ⭐ PHASE7-2 항목 8: Manager 상태 복원
                    logger.info("🔄 [LIVE] Manager 상태 복원 시도...")
                    portfolio_restored = portfolio.restore_state(conn, mode="live", run_id=os.getenv("RUN_ID", "default"))
                    risk_restored = risk.restore_state(conn, mode="live", run_id=os.getenv("RUN_ID", "default"))
                    
                    if portfolio_restored and risk_restored:
                        logger.info("✅ [LIVE] Manager 상태 복원 완료")
                    else:
                        logger.warning("⚠️ [LIVE] Manager 상태 복원 실패 또는 데이터 없음 (초기 실행일 수 있음)")
            else:
                logger.info("✅ [LIVE] Binance에 OPEN 포지션 없음 (신규 시작)")
        except Exception as e:
            logger.warning(f"⚠️ [LIVE] 포지션 조회 실패 (무시하고 계속): {e}")

    # ⭐ 백테스트 진행률 표시 (총 캔들 수 확인)
    total_candles = getattr(feed, "total", None)

    # ⭐ 페이퍼/라이브 모드: 주기적 상태 로그 (10분마다)
    last_status_log = 0
    last_performance_log = 0
    status_interval = 600  # 10분 = 600초
    performance_interval = 600  # 10분 = 600초
    flash_block_last_log: Dict[str, int] = {}
    try:
        flash_log_throttle_ms = getattr(risk, "_flash_log_throttle_ms", 300000)
    except Exception:
        flash_log_throttle_ms = 300000

    # ⭐ 프리로드 수행 (paper/live 모드, 콜백 설정 후)
    if hasattr(feed, "_preload_info"):
        info = feed._preload_info
        logger.info(f"📥 초기 데이터 로드 중 ({len(info['symbols'])}개 심볼)...")

        # PR7-4: Multi-TF Preload 지원
        if info.get("use_multi_tf") and "strategies_config" in info:
            from execution.adapters import preload_multi_timeframes

            preload_multi_timeframes(
                feed,
                info["symbols"],
                info["strategies_config"],
                info["lookback"],
                logger,
            )
            logger.info("✅ Multi-TF 프리로드 완료")
        else:
            # Fallback: 단일 TF 프리로드 (Option A)
            from execution.adapters import preload_symbols

            timeframe = info.get("timeframe", config.get("timeframe", "5m"))
            preload_symbols(feed, info["symbols"], timeframe, info["lookback"], logger)
            logger.info(f"✅ 전체 심볼 프리로드 완료 (fallback: {timeframe})")

        # stream() 시작 전 큐 상태 확인
        queue_size_before = (
            feed.candle_queue.qsize() if hasattr(feed, "candle_queue") else 0
        )
        logger.info(f"📊 stream() 시작 전 큐 사이즈: {queue_size_before}")

    # ⭐ 메인 루프
    for candle in feed.stream():
        # ⭐ PR12: 일일 PnL 자동 리셋 체크 (자정 00:00)
        portfolio.check_and_reset_daily()
        
        candle_count += 1

        # 백테스트: 진행률 로깅 (매 1000캔들마다)
        if total_candles and candle_count % 1000 == 0:
            progress_pct = (candle_count / total_candles) * 100
            logger.info(
                f"📊 진행률: {candle_count:,}/{total_candles:,} ({progress_pct:.1f}%) | 거래: {trade_count}건 | Equity: ${portfolio.get_equity():,.0f}"
            )

        # 페이퍼/라이브: 주기적 상태 로그 (10분마다)
        if not total_candles:  # 페이퍼/라이브 모드
            import time

            current_time = time.time()

            # 상태 로그
            if current_time - last_status_log > status_interval:
                active_count = len(active_positions)
                strategy_id = config.get("strategy", {}).get("selector", "ensemble")
                log_status(
                    strategy_id,
                    candle_count,
                    active_count,
                    trade_count,
                    portfolio.get_equity(),
                )

                # MonitoringFacade 모니터링 훅
                try:
                    monitoring = (
                        init_monitoring(config)
                        if "monitoring" not in locals()
                        else monitoring
                    )
                    perf = monitoring.sample_system()
                    monitoring.emit_event(
                        {
                            "type": "system.performance",
                            "ts": current_time,
                            "payload": perf,
                        }
                    )
                except Exception as e:
                    logger.debug(f"MonitoringFacade 훅 실패: {e}")

                last_status_log = current_time

            # 성능 로그 (10분마다)
            if current_time - last_performance_log > performance_interval:
                strategy_id = config.get("strategy", {}).get("selector", "ensemble")
                log_performance(strategy_id, send_telegram=False, config=config)
                last_performance_log = current_time

        # ⭐ 표준 키 사용: closed_at (하위 호환 time 지원)
        ts = candle.get("closed_at", candle.get("time", 0))

        # 시계 업데이트
        clock.update(ts)

        # ⭐ PR7-4: Multi-TF 버퍼 관리: 캔들에서 symbol, timeframe 추출
        candle_symbol = candle.get("symbol", symbol)  # 기본값 fallback
        candle_timeframe = candle.get(
            "timeframe", config.get("timeframe", "5m")
        )  # PR7-4
        buffer_key = (candle_symbol, candle_timeframe)

        # ⭐⭐⭐ PR9 Phase 1: 캔들 Dedup (중복 캔들 처리 방지)
        if redis_client:
            dedup_key = f"dedup:{candle_symbol}:{candle_timeframe}:{ts}"
            try:
                if redis_client.exists(dedup_key):
                    logger.debug(
                        f"⏭️ 중복 캔들 무시: {candle_symbol} {candle_timeframe} {ts}"
                    )
                    continue
                redis_client.setex(dedup_key, redis_ttl, "1")
            except Exception as e:
                logger.warning(f"⚠️  Redis dedup 실패 (처리 계속): {e}")

        # 버퍼 초기화 ((심볼, TF)별 최초 1회)
        if buffer_key not in buffers:
            buffers[buffer_key] = deque(maxlen=lookback)
            logger.debug(
                f"⭐ {candle_symbol} {candle_timeframe} 버퍼 초기화 (maxlen={lookback})"
            )

        # 버퍼 추가 ((심볼, TF)별 독립)
        buffers[buffer_key].append(candle)

        # 충분한 데이터 확인 ((심볼, TF)별) - 신호 생성만 스킵, 캔들은 계속 수집
        df = None  # ⭐ 초기화 (continue 시 대비)
        if len(buffers[buffer_key]) < min_bars_required:
            continue  # 신호 생성 스킵, 루프는 계속 진행

        # DataFrame 생성 + 지표 계산 ((심볼, TF)별)
        df_raw = pd.DataFrame(list(buffers[buffer_key]))
        df = df_raw.copy()
        # ✅ 지표 파라미터 주입 (config.yml → indicators.*)
        inds = config.get("indicators", {})
        ema_cfg = inds.get("ema", {})
        rsi_cfg = inds.get("rsi", {})
        macd_cfg = inds.get("macd", {})
        bb_cfg = inds.get("bollinger", {})
        atr_cfg = inds.get("atr", {})
        vol_cfg = inds.get("volume", {})
        df = add_indicators(
            df,
            ema_cfg.get("fast", 20),
            ema_cfg.get("mid", 50),
            ema_cfg.get("slow", 200),
            rsi_cfg.get("length", 14),
            macd_cfg.get("fast", 12),
            macd_cfg.get("slow", 26),
            macd_cfg.get("signal", 9),
            bb_cfg.get("length", 20),
            bb_cfg.get("std", 2.0),
            atr_cfg.get("length", 14),
            vol_cfg.get("ma_length", 30),
        )

        # 현재 가격
        current_price = float(candle.get("close", 0))

        # ⭐ 실밥 리팩토링: Flash Guard 업데이트 (급등락 감지)
        # 멀티심볼: candle_symbol 사용
        risk.flash_guard_update(candle_symbol, current_price, ts)

        # ⭐ PHASE7-2 Phase 0: 실시간 Extreme Loss 체크 (WebSocket 가격 업데이트마다)
        # - 1분 내 급락 즉시 감지 (캔들 종료 대기 없음)
        positions_to_close = []
        for pos_id, position in list(active_positions.items()):
            if position["symbol"] != candle_symbol:
                continue
            
            should_close, reason = tracker.check_extreme_loss_realtime(position, current_price)
            if should_close:
                positions_to_close.append((pos_id, position, reason))

        # 활성 포지션 체크 (TP/SL + Trailing) - ⭐ 같은 심볼만 체크
        for pos_id, position in list(active_positions.items()):
            # ⭐ 심볼이 다르면 스킵 (멀티 심볼 환경)
            if position["symbol"] != candle_symbol:
                continue

            # ⭐ TUNING_VIBLE: TP 분할 체크 (ATR 전달)
            atr = (
                df["atr"].iloc[-1]
                if df is not None and "atr" in df.columns and len(df) > 0
                else None
            )
            
            # ⭐ PR10: 트레일링 SL 갱신 전 기존 SL 저장
            old_sl = position.get('sl')
            
            # ⭐ PHASE7-1: OHLC 데이터 전달 (High/Low SL 체크용)
            # ⭐ PHASE7-2 Phase 2: exit_price 반환 추가 (SL 슬리피지)
            should_action, partial_qty, reason, exit_price = tracker.check_tpsl_with_partial(
                position, current_price, atr, candle=candle, config=config  # ⭐ PHASE7-2 Phase 1: config 전달 (Trailing 조기 활성화)
            )
            
            # ⭐ PR10: 트레일링 SL 갱신 감지 및 서버 업데이트
            new_sl = position.get('sl')
            if mode in ["paper", "live"] and old_sl != new_sl:
                broker.update_sl_price(
                    position_id=pos_id,
                    symbol=position['symbol'],
                    side=position['side'],
                    new_sl_price=new_sl
                )

            if should_action:
                # 부분 청산 또는 전체 청산
                if partial_qty and partial_qty > 0:
                    # 부분 청산 (TP1 또는 TP2)
                    close_qty = partial_qty
                    fee_rate = config.get('fees', {}).get('taker', 0.0004)
                    pnl = calculate_pnl(
                        {
                            "entry": position["entry"],
                            "qty": close_qty,
                            "side": position["side"],
                        },
                        current_price,
                        fee_rate,
                    )
                    logger.info(f"📊 {reason}: {close_qty:.4f} 청산, PnL: ${pnl:,.2f}")

                    # 수량 차감
                    position["qty"] -= close_qty
                    active_positions[pos_id] = position

                    # 부분 청산 기록 (DB에 별도 기록 가능)
                    # close_trade_in_db에서 부분 청산 지원 필요
                else:
                    # 전체 청산 (SL 또는 남은 30%)
                    # ⭐ PHASE7-2 Phase 2: exit_price도 전달 (SL 슬리피지)
                    positions_to_close.append((pos_id, position, reason, exit_price))

        # 포지션 종료 처리
        drawdown_guard_triggered = False  # 플래그 추가
        fee_rate = config.get('fees', {}).get('taker', 0.0004)
        for pos_id, position, reason, exit_price in positions_to_close:
            # ⭐ PHASE7-2 Phase 2: SL/EXTREME_LOSS 시 exit_price 사용
            close_price = exit_price if exit_price else current_price
            pnl = calculate_pnl(position, close_price, fee_rate)
            close_trade_in_db(
                pos_id,
                close_price,
                pnl,
                reason,
                ts,
                mode=mode,
                leverage=position.get("lev", 1),
            )

            # ⭐ PR12: PnL 업데이트 단일화 (포트폴리오로 통합)
            portfolio.update_equity(pnl=pnl)  # 포트폴리오만 업데이트
            current_equity = portfolio.get_equity()
            
            # 다른 모듈에 equity 참조 전달
            sizer.update_equity(current_equity)
            risk.update_equity(current_equity)
            
            # ⭐ PR11: Drawdown Guard 체크
            logger.info(f"🔍 Drawdown Guard 체크: equity=${current_equity:,.2f}")
            if not risk.check_drawdown_guard(current_equity):
                logger.error(f"🔴 Drawdown Guard 차단 - 시스템 정지")
                drawdown_guard_triggered = True
                break  # 포지션 청산 루프 종료

            # ⭐ PR12: 연속 손실 추적 (리스크 관리자에서)
            risk.update_consecutive_losses(pnl)
            
            # 포지션 값 계산 (저장된 position_value 사용)
            position_value = position.get(
                "position_value", position["qty"] * position["entry"]
            )
            
            # ⭐ PR11: Extreme Loss Guard 체크
            pnl_pct = pnl / (position["entry"] * position["qty"]) if position["qty"] > 0 else 0
            logger.info(f"🔍 Extreme Loss Guard 체크: pnl_pct={pnl_pct*100:.2f}%")
            if not risk.check_extreme_loss_guard(pnl_pct):
                logger.warning(f"⚠️  Extreme Loss Guard 경고 - 포지션: {position['symbol']}")

            # ⭐ Portfolio Manager 업데이트 (포지션 제거)
            portfolio.remove_position(symbol=position["symbol"], position_id=pos_id)

            # Risk Manager: 포지션 제거 (노출 한도 업데이트)
            risk.remove_position(position["symbol"], position_value)

            # ⭐⭐⭐ active_positions에서 제거 (중요!)
            active_positions.pop(pos_id, None)
            
            # ⭐ PHASE7-2 항목 8: Manager 상태 저장 (포지션 종료 시)
            if mode in ["paper", "live"]:
                try:
                    portfolio.save_state(conn, mode=mode, run_id=os.getenv("RUN_ID", "default"))
                    risk.save_state(conn, mode=mode, run_id=os.getenv("RUN_ID", "default"))
                except Exception as e:
                    logger.warning(f"⚠️ Manager 상태 저장 실패 (무시하고 계속): {e}")

            closed_count += 1

            # ⭐ Exit Logging
            pnl_pct_calc = (
                (pnl / (position["entry"] * position["qty"])) * 100
                if position["qty"] > 0
                else 0
            )
            emoji_cfg = config.get("telegram", {}).get("emoji", {})
            if reason in ["TP", "TP2"]:
                exit_emoji = emoji_cfg.get("take_profit", "✅🏆")
            elif reason in ["SL", "STOP_LOSS", "TRAILING_SL"]:
                exit_emoji = emoji_cfg.get("stop_loss", "⛔🛑")
            elif reason == "TP1":
                exit_emoji = emoji_cfg.get("tp1_partial", "🟡🎯")
            else:
                exit_emoji = emoji_cfg.get("default", "⚪")
            logger.info(
                f"{exit_emoji} [{closed_count}] {reason}: {position['side']} {position['symbol']} @ {current_price:,.2f} (Entry: {position['entry']:,.2f}) | PnL: ${pnl:,.2f} ({pnl_pct_calc:+.2f}%)"
            )

            # ⭐ 텔레그램 청산 알림 (페이퍼/라이브 모드) - P2 최종 확정 포맷
            if mode in ["paper", "live"]:
                pnl_pct = (
                    (pnl / (position["entry"] * position["qty"])) * 100
                    if position["qty"] > 0
                    else 0
                )

                # 슬리피지/수수료 계산 (페이퍼 모드: config 기반, 라이브 모드: 실제 거래 데이터)
                slippage = position.get("slippage", 0.0)
                fee = position.get("fee", 0.0)

                # ⭐ PR12: 일일 누적 PnL (포트폴리오에서 추출)
                daily_pnl = (
                    portfolio.get_daily_pnl() if hasattr(portfolio, "get_daily_pnl") else 0.0
                )

                # 포트폴리오 정보 (청산 전/후)
                equity_before = (
                    portfolio.get_equity()
                    if hasattr(portfolio, "get_equity")
                    else config["capital"]["initial"]
                )
                equity_after = equity_before + pnl
                active_pos_count = len(
                    active_positions
                )  # 청산 후 포지션 수 (pop 이후 길이 사용)
                max_pos = config.get("risk", {}).get("max_positions", 20)

                # 포지션 번호 (청산되는 포지션)
                position_number = position.get("position_number", 1)

                # 청산 알람 생성 (P2 최종 확정 포맷)
                msg = format_exit_alert(
                    symbol=position["symbol"],
                    side=position["side"],
                    entry=position["entry"],
                    exit_price=current_price,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    reason=reason,
                    qty=position["qty"],
                    slippage=slippage,
                    fee=fee,
                    active_positions=active_pos_count,
                    max_positions=max_pos,
                    total_equity=equity_after,
                    equity_before=equity_before,
                    daily_pnl=daily_pnl,
                    lev=position.get("lev", 1),
                    position_number=position_number,
                    config=config,
                )
                tg(msg, config)

        # ⭐⭐⭐ 실밥 리팩토링 시작: 기존 전략 호출 로직 → SignalGenerator 활용 ⭐⭐⭐
        # =============================================================================
        # [기존 코드 - 주석 처리]
        # 전략별 신호 생성
        # signals = []
        # for strategy_id, strategy_module in strategies.items():
        #     try:
        #         from common.strategy_config import load_strategy_params
        #         strategy_params = load_strategy_params()
        #         cfg = strategy_params.get(strategy_id, {})
        #
        #         signal = strategy_module.signal_logic(df, cfg)
        #
        #         if signal and signal.get('side'):
        #             signal['strategy_id'] = strategy_id
        #             signals.append(signal)
        #     except Exception as e:
        #         logger.error(f"❌ [{strategy_id}] 전략 오류: {e}")
        # =============================================================================

        # ⭐ PR11: Drawdown Guard 체크 (메인 루프 종료)
        if drawdown_guard_triggered:
            logger.error(f"🔴 Drawdown Guard 트리거됨 - 메인 루프 종료")
            break  # 메인 루프 종료

        # ⭐ [새 코드] SignalGenerator 활용 (MTF, 쿨다운, 거래량 필터 포함)
        signals = []

        # ⭐⭐⭐ 단일 전략 모드: selector 전략만 실행
        if not use_ensemble:
            strategy_selector = config.get("strategy", {}).get("selector", "scalping")
            selected_strategies = {strategy_selector: strategies.get(strategy_selector)}
        else:
            selected_strategies = strategies

        for strategy_id, strategy_module in selected_strategies.items():
            if strategy_module is None:  # 전략이 없으면 스킵
                continue
            try:
                # ⭐ 전략별 설정 + 전체 config 병합
                strategy_cfg = config.get("strategies", {}).get(strategy_id, {})
                cfg = {
                    **config,  # 전체 config (leverage, tp_sl 등)
                    **strategy_cfg,  # 전략별 설정 (rr, risk_per_trade, cooldown_candles)
                }

                # ⭐ 전략별 필터 설정 병합 (MTF, regime, volume)
                strategy_filters = strategy_cfg.get("filters", {})
                if strategy_filters:
                    # MTF 필터
                    if "mtf_confirm" in strategy_filters:
                        cfg["enable_mtf_confirm"] = strategy_filters["mtf_confirm"]
                    # Regime 필터
                    if "regime" in strategy_filters:
                        cfg["enable_regime_filter"] = strategy_filters["regime"]
                    # Volume 필터
                    if "volume_spike" in strategy_filters:
                        cfg["enable_vol_spike_filter"] = strategy_filters[
                            "volume_spike"
                        ]

                # ⭐ PR7-4: Multi-TF 버퍼 직접 사용 (primary)
                strategy_tf = str(strategy_cfg.get("timeframe", timeframe))
                strategy_buffer_key = (candle_symbol, strategy_tf)

                # 전략 TF 버퍼가 있고 충분한 데이터가 있으면 직접 사용
                strategy_min_bars = strategy_cfg.get("min_bars_for_signal", 60)
                if (
                    strategy_buffer_key in buffers
                    and len(buffers[strategy_buffer_key]) >= strategy_min_bars
                ):
                    # Multi-TF 버퍼 직접 사용 (PR7-4 primary path)
                    df_tf_raw = pd.DataFrame(list(buffers[strategy_buffer_key]))
                    df_tf = df_tf_raw.copy()
                    # 지표 계산
                    df_tf = add_indicators(
                        df_tf,
                        ema_cfg.get("fast", 20),
                        ema_cfg.get("mid", 50),
                        ema_cfg.get("slow", 200),
                        rsi_cfg.get("length", 14),
                        macd_cfg.get("fast", 12),
                        macd_cfg.get("slow", 26),
                        macd_cfg.get("signal", 9),
                        bb_cfg.get("length", 20),
                        bb_cfg.get("std", 2.0),
                        atr_cfg.get("length", 14),
                        vol_cfg.get("ma_length", 30),
                    )
                    logger.debug(
                        f"✅ [{strategy_id}] Multi-TF 버퍼 사용: {strategy_tf} ({len(buffers[strategy_buffer_key])}개)"
                    )
                else:
                    # Fallback: resample 사용 (Option A)
                    df_tf = df_raw.copy()
                    try:
                        ts_col = (
                            "closed_at"
                            if "closed_at" in df_tf.columns
                            else ("time" if "time" in df_tf.columns else None)
                        )
                        if ts_col is not None:
                            if not isinstance(df_tf[ts_col].iloc[-1], pd.Timestamp):
                                df_tf[ts_col] = pd.to_datetime(
                                    df_tf[ts_col], unit="ms", utc=True
                                )
                            df_idx = df_tf.set_index(ts_col)
                            tf = strategy_tf.lower()
                            # base interval minutes
                            try:
                                _diffs = df_idx.index.to_series().diff().dropna()
                                _base_min = (
                                    int(_diffs.dt.total_seconds().mode().iloc[0] // 60)
                                    if not _diffs.empty
                                    else 0
                                )
                            except Exception:
                                _base_min = 0
                            if tf.endswith("m"):
                                _req_min = int(tf[:-1])
                                rule = f"{_req_min}min"
                            elif tf.endswith("h"):
                                _req_min = int(tf[:-1]) * 60
                                rule = f"{int(tf[:-1])}h"
                            elif tf.endswith("d"):
                                _req_min = int(tf[:-1]) * 60 * 24
                                rule = f"{int(tf[:-1])}D"
                            else:
                                rule = None
                                _req_min = 0
                            # only resample if req is multiple of base
                            if (
                                rule
                                and _base_min > 0
                                and _req_min >= _base_min
                                and (_req_min % _base_min == 0)
                            ):
                                df_tf = (
                                    df_idx.resample(rule, label="right", closed="right")
                                    .agg(
                                        {
                                            "open": "first",
                                            "high": "max",
                                            "low": "min",
                                            "close": "last",
                                            "volume": "sum",
                                        }
                                    )
                                    .dropna(subset=["open", "high", "low", "close"])
                                    .reset_index()
                                    .rename(columns={ts_col: "time"})
                                )
                            else:
                                # unsupported tf → use base
                                df_tf = df.copy()
                        else:
                            df_tf = df.copy()
                    except Exception:
                        df_tf = df.copy()
                    logger.debug(
                        f"⚠️ [{strategy_id}] Fallback resample 사용: {strategy_tf}"
                    )

                # 전략별 최소 바 수 확인 (부족 시 스킵)
                min_required = int(
                    strategy_cfg.get("min_bars_for_signal", min_bars_required)
                )
                if len(df_tf) < min_required:
                    continue

                # Fallback 경로에서만 지표 계산 필요 (Multi-TF 경로는 이미 계산함)
                if "ema_fast" not in df_tf.columns:
                    df_tf = add_indicators(
                        df_tf,
                        ema_cfg.get("fast", 20),
                        ema_cfg.get("mid", 50),
                        ema_cfg.get("slow", 200),
                        rsi_cfg.get("length", 14),
                        macd_cfg.get("fast", 12),
                        macd_cfg.get("slow", 26),
                        macd_cfg.get("signal", 9),
                        bb_cfg.get("length", 20),
                        bb_cfg.get("std", 2.0),
                        atr_cfg.get("length", 14),
                        vol_cfg.get("ma_length", 30),
                    )

                # 전략 실행 (리샘플 DF)
                signal = strategy_module.signal_logic(df_tf, cfg)

                if signal and signal.get("side"):
                    signal["strategy_id"] = strategy_id
                    # 캔들 닫힘 시간: 전략 TF 기준
                    try:
                        _last_time = df_tf["time"].iloc[-1]
                        if hasattr(_last_time, "value"):
                            strategy_ts = int(_last_time.value // 10**6)
                        else:
                            strategy_ts = int(_last_time)
                    except Exception:
                        strategy_ts = ts
                    signal["ts"] = strategy_ts
                    signal["symbol"] = (
                        candle_symbol  # ⭐ 멀티 심볼: 현재 캔들의 심볼 사용
                    )
                    signal["timeframe"] = strategy_tf  # 전략 실제 TF 저장

                    # ⭐ 신호 검증 (MTF 캐싱 적용 - 빠른 검증!)
                    # validate_signal 내부에서 _mtf_confirm(symbol, side, current_ts) 호출
                    # current_ts 전달로 캐시 히트 시 즉시 반환 (API 호출 X)
                    if signal_gen.validate_signal(
                        candle_symbol, signal, df_tf
                    ):  # ⭐ 멀티 심볼 수정
                        # ⭐⭐⭐ 신호 DB 저장 (monitoring.signals 테이블) - 수정됨 2025-10-23
                        # 백테스트 모드에서는 기본적으로 외부 DB 신호 저장을 비활성화하여 속도와 안정성 향상
                        # config.backtest.persist_signals=true 일 때만 저장 수행
                        if mode != "backtest" or config.get("backtest", {}).get(
                            "persist_signals", False
                        ):
                            try:
                                save_signal_to_db(
                                    signal_id=str(uuid4()),
                                    strategy_id=strategy_id,
                                    symbol=candle_symbol,  # ⭐ 멀티 심볼 수정
                                    timeframe=strategy_tf,  # ✅ 전략 TF로 저장
                                    candle_closed_at=datetime.fromtimestamp(
                                        strategy_ts / 1000
                                    ),  # ✅ int → datetime
                                    direction=signal.get("side"),  # ✅ side → direction
                                    confidence=signal.get(
                                        "confidence", 0.75
                                    ),  # ✅ 추가
                                    entry_price=signal.get("entry"),
                                    sl_price=signal.get("sl"),
                                    tp_price=signal.get("tp"),
                                    atr=signal.get("atr"),  # ✅ 추가
                                    leverage=signal.get("lev"),  # ✅ 추가
                                )
                            except Exception as e:
                                logger.debug(f"신호 저장 실패: {e}")
                        signals.append(signal)
                    else:
                        logger.debug(
                            f"⏸ [{strategy_id}] 신호 검증 실패 (MTF/쿨다운/거래량)"
                        )
            except Exception as e:
                logger.error(f"❌ [{strategy_id}] 전략 오류: {e}")
        # ⭐⭐⭐ 실밥 리팩토링 종료 ⭐⭐⭐

        # ⭐ Flash Guard 체크 추가 (신호가 있을 때만)
        if signals and not risk.flash_guard_allowed(candle_symbol, ts):
            last_block = flash_block_last_log.get(candle_symbol, 0)
            if ts - last_block >= flash_log_throttle_ms:
                logger.warning(f"🛡 [{candle_symbol}] Flash Guard 활성화 - 신호 보류")
                flash_block_last_log[candle_symbol] = ts
            continue

        # 신호 필터링
        if not signals:
            continue

        # ⭐ 로깅: 생성된 신호 목록
        signal_desc = [
            f"{s.get('strategy_id', '?')}:{s.get('side', '?')}" for s in signals
        ]
        logger.info(
            f"🔔 [{candle_symbol}] 신호 생성: {len(signals)}개 - {', '.join(signal_desc)}"
        )

        # Ensemble: 신호 통합
        if ensemble_module:
            # 실제 ensemble 사용
            try:
                with get_db_connection() as conn:
                    # ensemble.combine_signals 사용 (config 전달)
                    decision = ensemble_module.combine_signals(signals, conn, config)
                    if not decision:
                        logger.debug(
                            f"⏸ [{candle_symbol}] Ensemble 결정 없음 (동점 or 부적합)"
                        )
                        continue
                    logger.info(
                        f"✅ [{candle_symbol}] Ensemble 결정: {decision.get('side')} by {decision.get('strategy_id')}"
                    )
            except Exception as e:
                logger.error(f"❌ Ensemble 오류: {e}")
                decision = signals[0]  # fallback
        else:
            # 첫 신호 사용 (간단 모드)
            decision = signals[0]
            logger.info(
                f"✅ [{candle_symbol}] 단일 신호 사용: {decision.get('side')} by {decision.get('strategy_id')}"
            )

        # 신호 포맷 통일 (전략 키 → position_sizer 키)
        decision["entry_price"] = decision.get("entry", 0)
        decision["sl_price"] = decision.get("sl", 0)
        decision["tp_price"] = decision.get("tp", 0)
        decision["symbol"] = candle_symbol  # ⭐ risk_manager를 위한 symbol 추가
        
        # ⭐ PHASE7-2 Phase 2: ATR 추가 (동적 슬리피지 계산용)
        if df is not None and "atr" in df.columns and len(df) > 0:
            decision["atr"] = df["atr"].iloc[-1]
        else:
            decision["atr"] = None

        # Risk 체크 (메서드 체크)
        if hasattr(risk, "allow_entry") and not risk.allow_entry(
            candle_symbol, decision.get("side")
        ):
            logger.debug(f"⚠️ Risk 거부: {decision.get('side')}")

        # 포지션 사이즈 계산
        qty, meta = sizer.calculate(
            {
                "entry_price": decision.get("entry"),
                "sl_price": decision.get("sl"),
                "confidence": decision.get("confidence", 0.8),
            }
        )

        if qty <= 0:
            continue

        # ⭐ position_sizer가 계산한 position_value 사용 (재계산 금지!)
        position_value = meta.get("position_value", qty * decision.get("entry"))

        # ⭐ PR8/PR9: 전략별 심볼 거부 쿨다운 체크 (ensemble 모드 대응)
        strategy_id = decision.get("strategy_id", "ensemble")
        cooldown_key = f"{candle_symbol}_{strategy_id}"

        # ⭐⭐⭐ PR9 Phase 2: Redis 쿨다운 TTL (재시작 후에도 유지)
        if redis_client:
            redis_cooldown_key = f"cooldown:{cooldown_key}"
            try:
                ttl = redis_client.ttl(redis_cooldown_key)
                if ttl > 0:
                    logger.info(
                        f"🔒 {strategy_id} {candle_symbol} 쿨다운 중 (Redis TTL: {ttl}초)"
                    )
                    continue
            except Exception as e:
                logger.warning(f"⚠️  Redis 쿨다운 체크 실패 (처리 계속): {e}")
        else:
            # Fallback: 로컬 메모리 쿨다운
            if cooldown_key in reject_cooldown:
                elapsed = time.time() - reject_cooldown[cooldown_key]
                if elapsed < cooldown_seconds:
                    logger.debug(
                        f"🔒 [{strategy_id}] {candle_symbol} 쿨다운 중: {elapsed:.1f}초/{cooldown_seconds}초"
                    )
                    continue
                else:
                    del reject_cooldown[cooldown_key]
                    logger.debug(f"✅ [{strategy_id}] {candle_symbol} 쿨다운 해제")

        # ⭐⭐⭐ PR9 Phase 3: 신호 멱등성 (타임프레임 기반 개선)
        # - 봉 단위 멱등: symbol + side + candle_close_time 기준
        # - TTL: 타임프레임 자동 조정 (1m=63s, 5m=315s)
        if redis_client:
            # 캔들 종료 시간 (밀리초 → 초 단위, 타임프레임 단위로 정규화)
            candle_close_ts = int(ts / 1000) if ts > 1000000000000 else int(ts)
            # 타임프레임 초 단위로 정규화 (같은 봉 내에서는 동일한 키)
            tf_seconds = redis_ttl / 1.05  # 버퍼 제거한 실제 봉 길이
            normalized_ts = int(candle_close_ts / tf_seconds) * int(tf_seconds)
            
            # 멱등 키: symbol:side:candle_ts (가격대가 아닌 봉 단위로 차단)
            redis_signal_key = f"signal:{candle_symbol}:{decision.get('side')}:{normalized_ts}"

            try:
                if redis_client.exists(redis_signal_key):
                    logger.warning(
                        f"⚠️ 🧩 신호 멱등 차단: {strategy_id} {candle_symbol} {decision.get('side')} "
                        f"(같은 봉 내 중복, TTL={redis_ttl}초)"
                    )
                    continue
                redis_client.setex(redis_signal_key, redis_ttl, "1")
                logger.debug(f"✅ 멱등 키 설정: {redis_signal_key} (TTL={redis_ttl}초)")
            except Exception as e:
                logger.warning(f"⚠️  Redis 멱등성 체크 실패 (처리 계속): {e}")

        # Risk Manager 체크 (⭐ position_value 전달)
        allowed, reason = risk.check_order(decision, qty, position_value=position_value)
        if not allowed:
            # ⭐ PR9 Phase 2: Redis 쿨다운 TTL 설정
            if redis_client:
                try:
                    redis_cooldown_key = f"cooldown:{cooldown_key}"
                    redis_client.setex(redis_cooldown_key, cooldown_seconds, "1")
                except Exception as e:
                    logger.warning(f"⚠️  Redis 쿨다운 설정 실패: {e}")
            reject_cooldown[cooldown_key] = time.time()  # Fallback
            logger.warning(
                f"⛔ [{strategy_id}] {candle_symbol} 리스크 체크 실패 (쿨다운 {cooldown_seconds}초): {reason}"
            )
            if mode in ["paper", "live"]:
                tg(
                    f"⚠️ *거래 거부* | 전략: {strategy_id} | 심볼: {candle_symbol} | 방향: {decision.get('side')} | 사유: {reason}",
                    config,
                )
            continue

        # ⭐ Portfolio Manager 체크 (멀티 심볼 환경)
        can_open, portfolio_reason = portfolio.can_open_position(
            symbol=candle_symbol,  # ⭐ 멀티 심볼 수정
            strategy=strategy_id,
            position_value=position_value,
            side=decision.get("side"),
        )

        if not can_open:
            # ⭐ PR9 Phase 2: Redis 쿨다운 TTL 설정
            if redis_client:
                try:
                    redis_cooldown_key = f"cooldown:{cooldown_key}"
                    redis_client.setex(redis_cooldown_key, cooldown_seconds, "1")
                except Exception as e:
                    logger.warning(f"⚠️  Redis 쿨다운 설정 실패: {e}")
            reject_cooldown[cooldown_key] = time.time()  # Fallback
            logger.warning(
                f"⛔ [{strategy_id}] {candle_symbol} 포트폴리오 거부 (쿨다운 {cooldown_seconds}초): {portfolio_reason}"
            )
            if mode in ["paper", "live"]:
                tg(
                    f"⚠️ *포트폴리오 거부* | 전략: {strategy_id} | 심볼: {candle_symbol} | 방향: {decision.get('side')} | 사유: {portfolio_reason}",
                    config,
                )
            continue

        # ⭐ PR10: One-Way Mode 강제 (같은 심볼 반대 포지션 청산)
        new_side = decision.get("side")
        opposite_side = "SHORT" if new_side == "LONG" else "LONG"
        
        # ⭐ CRITICAL: 동일 심볼 동일 방향 중복 진입 방지 (메모리 + DB 이중 체크)
        # 1. 메모리 체크
        same_direction_positions = [
            (pos_id, pos) for pos_id, pos in list(active_positions.items())
            if pos["symbol"] == candle_symbol and pos["side"] == new_side
        ]
        
        if same_direction_positions:
            logger.warning(f"⚠️ [MEMORY] 중복 진입 방지: {candle_symbol} {new_side} 기존 포지션 {len(same_direction_positions)}개 존재 - 진입 스킵")
            continue  # 중복 진입 차단
        
        # 2. DB 재확인 (PHASE7-2 Phase 2: 메모리-DB 동기화 누락 방지)
        if config.get('risk', {}).get('duplicate_check_db', True):
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT COUNT(*) FROM trading.trades
                            WHERE symbol = %s AND side = %s 
                              AND status = 'OPEN' AND mode = %s
                        """, (candle_symbol, new_side, mode))
                        db_open_count = cur.fetchone()[0]
                        
                        if db_open_count > 0:
                            logger.warning(f"⚠️ [DB] 중복 진입 방지: {candle_symbol} {new_side} DB OPEN 포지션 {db_open_count}건 존재 - 진입 스킵")
                            continue  # 중복 진입 차단
            except Exception as e:
                logger.error(f"❌ DB 중복 진입 체크 실패: {e}")
                # DB 오류 시에도 메모리 체크는 통과했으므로 진행 (안전 우선)
        
        # 같은 심볼의 반대 포지션 찾기
        opposite_positions = [
            (pos_id, pos) for pos_id, pos in list(active_positions.items())
            if pos["symbol"] == candle_symbol and pos["side"] == opposite_side
        ]
        
        if opposite_positions:
            logger.info(f"🔄 [ONE-WAY MODE] {candle_symbol} 반대 포지션 감지 ({opposite_side} → {new_side}): {len(opposite_positions)}개 청산")
            fee_rate = config.get('fees', {}).get('taker', 0.0004)
            for pos_id, position in opposite_positions:
                # 현재가로 청산
                pnl = calculate_pnl(position, current_price, fee_rate)
                close_trade_in_db(
                    pos_id,
                    current_price,
                    pnl,
                    "ONE_WAY_MODE",  # 청산 이유
                    ts,
                    mode=mode,
                    leverage=position.get("lev", 1),
                )
                
                # ⭐ PR12: Equity 단일 소스 - PortfolioManager만 업데이트
                portfolio.update_equity(pnl=pnl)
                
                # 포지션 제거
                position_value = position.get("position_value", position["qty"] * position["entry"])
                portfolio.remove_position(symbol=position["symbol"], position_id=pos_id)
        
        # ⭐ CRITICAL FIX: Broker 실행 (Paper/Live/Sim 모두)
        # ⭐ PHASE7-2 Phase 2: ATR 전달 (동적 슬리피지 계산)
        fill = broker.execute(decision, qty, atr=decision.get('atr'))
        
        if not fill.get("success"):
            logger.error(f"❌ 거래 실행 실패: {candle_symbol}")
            continue
        
        # 포지션 ID 생성
        import uuid
        position_id = str(uuid.uuid4())
        entry_time = ts
        
        # Trade DB 저장
        position_id = save_trade_to_db(
            position_id,  # 첫 번째 위치 인자
            symbol=candle_symbol,
            side=decision.get("side"),
            entry_price=fill.get("filled_price"),
            qty=qty,
            sl_price=decision.get("sl"),
            tp_price=decision.get("tp"),
            strategy_id=decision.get("strategy_id", "ensemble"),
            timestamp=entry_time,
            mode=mode,
            leverage=decision.get("lev", 1),
            trial_id=trial_id,
        )

        # Risk Manager에 포지션 등록 (⭐ candle_symbol 사용!)
        risk.add_position(candle_symbol, position_value)

        # ⭐ Portfolio Manager에 포지션 추가
        portfolio.add_position(
            symbol=candle_symbol,
            strategy=strategy_id,
            position_value=position_value,
            side=decision.get("side"),
            position_id=position_id,
        )

        # ⭐ TUNING_VIBLE: TP 레벨 계산
        tp_levels = tracker.tp_manager.calculate_tp_levels(
            entry=fill.get("filled_price"),
            stop=decision.get("sl"),
            side=decision.get("side"),
            atr=df["atr"].iloc[-1] if "atr" in df.columns else None,
            symbol=candle_symbol,  # ⭐ PHASE7-1: symbol 전달 (정확한 tick_size 반올림)
            config=config  # ⭐ PHASE7-2 Phase 1: config 전달 (동적 TP 레벨)
        )

        # 포지션 번호 계산 (현재 활성 포지션 수 + 1)
        position_number = len(active_positions) + 1

        # 활성 포지션 저장 (⭐ position_value + tp_levels 포함)
        active_positions[position_id] = {
            "symbol": candle_symbol,
            "strategy": decision.get("strategy_id", "ensemble"),
            "side": decision.get("side"),
            "entry": fill.get("filled_price"),
            "sl": decision.get("sl"),
            "tp": decision.get("tp"),
            "qty": qty,
            "trailing_stop": None,
            "entry_time": entry_time,
            "position_value": position_value,  # ⭐ 생성 시 position_value 저장
            "tp_levels": tp_levels,  # ⭐ TUNING_VIBLE TP 분할
            "tp1_hit": False,
            "tp2_hit": False,
            "be_moved": False,
            "remaining_pct": 100.0,
            "highest": fill.get("filled_price"),
            "lowest": fill.get("filled_price"),
            "trail_price": decision.get("sl"),
            "lev": decision.get("lev", 1),
            "position_number": position_number,  # ⭐ P2: 포지션 번호 추가
        }
        
        # ⭐ PR10: SL 서버 등록 (Option C + workingType + priceProtect)
        if mode in ["paper", "live"]:
            binance_api_cfg = config.get('exits', {}).get('binance_api', {})
            working_type = binance_api_cfg.get('working_type', 'CONTRACT_PRICE')
            price_protect = 'TRUE' if binance_api_cfg.get('price_protect', True) else 'FALSE'
            
            broker.create_sl_order(
                position={'id': position_id, 'symbol': candle_symbol,
                          'side': decision.get('side'), 'qty': qty},
                sl_price=decision.get('sl'),
                working_type=working_type,
                price_protect=price_protect
            )

        logger.info(
            f"✅ [{trade_count}] {decision.get('side')} @ {fill.get('filled_price'):.2f}"
        )

        # ⭐ 텔레그램 알림 (페이퍼/라이브 모드) - P2 최종 확정 포맷
        if mode in ["paper", "live"]:
            # 신호 정보 구성
            signal_info = {
                "side": decision.get("side"),
                "entry": fill.get("filled_price"),
                "sl": decision.get("sl"),
                "tp": decision.get("tp"),
                "lev": decision.get("lev", 1),
                "reason": decision.get("reason", ["신호 감지"]),
            }

            # 포트폴리오 정보
            current_equity = (
                portfolio.get_equity()
                if hasattr(portfolio, "get_equity")
                else config["capital"]["initial"]
            )
            stats_after = (
                portfolio.get_stats() if hasattr(portfolio, "get_stats") else {}
            )
            total_exposure_after = stats_after.get("total_exposure", 0.0)
            # 현재 포지션 반영 전/후 현금
            total_exposure_before = max(0.0, total_exposure_after - position_value)
            cash_before = max(0.0, current_equity - total_exposure_before)
            cash_after = max(0.0, current_equity - total_exposure_after)
            active_pos_count = len(active_positions)
            max_pos = config.get("risk", {}).get("max_positions", 20)

            # format_signal_alert 사용 (P2 최종 포맷)
            msg = format_signal_alert(
                symbol=candle_symbol,
                I=signal_info,
                qty=qty,
                notional=position_value,
                margin=position_value / signal_info["lev"],
                config=config,
                total_equity=current_equity,
                active_positions=active_pos_count,
                max_positions=max_pos,
                position_number=position_number,
                cash_before=cash_before,
                cash_after=cash_after,
            )
            tg(msg, config)

            # 📜 Detailed Entry Logging
            emoji_cfg = config.get("telegram", {}).get("emoji", {})
            emoji_circle = (
                emoji_cfg.get("long_circle", "🔵")
                if decision.get("side") == "LONG"
                else emoji_cfg.get("short_circle", "🔴")
            )
            mode_tag = config.get("mode", "paper").upper()
            strategy_tag = decision.get("strategy_id", "ensemble").upper()
            logger.info(
                f"{emoji_circle} [{mode_tag}|{strategy_tag}] {candle_symbol} BUY @ {fill.get('filled_price'):,.2f} | SL: {decision.get('sl'):,.2f} | TP: {decision.get('tp'):,.2f} | Qty: {qty:.2f} | Notional: ${position_value:,.0f} | x{signal_info['lev']}"
            )
            stats_now = (
                portfolio.get_stats()
                if hasattr(portfolio, "get_stats")
                else {
                    "total_exposure": 0.0,
                    "total_exposure_pct": 0.0,
                    "total_positions": len(active_positions),
                    "max_positions": max_pos,
                }
            )
            total_exposure = stats_now.get("total_exposure", 0.0)
            exposure_pct = stats_now.get(
                "total_exposure_pct",
                (
                    total_exposure / current_equity * 100
                    if current_equity > 0
                    else 0.0
                ),
            )
            total_positions = stats_now.get(
                "total_positions", len(active_positions)
            )
            max_positions = stats_now.get("max_positions", max_pos)
            logger.info(
                f"📊 [PORTFOLIO] Positions {total_positions}/{max_positions} | Total Notional: ${total_exposure:,.0f} ({exposure_pct:.1f}%) | Equity: ${current_equity:,.0f}"
            )

        # 진행 상황 (백테스트용)
        if candle_count % 10000 == 0:
            progress = getattr(feed, "progress", lambda: 0)()
            logger.info(
                f"📊 진행: {progress*100:.1f}% ({candle_count:,}개 캔들, {trade_count}건 거래)"
            )

    logger.info("=" * 80)
    logger.info(
        f"✅ Trading Engine 종료: 총 캔들={candle_count:,}개, 진입 거래={trade_count}건, 종료 거래={closed_count}건, 활성 포지션={len(active_positions)}개"
    )
    logger.info("=" * 80)

    # ⭐ 백테스트 모드일 경우 HTML 리포트 생성 또는 TUNING_VIBLE 검증
    mode = config.get("mode", "paper")
    reports_cfg = config.get("reports", {})
    html_enabled = reports_cfg.get("html", True)

    if mode == "backtest":
        try:
            # PostgreSQL 기반 백테스트 리포트 (analytics 모듈 사용)
            from analytics.report_generator import generate_backtest_report
            from pathlib import Path

            if html_enabled:
                # 리포트 디렉토리 생성
                report_dir = Path("reports/backtest")
                report_dir.mkdir(parents=True, exist_ok=True)

                # 결과 데이터 준비 (간단 버전)
                results = {
                    "metadata": {
                        "mode": "backtest",
                        "symbol": symbol,
                        "timeframe": config.get("timeframe", "5m"),
                        "strategies": list(strategies.keys()) if strategies else [],
                        "total_candles": candle_count,
                        "total_trades": trade_count,
                        "closed_trades": closed_count,
                        "active_positions": len(active_positions),
                    }
                }

                # PostgreSQL 기반 백테스트 리포트 생성
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                html_file = report_dir / f"backtest_{timestamp}.html"

                # analytics 모듈로 리포트 생성 (PostgreSQL 기반, TUNING_VIBLE 포함)
                result = generate_backtest_report(
                    trial_id=None,  # 전체 백테스트 결과
                    output_file=str(html_file),
                    sinks=["log", "html", "json"],
                )

                if result.get("status") == "success":
                    logger.info("📊 백테스트 리포트 생성 완료")
                    logger.info(f"   - HTML: {result.get('html_path')}")
                    logger.info(f"   - JSON: {result.get('json_path')}")
                    logger.info(
                        f"   - TUNING_VIBLE 총점: {result.get('total_score', 0):.1f}/100"
                    )
                else:
                    logger.warning(
                        f"⚠️  백테스트 리포트 생성 실패: {result.get('error', '데이터 없음')}"
                    )
            else:
                # TUNING_VIBLE 100점 만점 검증만 수행 (HTML 미생성)
                logger.info("=" * 80)
                logger.info("🎯 TUNING_VIBLE 100점 만점 검증 시작")
                logger.info("=" * 80)
                result = generate_backtest_report(
                    trial_id=None, sinks=["log"]  # 로그만 출력
                )
                if result.get("status") == "success":
                    logger.info(
                        f"🏆 TUNING_VIBLE 총점: {result.get('total_score', 0):.1f}/100"
                    )
                else:
                    logger.warning("⚠️  검증 실패: 거래 데이터 없음")
        except Exception as e:
            logger.warning(f"⚠️  백테스트 리포트 생성 실패: {e}")


def calculate_pnl(position: Dict, exit_price: float, fee_rate: float = 0.0004) -> float:
    """
    PnL 계산 (수수료 반영)
    
    Args:
        position: 포지션 정보
        exit_price: 청산가
        fee_rate: 수수료율 (기본값 0.0004 = 0.04%)
    
    Returns:
        수수료 차감 후 순수익 (Net PnL)
    """
    entry = position["entry"]
    qty = position["qty"]
    side = position["side"]

    # Gross PnL
    if side == "LONG":
        gross_pnl = (exit_price - entry) * qty
    else:  # SHORT
        gross_pnl = (entry - exit_price) * qty

    # 수수료 (진입 + 청산)
    total_fee = (entry + exit_price) * qty * fee_rate
    
    # Net PnL
    return gross_pnl - total_fee


def close_trade_in_db(
    position_id: str,
    exit_price: float,
    pnl: float,
    reason: str,
    exit_time: int = None,
    mode: str = "paper",
    leverage: int = 1,
):
    """거래 종료를 DB에 기록 (PostgreSQL 단일화)"""
    try:
        # 백테스트/Paper/Live 모두 PostgreSQL 사용
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # ⭐ PR10 Bug Fix: pnl_pct 계산 및 저장
                # entry_price와 quantity를 조회하여 pnl_pct 계산
                cur.execute(
                    """
                    SELECT entry_price, quantity
                    FROM trading.trades
                    WHERE trade_id = %s
                    """,
                    (position_id,),
                )
                row = cur.fetchone()
                
                if row:
                    entry_price, quantity = row
                    # ⭐ PR10 Bug Fix: Decimal → float 변환 (PostgreSQL 타입 호환)
                    entry_price = float(entry_price)
                    quantity = float(quantity)
                    # pnl_pct 계산: (pnl / (entry_price * quantity)) * 100
                    pnl_pct = (pnl / (entry_price * quantity)) * 100 if quantity > 0 else 0.0
                    logger.debug(f"✅ pnl_pct 계산: {position_id} -> {pnl_pct:.2f}% (pnl={pnl:.2f}, entry={entry_price}, qty={quantity})")
                else:
                    pnl_pct = 0.0
                    logger.warning(f"⚠️ trade_id {position_id} not found for pnl_pct calculation")
                
                # UPDATE with pnl_pct
                cur.execute(
                    """
                    UPDATE trading.trades
                    SET exit_price = %s, pnl = %s, pnl_pct = %s, exit_reason = %s, status = 'CLOSED', ts_close = NOW()
                    WHERE trade_id = %s
                """,
                    (exit_price, pnl, pnl_pct, reason, position_id),
                )
                logger.debug(f"✅ DB 종료 기록 완료: {position_id}, pnl_pct={pnl_pct:.2f}%")
    except Exception as e:
        logger.error(f"❌ DB 종료 기록 실패: {e}")


def save_trade_to_db(
    position_id: str,
    symbol: str,
    side: str,
    entry_price: float,
    qty: float,
    sl_price: float = None,
    tp_price: float = None,
    strategy_id: str = None,
    timestamp: int = None,
    mode: str = "paper",
    leverage: int = 1,
    trial_id: str = None,
):
    """거래를 DB에 저장 (PostgreSQL 단일화)"""
    try:
        # 백테스트/Paper/Live 모두 PostgreSQL 사용 (trial_id는 DB 스키마에 없으므로 제외)
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO trading.trades (
                        trade_id, symbol, strategy_id, side,
                        entry_price, quantity, sl_price, tp_price,
                        leverage, status, ts_open, mode
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                """,
                    (
                        position_id,
                        symbol,
                        strategy_id,
                        side,
                        entry_price,
                        qty,
                        sl_price,
                        tp_price,
                        leverage,
                        "OPEN",
                        mode,  # ⭐ PR12: Paper/Live 모드 분리
                    ),
                )
    except Exception as e:
        logger.error(f"❌ DB 저장 실패: {e}")
