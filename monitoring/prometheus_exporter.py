#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prometheus Metrics Exporter
============================
PHASE28-0: Monitoring & Observability Baseline

목적:
- 엔진/전략/리스크/포트폴리오 핵심 KPI를 Prometheus 지표로 노출
- 기존 TradeActivityTracker/MultiSymbolProfiler 재사용
- 최소 성능 오버헤드, Config 기반 활성화

사용법:
    # 초기화 (엔진 시작 시)
    exporter = PrometheusExporter(
        enabled=True,
        port=9091,
        mode="paper"
    )
    exporter.start()
    
    # 메트릭 기록 (엔진 루프/Tracker에서 호출)
    exporter.record_strategy_signal(symbol="BTCUSDT", strategy="baseline_v1", has_signal=True, side="LONG")
    exporter.record_loop_latency(symbol="BTCUSDT", latency_ms=12.5)
    exporter.record_trade(symbol="BTCUSDT", side="LONG")
    
    # 종료 (선택)
    exporter.stop()

Prometheus 규칙:
- 메트릭명: fab_<category>_<name>_<unit>
- 레이블: mode(backtest/paper/live), symbol, strategy, side, regime 등
"""
import time
import threading
from typing import Dict, Optional, Any
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    start_http_server,
    REGISTRY,
)
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


class PrometheusExporter:
    """
    Prometheus 메트릭 Exporter (PHASE28-0)
    
    카테고리:
    1. Engine Loop / System
    2. Trade / Execution
    3. Strategy / Ensemble
    4. Risk / Portfolio / Guard
    5. Infra / Error
    """
    
    def __init__(
        self,
        enabled: bool = True,
        port: int = 9091,
        mode: str = "paper"
    ):
        """
        Exporter 초기화
        
        Args:
            enabled: 모니터링 활성화 여부
            port: Prometheus HTTP 서버 포트
            mode: 실행 모드 (backtest/paper/live)
        """
        self.enabled = enabled
        self.port = port
        self.mode = mode
        self._http_server = None
        self._lock = threading.Lock()
        
        if not self.enabled:
            logger.info("📊 [PHASE28-0] Prometheus Exporter: DISABLED")
            return
        
        logger.info(f"📊 [PHASE28-0] Prometheus Exporter 초기화: port={port}, mode={mode}")
        
        # ============================================
        # 1. Engine Loop / System 메트릭
        # ============================================
        
        # Loop latency (Histogram for percentiles)
        self.loop_latency = Histogram(
            'fab_engine_loop_latency_seconds',
            'Engine loop latency per symbol',
            ['mode', 'symbol'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
        )
        
        # Candles processed
        self.candles_processed = Counter(
            'fab_candles_processed_total',
            'Total candles processed',
            ['mode', 'symbol']
        )
        
        # Engine info (상태 정보)
        self.engine_info = Info(
            'fab_engine',
            'Engine status and configuration'
        )
        self.engine_info.info({
            'mode': mode,
            'version': 'PHASE28-0'
        })
        
        # ============================================
        # 2. Trade / Execution 메트릭
        # ============================================
        
        # Trades (주문 체결)
        self.trades = Counter(
            'fab_trades_total',
            'Total trades executed',
            ['mode', 'symbol', 'side']
        )
        
        # Orders submitted (주문 제출)
        self.orders_submitted = Counter(
            'fab_orders_submitted_total',
            'Total orders submitted',
            ['mode', 'symbol']
        )
        
        # PnL (Gauge - 현재 값)
        self.pnl_total = Gauge(
            'fab_pnl_total',
            'Total PnL',
            ['mode', 'symbol']
        )
        
        # Open positions
        self.open_positions = Gauge(
            'fab_open_positions_total',
            'Current open positions',
            ['mode', 'symbol']
        )
        
        # ============================================
        # 3. Strategy / Ensemble 메트릭
        # ============================================
        
        # Strategy signals
        self.strategy_signals = Counter(
            'fab_strategy_signals_total',
            'Strategy signal calls',
            ['mode', 'symbol', 'strategy', 'has_signal']
        )
        
        # Strategy signals by side
        self.strategy_signals_by_side = Counter(
            'fab_strategy_signals_by_side_total',
            'Strategy signals by side',
            ['mode', 'symbol', 'strategy', 'side']
        )
        
        # Strategy signals by regime
        self.strategy_signals_by_regime = Counter(
            'fab_strategy_signals_by_regime_total',
            'Strategy signals by regime',
            ['mode', 'symbol', 'strategy', 'regime']
        )
        
        # Ensemble decisions
        self.ensemble_decisions = Counter(
            'fab_ensemble_decisions_total',
            'Ensemble aggregator decisions',
            ['mode', 'symbol', 'tier']
        )
        
        # ============================================
        # 4. Risk / Portfolio / Guard 메트릭
        # ============================================
        
        # Budget used ratio
        self.budget_used_ratio = Gauge(
            'fab_portfolio_budget_used_ratio',
            'Portfolio budget used ratio (0.0 ~ 1.0)',
            ['mode']
        )
        
        # Guard blocks
        self.guard_blocks = Counter(
            'fab_guard_blocks_total',
            'Guard/Risk blocks by reason',
            ['mode', 'symbol', 'reason']
        )
        
        # ============================================
        # 5. Infra / Error 메트릭
        # ============================================
        
        # Engine errors
        self.engine_errors = Counter(
            'fab_engine_errors_total',
            'Engine errors by level',
            ['mode', 'level']
        )
        
        # CPU usage
        self.cpu_usage = Gauge(
            'fab_cpu_usage_percent',
            'CPU usage percentage',
            ['mode']
        )
        
        # Memory usage
        self.memory_usage = Gauge(
            'fab_memory_usage_mb',
            'Memory usage in MB',
            ['mode']
        )
        
        logger.info("✅ [PHASE28-0] Prometheus 메트릭 등록 완료")
    
    def start(self):
        """
        Prometheus HTTP 서버 시작 (/metrics 엔드포인트 노출)
        """
        if not self.enabled:
            return
        
        try:
            start_http_server(self.port)
            logger.info(f"🚀 [PHASE28-0] Prometheus HTTP 서버 시작: http://localhost:{self.port}/metrics")
        except OSError as e:
            logger.warning(f"⚠️  [PHASE28-0] Prometheus HTTP 서버 시작 실패 (포트 {self.port} 사용 중?): {e}")
            logger.warning(f"⚠️  [PHASE28-0] 메트릭 수집은 계속되지만 HTTP 노출은 불가")
    
    def stop(self):
        """
        Exporter 종료 (선택적)
        
        Note: prometheus_client는 명시적 stop이 없음 (프로세스 종료 시 자동)
        """
        if not self.enabled:
            return
        
        logger.info("🛑 [PHASE28-0] Prometheus Exporter 종료")
    
    # ============================================
    # Record API: 엔진/Tracker에서 호출
    # ============================================
    
    def record_loop_latency(self, symbol: str, latency_ms: float):
        """
        Engine loop latency 기록
        
        Args:
            symbol: 심볼
            latency_ms: Loop latency (밀리초)
        """
        if not self.enabled:
            return
        
        latency_sec = latency_ms / 1000.0
        self.loop_latency.labels(mode=self.mode, symbol=symbol).observe(latency_sec)
    
    def record_candle_processed(self, symbol: str):
        """
        캔들 처리 카운트 기록
        
        Args:
            symbol: 심볼
        """
        if not self.enabled:
            return
        
        self.candles_processed.labels(mode=self.mode, symbol=symbol).inc()
    
    def record_strategy_signal(
        self,
        symbol: str,
        strategy: str,
        has_signal: bool,
        side: Optional[str] = None,
        regime: Optional[str] = None
    ):
        """
        전략 신호 기록
        
        Args:
            symbol: 심볼
            strategy: 전략 ID
            has_signal: 신호 여부
            side: 신호 방향 (LONG/SHORT, optional)
            regime: 레짐 (RANGE/TREND, optional)
        """
        if not self.enabled:
            return
        
        # Total signals
        has_signal_str = "true" if has_signal else "false"
        self.strategy_signals.labels(
            mode=self.mode,
            symbol=symbol,
            strategy=strategy,
            has_signal=has_signal_str
        ).inc()
        
        # By side
        if has_signal and side:
            self.strategy_signals_by_side.labels(
                mode=self.mode,
                symbol=symbol,
                strategy=strategy,
                side=side.upper()
            ).inc()
        
        # By regime
        if has_signal and regime:
            self.strategy_signals_by_regime.labels(
                mode=self.mode,
                symbol=symbol,
                strategy=strategy,
                regime=regime.upper()
            ).inc()
    
    def record_ensemble_decision(self, symbol: str, tier: str):
        """
        앙상블 결정 기록
        
        Args:
            symbol: 심볼
            tier: 결정 티어 (tier1/tier2/skip)
        """
        if not self.enabled:
            return
        
        self.ensemble_decisions.labels(
            mode=self.mode,
            symbol=symbol,
            tier=tier.lower()
        ).inc()
    
    def record_guard_block(self, symbol: str, reason: str):
        """
        Guard/Risk 블록 기록
        
        Args:
            symbol: 심볼
            reason: 블록 사유
        """
        if not self.enabled:
            return
        
        self.guard_blocks.labels(
            mode=self.mode,
            symbol=symbol,
            reason=reason
        ).inc()
    
    def record_order_submitted(self, symbol: str):
        """
        주문 제출 기록
        
        Args:
            symbol: 심볼
        """
        if not self.enabled:
            return
        
        self.orders_submitted.labels(
            mode=self.mode,
            symbol=symbol
        ).inc()
    
    def record_trade(self, symbol: str, side: str):
        """
        트레이드 (체결) 기록
        
        Args:
            symbol: 심볼
            side: 포지션 방향 (LONG/SHORT)
        """
        if not self.enabled:
            return
        
        self.trades.labels(
            mode=self.mode,
            symbol=symbol,
            side=side.upper()
        ).inc()
    
    def update_pnl(self, symbol: str, pnl: float):
        """
        PnL 업데이트
        
        Args:
            symbol: 심볼
            pnl: 현재 PnL
        """
        if not self.enabled:
            return
        
        self.pnl_total.labels(
            mode=self.mode,
            symbol=symbol
        ).set(pnl)
    
    def update_open_positions(self, symbol: str, count: int):
        """
        오픈 포지션 수 업데이트
        
        Args:
            symbol: 심볼
            count: 오픈 포지션 수
        """
        if not self.enabled:
            return
        
        self.open_positions.labels(
            mode=self.mode,
            symbol=symbol
        ).set(count)
    
    def update_budget_used_ratio(self, ratio: float):
        """
        Budget 사용 비율 업데이트
        
        Args:
            ratio: Budget 사용 비율 (0.0 ~ 1.0)
        """
        if not self.enabled:
            return
        
        self.budget_used_ratio.labels(mode=self.mode).set(ratio)
    
    def record_error(self, level: str):
        """
        엔진 에러 기록
        
        Args:
            level: 로그 레벨 (ERROR/CRITICAL)
        """
        if not self.enabled:
            return
        
        self.engine_errors.labels(
            mode=self.mode,
            level=level.upper()
        ).inc()
    
    def update_cpu_usage(self, percent: float):
        """
        CPU 사용률 업데이트
        
        Args:
            percent: CPU 사용률 (0.0 ~ 100.0)
        """
        if not self.enabled:
            return
        
        self.cpu_usage.labels(mode=self.mode).set(percent)
    
    def update_memory_usage(self, mb: float):
        """
        메모리 사용량 업데이트
        
        Args:
            mb: 메모리 사용량 (MB)
        """
        if not self.enabled:
            return
        
        self.memory_usage.labels(mode=self.mode).set(mb)


# ============================================
# 전역 인스턴스 (엔진에서 초기화)
# ============================================

_global_exporter: Optional[PrometheusExporter] = None


def init_prometheus_exporter(
    enabled: bool = True,
    port: int = 9091,
    mode: str = "paper"
) -> PrometheusExporter:
    """
    전역 Prometheus Exporter 초기화
    
    Args:
        enabled: 모니터링 활성화 여부
        port: HTTP 서버 포트
        mode: 실행 모드
    
    Returns:
        PrometheusExporter 인스턴스
    """
    global _global_exporter
    
    _global_exporter = PrometheusExporter(
        enabled=enabled,
        port=port,
        mode=mode
    )
    
    if enabled:
        _global_exporter.start()
    
    return _global_exporter


def get_prometheus_exporter() -> Optional[PrometheusExporter]:
    """
    전역 Exporter 인스턴스 반환
    
    Returns:
        PrometheusExporter 인스턴스 (초기화 전이면 None)
    """
    return _global_exporter
