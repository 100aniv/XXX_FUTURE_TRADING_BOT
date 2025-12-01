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
from common.namespace import build_redis_key  # PHASE18-2: run_id 네임스페이스
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
from common.database import get_db_connection  # ⭐ PHASE16+: Paper 모드에서 DB 저장 필요
from execution.position_sizer import PositionSizer
from execution.risk_manager import RiskManager, ExposureDecision  # ⭐ PHASE17
from signals.signal_generator import SignalGenerator
from execution.portfolio_manager import PortfolioManager
from execution.position_tracker import PositionTracker

logger = setup_logger(__name__, log_type="application")


def run_v2(mode: str, config: dict, clean_state: bool = False):
    """
    PHASE23-1: Single-Engine Entry Point
    =====================================
    엔진 중심 아키텍처의 새로운 진입점
    
    Args:
        mode: 실행 모드 ('paper', 'backtest', 'live')
        config: 전체 설정 딕셔너리 (SSOT)
        clean_state: Redis/DB 상태 초기화 여부 (PAPER/LIVE only)
    
    Design:
        - Script는 config만 전달
        - Engine이 load_strategies() 호출
        - Engine이 use_ensemble 판단
        - Engine이 adapter 생성
        - Config params가 100% 전파됨 보장
    """
    logger.info("=" * 80)
    logger.info(f"🚀 [PHASE23-1] Engine V2 시작 - Mode: {mode.upper()}")
    logger.info("=" * 80)
    
    # 1. Config Validation
    required_keys = ['timeframe', 'lookback', 'equity', 'risk', 'strategy']
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise ValueError(f"❌ Config 필수 키 누락: {missing}")
    
    symbol = config.get('symbol', 'BTCUSDT')
    timeframe = config['timeframe']
    logger.info(f"📊 Symbol: {symbol}, Timeframe: {timeframe}")
    
    # 2. Strategy 로딩 (Engine이 직접 호출 - PHASE23-1 핵심)
    logger.info("🎯 [PHASE23-1] Engine에서 load_strategies() 직접 호출")
    from strategies import load_strategies
    
    strategies = load_strategies(config=config)
    if not strategies:
        raise ValueError("❌ 로딩된 전략 없음")
    
    logger.info(f"✅ 전략 로딩 완료: {list(strategies.keys())}")
    
    # PHASE23-1 DEBUG: Params 전파 확인
    for strategy_name, strategy_info in strategies.items():
        params = strategy_info.get('params', {})
        logger.info(f"🔍 [PHASE23-1 DEBUG] {strategy_name} params: {params}")
    
    # 3. Ensemble 모듈 로딩
    ensemble_module = None
    use_ensemble = config.get('strategy', {}).get('use_ensemble', False)
    
    if use_ensemble:
        logger.info("🎯 [PHASE23-1] Ensemble 모드 활성화")
        try:
            from strategies import ensemble
            ensemble_module = ensemble
            logger.info("✅ Ensemble 모듈 로딩 완료")
        except Exception as e:
            logger.warning(f"⚠️  Ensemble 모듈 로딩 실패, 단일 전략 모드로 전환: {e}")
            ensemble_module = None
    else:
        logger.info("ℹ️  단일 전략 모드")
    
    # 4. Mode-based Adapter 생성
    logger.info(f"🔧 [PHASE23-1] {mode.upper()} 모드 Adapters 생성")
    
    if mode == 'paper':
        adapters = _create_paper_adapters(config, clean_state)
    elif mode == 'backtest':
        adapters = _create_backtest_adapters(config)
    elif mode == 'live':
        adapters = _create_live_adapters(config, clean_state)
    else:
        raise ValueError(f"❌ 지원하지 않는 모드: {mode}")
    
    logger.info(f"✅ Adapters 생성 완료")
    
    # 5. Duration 설정
    duration_hours = config.get('duration_hours')
    if duration_hours:
        config.setdefault('execution', {})['max_runtime_hours'] = duration_hours
        logger.info(f"⏱️  Duration: {duration_hours}h")
    
    # 6. 기존 run() 호출 (단일 엔진 원칙)
    logger.info("🚀 [PHASE23-1] Core engine.run() 호출")
    
    try:
        run(
            feed=adapters['feed'],
            broker=adapters['broker'],
            clock=adapters['clock'],
            strategies=strategies,
            ensemble_module=ensemble_module,
            config=config
        )
        logger.info("✅ [PHASE23-1] Engine V2 정상 종료")
        
    finally:
        # 7. Cleanup
        if hasattr(adapters['feed'], 'stop'):
            adapters['feed'].stop()
            logger.info("✅ Feed 정리 완료")


def _create_paper_adapters(config: dict, clean_state: bool) -> dict:
    """PAPER 모드 adapters 생성"""
    from execution.adapters import create_adapters
    
    symbol = config.get('symbol', 'BTCUSDT')
    
    # execution.adapters.create_adapters 호출
    feed, broker, clock = create_adapters(
        mode='paper',
        symbols=[symbol],
        config=config,
        logger=logger
    )
    
    # Clean state (if requested)
    if clean_state and hasattr(broker, 'open_positions'):
        broker.open_positions.clear()
        logger.info("✅ Portfolio 상태 초기화")
    
    return {'feed': feed, 'broker': broker, 'clock': clock}


def _create_backtest_adapters(config: dict) -> dict:
    """BACKTEST 모드 adapters 생성"""
    from execution.adapters import create_adapters
    
    symbol = config.get('symbol', 'BTCUSDT')
    
    # execution.adapters.create_adapters 호출
    feed, broker, clock = create_adapters(
        mode='backtest',
        symbols=[symbol],
        config=config,
        logger=logger
    )
    
    return {'feed': feed, 'broker': broker, 'clock': clock}


