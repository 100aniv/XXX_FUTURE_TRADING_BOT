#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Metrics Adapter
===============
PHASE28-0: TradeActivityTracker/MultiSymbolProfiler → PrometheusExporter 어댑터

목적:
- 기존 Tracker/Profiler의 데이터를 Prometheus Exporter로 전달
- 엔진의 DO-NOT-TOUCH 원칙 유지 (최소 침투)
- 선택적 활성화 (Config 기반)

사용법:
    # 초기화 (엔진 시작 시)
    adapter = MetricsAdapter(
        exporter=prometheus_exporter,
        tracker=trade_activity_tracker,
        profiler=multi_symbol_profiler
    )
    
    # Tracker 데이터 → Exporter (주기적으로 또는 종료 시)
    adapter.sync_tracker_to_exporter()
    
    # Profiler 데이터 → Exporter (주기적으로 또는 종료 시)
    adapter.sync_profiler_to_exporter()
"""
from typing import Optional
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


class MetricsAdapter:
    """
    Tracker/Profiler → PrometheusExporter 어댑터 (PHASE28-0)
    
    역할:
    - TradeActivityTracker의 totals를 Prometheus Counter/Gauge에 반영
    - MultiSymbolProfiler의 latency/CPU/Memory를 Prometheus Gauge에 반영
    - 주기적 sync 또는 종료 시 final sync
    """
    
    def __init__(
        self,
        exporter: Optional[object] = None,
        tracker: Optional[object] = None,
        profiler: Optional[object] = None
    ):
        """
        어댑터 초기화
        
        Args:
            exporter: PrometheusExporter 인스턴스 (None이면 비활성화)
            tracker: TradeActivityTracker 인스턴스 (None이면 비활성화)
            profiler: MultiSymbolProfiler 인스턴스 (None이면 비활성화)
        """
        self.exporter = exporter
        self.tracker = tracker
        self.profiler = profiler
        
        # Exporter가 비활성화되어 있으면 어댑터도 비활성화
        self.enabled = (
            exporter is not None and
            hasattr(exporter, 'enabled') and
            exporter.enabled
        )
        
        if self.enabled:
            logger.info("📊 [PHASE28-0] MetricsAdapter 활성화")
        else:
            logger.info("📊 [PHASE28-0] MetricsAdapter 비활성화 (Exporter disabled or None)")
    
    def sync_tracker_to_exporter(self):
        """
        TradeActivityTracker → PrometheusExporter 동기화
        
        Note:
        - Tracker는 Counter 형태로 누적되므로, Exporter Counter에 직접 반영 불가
        - 대신, 현재 Tracker totals를 읽어서 Exporter의 내부 상태와 diff 계산 후 inc() 호출
        - 또는 Tracker 이벤트 시점에 Exporter를 직접 호출하는 방식 선택
        
        현재 구현:
        - Tracker totals를 읽고, 이전 sync 이후 증가분만 Exporter에 반영
        """
        if not self.enabled or self.tracker is None:
            return
        
        # Tracker totals 구조:
        # {
        #     "strategy_signals_total": int,
        #     "strategy_signals_true": int,
        #     "strategy_signals_false": int,
        #     "long_signals": int,
        #     "short_signals": int,
        #     "regime_range": int,
        #     "regime_trend": int,
        #     "ensemble_tier1": int,
        #     "ensemble_tier2": int,
        #     "ensemble_skip": int,
        #     "guard_blocks_total": int,
        #     "orders_submitted": int
        # }
        
        # Note: Tracker는 이미 이벤트 시점에 기록되므로,
        # 여기서는 최종 Summary 리포트용으로 로그만 남김
        totals = self.tracker.totals
        
        logger.debug(f"[PHASE28-0] Tracker totals: {totals}")
    
    def sync_profiler_to_exporter(self):
        """
        MultiSymbolProfiler → PrometheusExporter 동기화
        
        현재 구현:
        - Profiler의 CPU/Memory 샘플 평균을 Exporter Gauge에 반영
        - Loop latency는 실시간으로 Exporter에 기록되므로 여기서는 skip
        """
        if not self.enabled or self.profiler is None:
            return
        
        # CPU 샘플 평균
        if hasattr(self.profiler, 'cpu_samples') and self.profiler.cpu_samples:
            avg_cpu = sum(self.profiler.cpu_samples) / len(self.profiler.cpu_samples)
            self.exporter.update_cpu_usage(avg_cpu)
        
        # Memory 샘플 평균
        if hasattr(self.profiler, 'memory_samples') and self.profiler.memory_samples:
            avg_memory = sum(self.profiler.memory_samples) / len(self.profiler.memory_samples)
            self.exporter.update_memory_usage(avg_memory)
        
        logger.debug("[PHASE28-0] Profiler → Exporter 동기화 완료")
    
    def sync_all(self):
        """
        Tracker + Profiler 전체 동기화 (주기적 또는 종료 시)
        """
        if not self.enabled:
            return
        
        self.sync_tracker_to_exporter()
        self.sync_profiler_to_exporter()
        
        logger.debug("[PHASE28-0] MetricsAdapter: 전체 동기화 완료")


# ============================================
# 편의 함수: Tracker 이벤트 → Exporter 직접 호출
# ============================================

def on_strategy_signal(
    exporter: Optional[object],
    symbol: str,
    strategy: str,
    has_signal: bool,
    side: Optional[str] = None,
    regime: Optional[str] = None
):
    """
    전략 신호 이벤트 → Exporter 기록
    
    Usage: Tracker hook에서 호출
    """
    if exporter is None or not hasattr(exporter, 'enabled') or not exporter.enabled:
        return
    
    exporter.record_strategy_signal(
        symbol=symbol,
        strategy=strategy,
        has_signal=has_signal,
        side=side,
        regime=regime
    )


def on_ensemble_decision(
    exporter: Optional[object],
    symbol: str,
    tier: str
):
    """
    앙상블 결정 이벤트 → Exporter 기록
    
    Usage: Tracker hook에서 호출
    """
    if exporter is None or not hasattr(exporter, 'enabled') or not exporter.enabled:
        return
    
    exporter.record_ensemble_decision(symbol=symbol, tier=tier)


def on_guard_block(
    exporter: Optional[object],
    symbol: str,
    reason: str
):
    """
    Guard 블록 이벤트 → Exporter 기록
    
    Usage: Tracker hook에서 호출
    """
    if exporter is None or not hasattr(exporter, 'enabled') or not exporter.enabled:
        return
    
    exporter.record_guard_block(symbol=symbol, reason=reason)


def on_order_submitted(
    exporter: Optional[object],
    symbol: str
):
    """
    주문 제출 이벤트 → Exporter 기록
    
    Usage: Tracker hook에서 호출
    """
    if exporter is None or not hasattr(exporter, 'enabled') or not exporter.enabled:
        return
    
    exporter.record_order_submitted(symbol=symbol)


def on_loop_latency(
    exporter: Optional[object],
    symbol: str,
    latency_ms: float
):
    """
    Loop latency → Exporter 기록
    
    Usage: Profiler profile_loop 종료 시 호출
    """
    if exporter is None or not hasattr(exporter, 'enabled') or not exporter.enabled:
        return
    
    exporter.record_loop_latency(symbol=symbol, latency_ms=latency_ms)


def on_candle_processed(
    exporter: Optional[object],
    symbol: str
):
    """
    캔들 처리 → Exporter 기록
    
    Usage: 엔진 루프에서 캔들 처리 후 호출
    """
    if exporter is None or not hasattr(exporter, 'enabled') or not exporter.enabled:
        return
    
    exporter.record_candle_processed(symbol=symbol)