def _create_live_adapters(config: dict, clean_state: bool) -> dict:
    """LIVE 모드 adapters 생성"""
    # TODO: LIVE 구현은 PHASE32에서
    raise NotImplementedError("LIVE 모드는 PHASE32에서 구현 예정")


def _convert_ensemble_decision_to_signal(ensemble_decision) -> dict:
    """
    PHASE19-3+: EnsembleDecision (V1)을 기존 엔진이 사용하는 signal dict로 변환
    """
    if ensemble_decision.tier == 'tier1' and ensemble_decision.chosen_strategy:
        chosen = next((d for d in ensemble_decision.decisions if d.name == ensemble_decision.chosen_strategy), None)
        if chosen and chosen.raw_signal:
            signal = chosen.raw_signal.copy() if isinstance(chosen.raw_signal, dict) else {}
            signal['ensemble_tier'] = 'tier1'
            signal['ensemble_confidence'] = ensemble_decision.confidence
            signal['ensemble_reason'] = ensemble_decision.reason
            signal['strategy_id'] = ensemble_decision.chosen_strategy
            return signal
    elif ensemble_decision.tier == 'tier2':
        if ensemble_decision.contributing_strategies:
            first_contrib = ensemble_decision.contributing_strategies[0]
            chosen = next((d for d in ensemble_decision.decisions if d.name == first_contrib), None)
            if chosen and chosen.raw_signal:
                signal = chosen.raw_signal.copy() if isinstance(chosen.raw_signal, dict) else {}
                signal['ensemble_tier'] = 'tier2'
                signal['ensemble_confidence'] = ensemble_decision.confidence
                signal['ensemble_reason'] = ensemble_decision.reason
                signal['ensemble_contributors'] = ', '.join(ensemble_decision.contributing_strategies)
                signal['strategy_id'] = first_contrib
                return signal
    return {'side': None}


def _convert_ensemble_decision_v2_to_signal(ensemble_decision_v2) -> dict:
    """
    PHASE23-3: EnsembleDecisionV2를 기존 엔진이 사용하는 signal dict로 변환
    
    Args:
        ensemble_decision_v2: EnsembleDecisionV2 인스턴스
    
    Returns:
        signal dict: {'side', 'action', 'entry', 'sl', 'tp', 'ensemble_*', ...}
    """
    if not ensemble_decision_v2.side:
        return {'side': None}
    
    # Base signal from EnsembleDecisionV2
    signal = {
        'side': ensemble_decision_v2.side,
        'action': ensemble_decision_v2.action,
        'entry': ensemble_decision_v2.entry,
        'sl': ensemble_decision_v2.sl,
        'tp': ensemble_decision_v2.tp,
        'reason': ensemble_decision_v2.reason,
        # Ensemble V2 meta
        'ensemble_tier': ensemble_decision_v2.tier,
        'ensemble_confidence': ensemble_decision_v2.confidence,
        'ensemble_reason': '; '.join(ensemble_decision_v2.reason),
        'ensemble_strategy_votes': ensemble_decision_v2.strategy_votes,
        'ensemble_agg_S_NET': ensemble_decision_v2.agg_S_NET,
        'ensemble_agg_S_RISK': ensemble_decision_v2.agg_S_RISK,
        'ensemble_agg_S_QUALITY': ensemble_decision_v2.agg_S_QUALITY,
    }
    
    # Add strategy_id (best contributor)
    if ensemble_decision_v2.strategy_votes:
        best_strategy = max(
            ensemble_decision_v2.strategy_votes.items(),
            key=lambda x: abs(x[1])
        )[0]
        signal['strategy_id'] = best_strategy
    
    return signal


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
    
    # ⭐ PHASE18-2: run_id & env 추출 (네임스페이스 격리)
    run_id = config.get("run_id", "unknown")
    env = config.get("env", "paper")  # backtest, paper, live
    logger.info(f"🆔 [PHASE18-2] Run ID: {run_id}, Env: {env}")

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
    # ⭐ PHASE8-2b: backtest 모드에서는 Redis 비활성화 (완전 격리)
    redis_config = config.get("monitoring", {}).get("redis", {})
    redis_client = None
    
    if mode in ['backtest', 'backtest_clean']:
        logger.info("🔒 [BACKTEST] Redis dedup 비활성화 (완전 격리)")
        redis_client = None
    else:
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
    # ⭐ PHASE8-2b: backtest 모드에서는 기존 포지션 로드 스킵
    sizer = PositionSizer(config)
    
    # ⭐ PHASE9-1 ROOT CAUSE FIX: backtest_raw 포함
    # ⭐ PHASE16+: paper 테스트 모드도 깨끗한 시작 (load_existing=False)
    is_backtest_mode = mode in ['backtest', 'backtest_clean', 'backtest_raw']
    is_paper_test_mode = mode == 'paper' and config.get('paper', {}).get('clean_start', True)
    load_existing = not (is_backtest_mode or is_paper_test_mode)
    
    if is_paper_test_mode:
        logger.info("🔄 [PAPER TEST] 깨끗한 시작: 기존 포지션 로드 스킵")
    
    portfolio = PortfolioManager(config, load_existing=load_existing)
    
    risk = RiskManager(config, portfolio=portfolio)  # ⭐ PR12: 포트폴리오 참조 추가
    tracker = PositionTracker(config)  # ⭐ TUNING_VIBLE TP 분할 지원

    # ⭐⭐⭐ SignalGenerator 초기화: config.merge_strategy_config 사용 ⭐⭐⭐
    from common.config_loader import merge_strategy_config

    # PHASE19-3+ / PHASE23-3: Ensemble 옵션 확인 및 초기화
    use_ensemble = config.get("ensemble", {}).get("enabled", False) or config.get("strategy", {}).get("use_ensemble", False)
    ensemble_mode = config.get("ensemble", {}).get("mode", "factor")  # PHASE23-3: 'score_v2' | 'factor' | 'hybrid'
    ensemble_registry = None
    ensemble_score_engine = None
    ensemble_aggregator = None
    ensemble_score_engine_v2 = None  # PHASE23-3
    ensemble_aggregator_v2 = None    # PHASE23-3

    if not use_ensemble:
        # 단일 전략: config.merge_strategy_config로 병합 (lookback 포함)
        strategy_selector = config.get("strategy", {}).get("selector", "scalping")
        signal_gen_config = merge_strategy_config(config, strategy_selector)

        logger.info(
            f"✅ [CONFIG] Strategy merged | strategy={strategy_selector} | lookback={signal_gen_config['lookback']} | timeframe={signal_gen_config['timeframe']}"
        )
        min_bars_required = signal_gen_config.get("min_bars_for_signal", 50)
    else:
        # 앙상블 모드: Ensemble 컴포넌트 초기화 (PHASE19-3+ / PHASE23-3)
        signal_gen_config = config
        ensemble_strategies = config.get("ensemble", {}).get("strategies", ["scalping"])
        ensemble_cfg = config.get("ensemble", {})
        
        try:
            # PHASE23-3: Score V2 모드 지원
            if ensemble_mode == 'score_v2':
                logger.info(f"🎯 [PHASE23-3] Ensemble V2 초기화 (mode={ensemble_mode})")
                from common.ensemble import ScoreEngineV2, EnsembleAggregatorV2
                
                ensemble_score_engine_v2 = ScoreEngineV2()
                ensemble_aggregator_v2 = EnsembleAggregatorV2(
                    score_engine=ensemble_score_engine_v2,
                    config=config
                )
                
                logger.info(
                    f"✅ [ENSEMBLE V2] Aggregator V2 초기화 완료 | "
                    f"strategies={ensemble_strategies} | "
                    f"high_conf={ensemble_cfg.get('high_conf_threshold', 0.7)} | "
                    f"consensus={ensemble_cfg.get('consensus_threshold', 0.4)}"
                )
            else:
                # PHASE19-3: Factor-based 기존 모드
                logger.info(f"🎯 [PHASE19] Ensemble V1 초기화 (mode={ensemble_mode})")
                from common.registry import StrategyRegistry
                from common.ensemble import ScoreEngine, EnsembleAggregator
                
                ensemble_registry = StrategyRegistry()
                ensemble_registry.scan()
                
                ensemble_score_engine = ScoreEngine()
                ensemble_aggregator = EnsembleAggregator(
                    registry=ensemble_registry,
                    score_engine=ensemble_score_engine,
                    min_tier1_score=ensemble_cfg.get("min_tier1_score", 0.8),
                    min_tier2_score=ensemble_cfg.get("min_tier2_score", 0.5),
                    tier1_conflict_diff=ensemble_cfg.get("tier1_conflict_diff", 0.15),
                    min_tier2_votes=ensemble_cfg.get("min_tier2_votes", 2),
                )
                
                logger.info(f"✅ [ENSEMBLE] Aggregator 초기화 완료 | strategies={ensemble_strategies}")
                logger.info(f"✅ [ENSEMBLE] Registry: {len(ensemble_registry._registry)}개 전략 스캔 완료")
        except Exception as e:
            logger.error(f"❌ [ENSEMBLE] 초기화 실패: {e}")
            raise RuntimeError(f"Ensemble 초기화 실패: {e}")
        
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

                        # TP 레벨 재생성
                        for pos_id, position in active_positions.items():
                            tp_levels = tracker.tp_manager.calculate_tp_levels(
                                entry=position["entry"],
                                stop=position["sl"],
                                side=position["side"],
                            )
                            position["tp_levels"] = tp_levels

                        logger.info("✅ TP 레벨 재생성 완료")
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
                    logger.info(f"✅ [LIVE] {len(active_positions)}개 실제 포지션을 시스템에 동기화")
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

    # ⭐ PHASE16+: Wall-clock Duration 모드 초기화
    # PHASE22-1-FIX: Duration 로직 명확화 및 검증 강화
    # PHASE22-2-HOTFIX: Duration 로그 간격 추적 변수 추가
    import time
    duration_mode = config.get('paper', {}).get('duration_mode', 'market_time')
    duration_hours = config.get('paper', {}).get('duration_hours', 1)
    start_wall_time = time.time()
    duration_seconds = duration_hours * 3600
    last_logged_interval = -1  # Duration 로그 출력 추적
    
    # Duration 설정 검증
    if duration_hours <= 0:
        logger.warning(f"⚠️ Duration 설정 이상: {duration_hours}h → 무제한 실행 모드")
        duration_mode = 'unlimited'
    
    if duration_mode == 'wall_clock':
        logger.info(f"⏱️  [WALL-CLOCK] Duration 모드 시작: {duration_hours:.2f}시간 ({duration_seconds:.0f}초)")
        logger.info(f"⏱️  [WALL-CLOCK] 시작 시각: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_wall_time))}")
        estimated_end = start_wall_time + duration_seconds
        logger.info(f"⏱️  [WALL-CLOCK] 종료 예정: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(estimated_end))}")
    else:
        logger.info(f"⏱️  [MARKET-TIME] Duration 모드 시작: {duration_hours:.2f}시간")

    # ⭐ PHASE18-3: Runtime Context 추출 (Graceful Shutdown)
    runtime_ctx = config.get('runtime_context', None)
    
    # ⭐ 메인 루프
    for candle in feed.stream():
        # ⭐ PHASE18-3: Shutdown 체크 (최우선)
        if runtime_ctx and runtime_ctx.is_shutdown_requested():
            reason = runtime_ctx.get_shutdown_reason()
            logger.info(f"🛑 Shutdown requested ({reason}) - 메인 루프 종료")
            break
        
        # ⭐ PHASE18-4: Heartbeat 업데이트
        if runtime_ctx and runtime_ctx.monitor_registry:
            heartbeat = runtime_ctx.monitor_registry.get('heartbeat')
            if heartbeat:
                heartbeat.update('engine')
        
        # ⭐ PHASE16+: Wall-clock Duration 체크 (루프 시작 시 먼저 확인)
        # PHASE22-1-FIX: Duration 종료 로그 명확화
        # PHASE22-2-FIX: Duration 체크 디버그 로그 추가
        # PHASE22-2-HOTFIX: Duration 로그 과다 출력 수정 (30초 구간 변경 시에만 출력)
        if duration_mode == 'wall_clock':
            elapsed_wall = time.time() - start_wall_time
            # DEBUG: 30초 구간이 바뀔 때만 경과 시간 출력
            elapsed_interval = int(elapsed_wall) // 30
            if elapsed_interval > last_logged_interval and elapsed_wall > 0:
                logger.info(f"⏱️  [WALL-CLOCK] 경과: {elapsed_wall:.0f}s / {duration_seconds:.0f}s ({elapsed_wall/duration_seconds*100:.1f}%)")
                last_logged_interval = elapsed_interval
            if elapsed_wall >= duration_seconds:
                logger.info(f"⏱️  [WALL-CLOCK] Duration 종료 조건 도달!")
                logger.info(f"    - 설정: {duration_hours:.2f}시간 ({duration_seconds:.0f}초)")
                logger.info(f"    - 경과: {elapsed_wall:.1f}초 ({elapsed_wall/60:.1f}분)")
                logger.info(f"    - 초과: {elapsed_wall - duration_seconds:.1f}초)")
                logger.info(f"✅ [WALL-CLOCK] 엔진 정상 종료 (Duration 만료)")
                break
        
        # ⭐ PHASE22-1-FIX: Feed timeout 시 None이 올 수 있음 (duration 체크용)
        if candle is None:
            continue
        
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

        # 활성 포지션 체크 (TP/SL + Trailing) - ⭐ 같은 심볼만 체크
        positions_to_close = []
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
            should_action, partial_qty, reason = tracker.check_tpsl_with_partial(
                position, current_price, atr, candle=candle
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
                    positions_to_close.append((pos_id, position, reason))

        # 포지션 종료 처리
        drawdown_guard_triggered = False  # 플래그 추가
        fee_rate = config.get('fees', {}).get('taker', 0.0004)
        for pos_id, position, reason in positions_to_close:
            pnl = calculate_pnl(position, current_price, fee_rate)
            
            # ⭐ PHASE10: Broker에 청산 기록 저장 (Scorecard 연동)
            # ⭐ PHASE16+: Broker 타입에 따라 다른 시그니처 사용
            if hasattr(broker, 'close_position'):
                broker_type = type(broker).__name__
                if broker_type in ['PaperBroker', 'LiveBroker']:
                    # PaperBroker/LiveBroker: position_id, symbol, side, qty, reason
                    broker.close_position(
                        position_id=pos_id,
                        symbol=position['symbol'],
                        side=position['side'],
                        qty=position['qty'],
                        reason=reason
                    )
                else:
                    # SimBroker: position, exit_price, exit_reason, candle_ts
                    broker.close_position(
                        position=position,
                        exit_price=current_price,
                        exit_reason=reason,
                        candle_ts=ts
                    )
            
            close_trade_in_db(
                pos_id,
                current_price,
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

        # ⭐⭐⭐ PHASE19-3+: Ensemble vs 단일 전략 모드 분기 ⭐⭐⭐
        signals = []

        # ========== ENSEMBLE 모드 (PHASE19-3+ / PHASE23-3) ==========
        if use_ensemble and (ensemble_aggregator is not None or ensemble_aggregator_v2 is not None):
            try:
                ensemble_strategies = config.get("ensemble", {}).get("strategies", ["scalping"])
                
                # 지표 계산된 DataFrame 준비
                df_with_indicators = df.copy()
                if "ema_fast" not in df_with_indicators.columns:
                    df_with_indicators = add_indicators(
                        df_with_indicators,
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
                
                # PHASE23-3: V2 모드 처리
                if ensemble_mode == 'score_v2' and ensemble_aggregator_v2 is not None:
                    logger.info(f"🔔 [ENSEMBLE V2] 전략 평가 시작: {ensemble_strategies}")
                    
                    # 1) 각 전략에서 signal 생성 (compute_signal 호출)
                    from common.ensemble import StrategyDecisionV2
                    decisions_v2 = []
                    
                    for strategy_name in ensemble_strategies:
                        strategy_info = strategies.get(strategy_name)
                        if not strategy_info or not strategy_info.get('enabled', True):
                            continue
                        
                        try:
                            # Get BaseStrategy instance
                            strategy_instance = strategy_info.get('instance')
                            if not strategy_instance:
                                logger.warning(f"⚠️  [ENSEMBLE V2] {strategy_name}: instance 없음")
                                continue
                            
                            # Compute signal
                            raw_signal = strategy_instance.compute_signal(df_with_indicators)
                            
                            if not raw_signal or not raw_signal.get('side'):
                                logger.info(f"⏸ [ENSEMBLE V2] {strategy_name}: 신호 없음 (side={raw_signal.get('side') if raw_signal else None})")
                                continue
                            
                            # Compute Score V2
                            score_v2 = ensemble_score_engine_v2.compute_strategy_score_v2(
                                signal=raw_signal,
                                metadata=strategy_instance.metadata,
                                mode='score_v2'
                            )
                            
                            # Get strategy weight
                            strategy_weights = config.get('ensemble', {}).get('strategy_weights', {})
                            weight = strategy_weights.get(strategy_name, 1.0)
                            
                            # Create StrategyDecisionV2
                            decision_v2 = StrategyDecisionV2(
                                name=strategy_name,
                                score_v2=score_v2,
                                raw_signal=raw_signal,
                                metadata=strategy_instance.metadata,
                                weight=weight
                            )
                            decisions_v2.append(decision_v2)
                            
                            logger.info(
                                f"📊 [ENSEMBLE V2] {strategy_name}: "
                                f"side={raw_signal.get('side')}, S_NET={score_v2.S_NET:.3f}, S_DIR={score_v2.S_DIR}, "
                                f"S_RISK={score_v2.S_RISK:.3f}, S_QUALITY={score_v2.S_QUALITY:.3f}"
                            )
                        
                        except Exception as e:
                            logger.warning(f"⚠️  [ENSEMBLE V2] {strategy_name} 평가 실패: {e}")
                            continue
                    
                    # 2) Aggregate decisions
                    ensemble_decision_v2 = ensemble_aggregator_v2.aggregate_v2(
                        decisions_v2=decisions_v2,
                        regime=None
                    )
                    
                    logger.info(
                        f"🎯 [ENSEMBLE V2] Aggregate 결과: "
                        f"tier={ensemble_decision_v2.tier}, side={ensemble_decision_v2.side}, "
                        f"reason={ensemble_decision_v2.reason}, strategies={len(decisions_v2)}"
                    )
                    
                    # 3) Convert to signal dict
                    if ensemble_decision_v2.side:
                        signal = _convert_ensemble_decision_v2_to_signal(ensemble_decision_v2)
                        signal["ts"] = ts
                        signal["symbol"] = candle_symbol
                        signal["timeframe"] = timeframe
                        
                        # 신호 검증 (MTF, 쿨다운, 거래량 필터)
                        if signal_gen.validate_signal(candle_symbol, signal, df_with_indicators):
                            signals.append(signal)
                            logger.info(
                                f"✅ [ENSEMBLE V2] {ensemble_decision_v2.tier.upper()} | "
                                f"{ensemble_decision_v2.side} (conf={ensemble_decision_v2.confidence:.2f}) | "
                                f"S_NET={ensemble_decision_v2.agg_S_NET:.3f} | "
                                f"{ensemble_decision_v2.reason[0] if ensemble_decision_v2.reason else 'no_reason'}"
                            )
                        else:
                            logger.debug(f"⏸ [ENSEMBLE V2] 신호 검증 실패")
                    else:
                        logger.debug(
                            f"⏸ [ENSEMBLE V2] NO TRADE: {ensemble_decision_v2.reason[0] if ensemble_decision_v2.reason else 'unknown'}"
                        )
                
                # PHASE19-3: V1 모드 처리 (기존 로직)
                elif ensemble_aggregator is not None:
                    logger.debug(f"🔔 [ENSEMBLE] 전략 평가 시작: {ensemble_strategies}")
                    ensemble_decision = ensemble_aggregator.decide(
                        strategy_names=ensemble_strategies,
                        df=df_with_indicators,
                        regime=None
                    )
                    
                    # EnsembleDecision → signal dict 변환
                    if ensemble_decision.side:
                        signal = _convert_ensemble_decision_to_signal(ensemble_decision)
                        signal["ts"] = ts
                        signal["symbol"] = candle_symbol
                        signal["timeframe"] = timeframe
                        
                        # 신호 검증 (MTF, 쿨다운, 거래량 필터)
                        if signal_gen.validate_signal(candle_symbol, signal, df_with_indicators):
                            signals.append(signal)
                            logger.info(
                                f"✅ [ENSEMBLE] {ensemble_decision.tier.upper()} | "
                                f"{ensemble_decision.side} (conf={ensemble_decision.confidence:.2f}) | "
                                f"{ensemble_decision.reason}"
                            )
                        else:
                            logger.debug(f"⏸ [ENSEMBLE] 신호 검증 실패")
                    else:
                        logger.debug(f"⏸ [ENSEMBLE] NO TRADE: {ensemble_decision.reason}")
                    
            except Exception as e:
                logger.error(f"❌ [ENSEMBLE] Aggregator 오류: {e}", exc_info=True)
        
        # ========== 단일 전략 모드 (기존 로직) ==========
        else:
            strategy_selector = config.get("strategy", {}).get("selector", "scalping")
            selected_strategies = {strategy_selector: strategies.get(strategy_selector)}

            for strategy_id, strategy_info in selected_strategies.items():
                # PHASE22-4: strategy_info는 {"module": ..., "params": ..., "enabled": ...} dict
                if not isinstance(strategy_info, dict) or not strategy_info.get("enabled", True):
                    continue
                
                try:
                    # PHASE22-4: module과 params 추출
                    strategy_module = strategy_info["module"]
                    strategy_params = strategy_info.get("params", {})
                    
                    # PHASE22-4 DEBUG: params 확인
                    logger.info(f"🔍 [PHASE22-4 DEBUG] {strategy_id} params: {strategy_params}")
                    
                    # ⭐ 전략별 설정 + 전체 config 병합 (PHASE22-4: params 우선순위)
                    strategy_cfg = config.get("strategies", {}).get(strategy_id, {})
                    cfg = {
                        **config,  # 전체 config (leverage, tp_sl 등)
                        **strategy_params,  # PHASE22-4: 전략별 params (rsi_oversold 등) - 최우선
                    }
                    
                    # PHASE22-4 DEBUG: 병합된 cfg의 RSI 값 확인
                    logger.info(f"🔍 [PHASE22-4 DEBUG] {strategy_id} cfg rsi_oversold={cfg.get('rsi_oversold', 'MISSING')}, rsi_overbought={cfg.get('rsi_overbought', 'MISSING')}")

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
                        signal["df"] = df_tf  # ⭐ PHASE22-3: Ensemble에 df 전달
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

        # Risk 체크 (메서드 체크)
        if hasattr(risk, "allow_entry") and not risk.allow_entry(
            candle_symbol, decision.get("side")
        ):
            logger.warning(f"⛔ [{candle_symbol}] Risk 거부: {decision.get('side')}")
            continue  # ⭐ PHASE9-1 FIX: 진입 거부 시 신호 스킵

        # ⭐ PHASE17: 포지션 사이즈 계산 + Multi-position Scaling
        # 1. 전략별 남은 예산 조회 (PHASE17 Budget SSOT)
        strategy_id = decision.get("strategy_id", "ensemble")
        available_budget = portfolio.get_available_budget(strategy_id)
        
        # 2. 기본 포지션 크기 계산 (Budget 전달)
        qty, meta = sizer.calculate(
            {
                "entry_price": decision.get("entry"),
                "sl_price": decision.get("sl"),
                "confidence": decision.get("confidence", 0.8),
            },
            available_budget=available_budget
        )
        
        # 3. Budget Cap 적용 로그
        if meta.get('budget_capped'):
            logger.info(
                f"💰 [Budget Cap Applied] {candle_symbol} {decision.get('side')} "
                f"strategy={strategy_id} position_value=${meta['position_value']:.2f} "
                f"available_budget=${available_budget:.2f}"
            )

        if qty <= 0:
            logger.warning(f"❌ [ENTRY BLOCK] symbol={candle_symbol} side={decision.get('side')} reason=position_size_zero qty={qty}")
            continue

        # 2. Multi-position Scaling 적용 (PHASE17)
        num_open_positions = len(active_positions)
        max_positions = config.get('risk', {}).get('max_positions', 20)
        base_risk_usdt = meta.get('risk_usdt', 0)
        
        # ⭐ PHASE17 V6 FIX: Budget Cap을 보존하기 위해 position_value 먼저 저장
        base_position_value = meta.get('position_value', qty * decision.get("entry"))
        
        if base_risk_usdt > 0:
            scaled_risk_usdt = sizer.apply_multi_position_scaling(
                base_risk=base_risk_usdt,
                num_open_positions=num_open_positions,
                max_positions=max_positions
            )
            # 리스크 조정 비율을 수량에 반영
            risk_ratio = scaled_risk_usdt / base_risk_usdt
            qty = qty * risk_ratio
            logger.debug(f"📊 Multi-position Scaling: {num_open_positions}개 열림, qty {meta.get('qty', 0):.4f} → {qty:.4f}")
        
        # ⭐ PHASE17 V6 FIX: position_value 계산 (Multi-position Scaling 반영)
        # Multi-position Scaling이 qty를 조정했으므로 항상 재계산 필요
        position_value = qty * decision.get("entry")
        
        # Budget Cap이 적용된 경우에도 Multi-position Scaling으로 더 줄어들 수 있음
        if meta.get('budget_capped'):
            logger.info(
                f"💰 [Budget Cap Applied] Original budget=${available_budget:.2f}, "
                f"After Multi-pos Scaling: position_value=${position_value:.2f}"
            )

        # ⭐ PHASE11-B: 엔트리 체크 시작 로그
        current_equity = portfolio.equity if hasattr(portfolio, 'equity') else 0
        open_positions = len(active_positions)
        logger.info(
            f"🔍 [ENTRY CHECK] symbol={candle_symbol} side={decision.get('side')} strategy={strategy_id} "
            f"price={current_price:.2f} qty={qty:.4f} position_value=${position_value:.2f} "
            f"equity=${current_equity:.2f} open_positions={open_positions}"
        )

        # ⭐ PR8/PR9: 전략별 심볼 거부 쿨다운 체크 (ensemble 모드 대응)
        cooldown_key = f"{candle_symbol}_{strategy_id}"

        # ⭐ PHASE11-C: 전략별 전용 쿨다운 (scalping 전략 우선)
        strategy_cfg = config.get("strategies", {}).get(strategy_id, {})
        strategy_cooldown = strategy_cfg.get(
            "entry_cooldown_seconds",
            config.get("execution", {}).get("reject_cooldown_seconds", 60),
        )
        
        # ⭐⭐⭐ PR9 Phase 2: Redis 쿨다운 TTL (재시작 후에도 유지)
        # ⭐ PHASE16+: 0초일 때는 쿨다운 체크 skip
        if strategy_cooldown > 0:
            if redis_client:
                # ⭐ PHASE18-2: run_id 네임스페이스 적용
                redis_cooldown_key = build_redis_key("cooldown", env, run_id, candle_symbol, strategy_id)
                try:
                    ttl = redis_client.ttl(redis_cooldown_key)
                    if ttl > 0:
                        logger.warning(
                            f"❌ [ENTRY BLOCK] symbol={candle_symbol} side={decision.get('side')} strategy={strategy_id} "
                            f"reason={strategy_id}_cooldown_active remaining_seconds={ttl}"
                        )
                        continue
                except Exception as e:
                    logger.warning(f"⚠️  Redis 쿨다운 체크 실패 (처리 계속): {e}")
            else:
                # Fallback: 로컬 메모리 쿨다운
                if cooldown_key in reject_cooldown:
                    elapsed = time.time() - reject_cooldown[cooldown_key]
                    if elapsed < strategy_cooldown:
                        remaining = int(strategy_cooldown - elapsed)
                        logger.warning(
                            f"❌ [ENTRY BLOCK] symbol={candle_symbol} side={decision.get('side')} strategy={strategy_id} "
                            f"reason={strategy_id}_cooldown_active remaining_seconds={remaining}"
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
                        f"❌ [ENTRY BLOCK] symbol={candle_symbol} side={decision.get('side')} strategy={strategy_id} "
                        f"reason=signal_idempotency candle_ts={normalized_ts} ttl={redis_ttl}s"
                    )
                    continue
                redis_client.setex(redis_signal_key, redis_ttl, "1")
                logger.debug(f"✅ 멱등 키 설정: {redis_signal_key} (TTL={redis_ttl}초)")
            except Exception as e:
                logger.warning(f"⚠️  Redis 멱등성 체크 실패 (처리 계속): {e}")

        # ⭐ PHASE17: Per-symbol Exposure Guard 3단계 의사결정 (먼저 체크)
        # 현재 심볼 노출도 계산
        current_symbol_exposure = sum(
            pos.get('position_value', pos['qty'] * pos['entry'])
            for pos in active_positions.values()
            if pos['symbol'] == candle_symbol
        )
        
        # Exposure Guard 체크
        exposure_decision = risk.check_symbol_exposure_with_adjustment(
            symbol=candle_symbol,
            requested_notional=position_value,
            current_exposure=current_symbol_exposure,
            min_position_notional=config.get('position_sizing', {}).get('min_position_notional', 100)
        )
        
        # BLOCK 처리
        if exposure_decision.decision == "BLOCK":
            if strategy_cooldown > 0:
                if redis_client:
                    try:
                        # ⭐ PHASE18-2: run_id 네임스페이스 적용
                        redis_cooldown_key = build_redis_key("cooldown", env, run_id, candle_symbol, strategy_id)
                        redis_client.setex(redis_cooldown_key, strategy_cooldown, "1")
                    except Exception as e:
                        logger.warning(f"⚠️  Redis 쿨다운 설정 실패: {e}")
                reject_cooldown[cooldown_key] = time.time()
            logger.warning(
                f"❌ [ENTRY BLOCK] symbol={candle_symbol} side={decision.get('side')} strategy={strategy_id} "
                f"reason=exposure_guard_block detail=\"{exposure_decision.reason}\" cooldown={strategy_cooldown}s"
            )
            if mode in ["paper", "live"]:
                tg(
                    f"⚠️ *Exposure Guard 차단* | 전략: {strategy_id} | 심볼: {candle_symbol} | 방향: {decision.get('side')} | 사유: {exposure_decision.reason}",
                    config,
                )
            continue
        
        # ALLOW_REDUCED 처리 (사이즈 축소)
        if exposure_decision.decision == "ALLOW_REDUCED":
            original_qty = qty
            original_value = position_value
            # 조정된 금액으로 수량 재계산
            qty = exposure_decision.adjusted_notional / decision.get("entry")
            position_value = exposure_decision.adjusted_notional
            logger.warning(
                f"⚠️  [ENTRY REDUCED] symbol={candle_symbol} side={decision.get('side')} strategy={strategy_id} "
                f"qty {original_qty:.4f} → {qty:.4f}, value ${original_value:.2f} → ${position_value:.2f} "
                f"reason=\"{exposure_decision.reason}\""
            )
        
        # Risk Manager 체크 (기존 로직: 일일 손실, Flash Guard 등)
        allowed, reason = risk.check_order(decision, qty, position_value=position_value)
        if not allowed:
            # ⭐ PR9 Phase 2: Redis 쿨다운 TTL 설정 (⭐ PHASE16+: 0초일 때는 skip)
            if strategy_cooldown > 0:
                if redis_client:
                    try:
                        # ⭐ PHASE18-2: run_id 네임스페이스 적용
                        redis_cooldown_key = build_redis_key("cooldown", env, run_id, candle_symbol, strategy_id)
                        redis_client.setex(redis_cooldown_key, strategy_cooldown, "1")
                    except Exception as e:
                        logger.warning(f"⚠️  Redis 쿨다운 설정 실패: {e}")
                reject_cooldown[cooldown_key] = time.time()  # Fallback
            logger.warning(
                f"❌ [ENTRY BLOCK] symbol={candle_symbol} side={decision.get('side')} strategy={strategy_id} "
                f"reason=risk_check_failed detail=\"{reason}\" cooldown={strategy_cooldown}s"
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
            # ⭐ PR9 Phase 2: Redis 쿨다운 TTL 설정 (⭐ PHASE16+: 0초일 때는 skip)
            if strategy_cooldown > 0:
                if redis_client:
                    try:
                        # ⭐ PHASE18-2: run_id 네임스페이스 적용
                        redis_cooldown_key = build_redis_key("cooldown", env, run_id, candle_symbol, strategy_id)
                        redis_client.setex(redis_cooldown_key, strategy_cooldown, "1")
                    except Exception as e:
                        logger.warning(f"⚠️  Redis 쿨다운 설정 실패: {e}")
                reject_cooldown[cooldown_key] = time.time()  # Fallback
            logger.warning(
                f"❌ [ENTRY BLOCK] symbol={candle_symbol} side={decision.get('side')} strategy={strategy_id} "
                f"reason=portfolio_check_failed detail=\"{portfolio_reason}\" cooldown={strategy_cooldown}s"
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
        
        # ⭐ PHASE9-3: 중복 진입 방지 (Config 제어)
        allow_dup = config.get('portfolio', {}).get('allow_duplicate_entry', False)
        dup_policy = config.get('portfolio', {}).get('duplicate_entry_policy', 'reject')
        max_dup = config.get('portfolio', {}).get('max_duplicate_entries', 1)
        
        same_direction_positions = [
            (pos_id, pos) for pos_id, pos in list(active_positions.items())
            if pos["symbol"] == candle_symbol and pos["side"] == new_side
        ]
        
        if same_direction_positions:
            current_dup_count = len(same_direction_positions)
            
            if not allow_dup or current_dup_count >= max_dup:
                logger.warning(
                    f"❌ [ENTRY BLOCK] symbol={candle_symbol} side={new_side} strategy={strategy_id} "
                    f"reason=duplicate_entry_prevented current_dup={current_dup_count} max_dup={max_dup} policy={dup_policy}"
                )
                continue  # 중복 진입 차단
            else:
                logger.info(f"✅ [중복 진입 허용] {candle_symbol} {new_side} 기존 포지션 {current_dup_count}개 (정책: {dup_policy}, 한도: {max_dup}개) - 진입 진행")
        
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
        fill = broker.execute(decision, qty)
        
        if not fill.get("success"):
            logger.error(f"❌ 거래 실행 실패: {candle_symbol}")
            continue
        
        # ⭐ PHASE11-B: 진입 성공 로그
        logger.info(
            f"✅ [ENTRY OPEN] symbol={candle_symbol} side={decision.get('side')} strategy={strategy_id} "
            f"qty={qty:.4f} entry=${fill.get('filled_price', 0):.2f} "
            f"sl=${decision.get('sl', 0):.2f} tp=${decision.get('tp', 0):.2f} "
            f"position_value=${position_value:.2f}"
        )
        
        # 포지션 ID 생성
        import uuid
        position_id = str(uuid.uuid4())
        entry_time = ts
        
        # DB 저장 (trial_id 포함)
        save_trade_to_db(
            position_id=position_id,
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

        # Risk Manager에도 등록 (⭐ candle_symbol 사용!)
        risk.add_position(candle_symbol, position_value)

        # ⭐ PR11: Slippage Guard 체크
        expected_price = decision.get("entry_price", decision.get("entry", 0))
        filled_price = fill.get("filled_price", 0)
        if expected_price > 0 and filled_price > 0:
            logger.info(f"🔍 Slippage Guard 체크: expected=${expected_price:.4f}, filled=${filled_price:.4f}")
            if not risk.check_slippage_guard(expected_price, filled_price):
                logger.error(f"🚨 Slippage Guard 차단 - 주문 취소: {candle_symbol}")
                continue  # 이 주문 스킵

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
        
        # ⭐ PHASE9-1 CRITICAL FIX: 진입 거래 카운트 증가
        trade_count += 1
        
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
                        trade_id, decision_id, symbol, side,
                        entry_price, exit_price, quantity, leverage,
                        sl_price, tp_price, ts_open, ts_close,
                        pnl, pnl_pct, fees, status,
                        strategy_id, exit_reason, created_at, trial_id, mode
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, NOW(), %s,
                        %s, %s, %s, %s,
                        %s, %s, NOW(), %s, %s
                    )
                """,
                    (
                        position_id,           # trade_id (NOT NULL)
                        None,                   # decision_id (nullable)
                        symbol,                 # symbol (NOT NULL)
                        side,                   # side (NOT NULL)
                        entry_price,            # entry_price (NOT NULL)
                        None,                   # exit_price (nullable, OPEN 상태이므로 NULL)
                        qty,                    # quantity (NOT NULL)
                        leverage,               # leverage (NOT NULL)
                        sl_price,               # sl_price (nullable)
                        tp_price,               # tp_price (nullable)
                        # ts_open: NOW() (NOT NULL)
                        None,                   # ts_close (nullable, OPEN 상태이므로 NULL)
                        0,                      # pnl (nullable, 시작 시 0)
                        0,                      # pnl_pct (nullable, 시작 시 0)
                        0,                      # fees (nullable, 기본값 0)
                        "OPEN",                 # status (NOT NULL)
                        strategy_id,            # strategy_id (NOT NULL)
                        None,                   # exit_reason (nullable, OPEN 상태이므로 NULL)
                        # created_at: NOW() (NOT NULL)
                        trial_id,               # trial_id (nullable)
                        mode,                   # mode (NOT NULL, default='paper')
                    ),
                )
                logger.info(f"✅ [DB] 거래 저장 성공: {position_id[:8]}... | {symbol} {side} @ {entry_price} | mode={mode}")
    except Exception as e:
        logger.error(f"❌ [DB] 거래 저장 실패: {e}")
        logger.error(f"   trade_id={position_id}, symbol={symbol}, side={side}, mode={mode}")
        import traceback
        logger.error(traceback.format_exc())
