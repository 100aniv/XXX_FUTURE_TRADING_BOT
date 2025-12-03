"""
Multi-Symbol Performance Profiler - PHASE26-3
=============================================

Multi-Symbol Engine 전용 프로파일러

기능:
- Per-symbol indicator latency 측정
- Loop latency per-symbol 측정
- Queue depth tracking
- Hot path 자동 분석
- 프로파일 리포트 생성

재사용:
- monitoring.telemetry_profiler.TelemetryProfiler
- monitoring.telemetry_profiler.PerformanceMonitor
"""

import time
import psutil
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from collections import defaultdict, deque
from contextlib import contextmanager
import logging

# ⭐ 기존 profiler 재사용
from monitoring.telemetry_profiler import (
    TelemetryProfiler,
    PerformanceMonitor,
)

logger = logging.getLogger(__name__)


class MultiSymbolProfiler:
    """
    Multi-Symbol 전용 프로파일러 (PHASE26-3)
    
    목적:
    - Top100 심볼 처리 시 성능 병목 식별
    - Per-symbol/per-indicator latency 측정
    - 자동 hot path 분석
    
    Usage:
        profiler = MultiSymbolProfiler()
        
        # Loop latency
        with profiler.profile_loop(symbol):
            # 캔들 처리
            pass
        
        # Indicator latency
        profiler.log_indicator_latency(symbol, "RSI", duration_ms)
        
        # 분석
        hot_paths = profiler.analyze_hot_paths()
        profiler.export_report("report.json")
    """
    
    def __init__(self, enabled: bool = True):
        # ⭐ 기존 profiler 재사용
        self.telemetry = TelemetryProfiler()
        self.perf = PerformanceMonitor()
        
        self.enabled = enabled
        
        # PHASE26-3 전용 메트릭
        self.per_symbol_indicators: Dict[str, Dict[str, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )  # {symbol: {indicator: [latency_ms]}}
        
        self.loop_latencies: Dict[str, List[float]] = defaultdict(list)
        # {symbol: [latency_ms]}
        
        self.queue_depths: Dict[str, List[int]] = defaultdict(list)
        # {symbol: [depth]}
        
        # 시스템 리소스 (전역)
        self.cpu_samples: List[float] = []
        self.memory_samples: List[float] = []  # MB
        
        self._start_time = time.time()
    
    def log_indicator_latency(
        self,
        symbol: str,
        indicator: str,
        duration_ms: float
    ):
        """
        Indicator 계산 latency 기록
        
        Args:
            symbol: 심볼 이름
            indicator: Indicator 이름 (예: "RSI", "EMA20")
            duration_ms: 실행 시간 (밀리초)
        """
        if not self.enabled:
            return
        
        self.per_symbol_indicators[symbol][indicator].append(duration_ms)
        
        # 최근 1000개만 유지
        if len(self.per_symbol_indicators[symbol][indicator]) > 1000:
            self.per_symbol_indicators[symbol][indicator] = (
                self.per_symbol_indicators[symbol][indicator][-1000:]
            )
    
    @contextmanager
    def profile_loop(self, symbol: str):
        """
        Loop latency 측정 컨텍스트 매니저
        
        Usage:
            with profiler.profile_loop("BTCUSDT"):
                # 캔들 처리 로직
                pass
        
        Args:
            symbol: 심볼 이름
        """
        if not self.enabled:
            yield
            return
        
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.loop_latencies[symbol].append(duration_ms)
            
            # 최근 1000개만 유지
            if len(self.loop_latencies[symbol]) > 1000:
                self.loop_latencies[symbol] = self.loop_latencies[symbol][-1000:]
    
    def log_queue_depth(self, symbol: str, depth: int):
        """
        Feed queue depth 기록
        
        Args:
            symbol: 심볼 이름
            depth: Queue depth (대기 중인 캔들 수)
        """
        if not self.enabled:
            return
        
        self.queue_depths[symbol].append(depth)
        
        # 최근 1000개만 유지
        if len(self.queue_depths[symbol]) > 1000:
            self.queue_depths[symbol] = self.queue_depths[symbol][-1000:]
    
    def log_system_resource(self):
        """
        시스템 리소스 (CPU/메모리) 기록
        
        Note: 5초 간격으로 호출 권장
        """
        if not self.enabled:
            return
        
        try:
            process = psutil.Process()
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            self.cpu_samples.append(cpu_percent)
            self.memory_samples.append(memory_mb)
            
            # 최근 1000개만 유지
            if len(self.cpu_samples) > 1000:
                self.cpu_samples = self.cpu_samples[-1000:]
                self.memory_samples = self.memory_samples[-1000:]
        
        except Exception as e:
            logger.warning(f"시스템 리소스 측정 실패: {e}")
    
    def analyze_hot_paths(self, top_n: int = 10) -> List[Tuple[str, str, float, float]]:
        """
        Hot Path 자동 분석 (느린 Indicator Top N)
        
        Args:
            top_n: 반환할 개수
        
        Returns:
            [(symbol, indicator, avg_ms, p95_ms), ...]
            P95 latency 기준 내림차순 정렬
        """
        hot_paths = []
        
        for symbol, indicators in self.per_symbol_indicators.items():
            for indicator, latencies in indicators.items():
                if not latencies:
                    continue
                
                avg_ms = sum(latencies) / len(latencies)
                sorted_latencies = sorted(latencies)
                p95_idx = int(len(sorted_latencies) * 0.95)
                p95_ms = sorted_latencies[p95_idx] if p95_idx < len(sorted_latencies) else sorted_latencies[-1]
                
                hot_paths.append((symbol, indicator, avg_ms, p95_ms))
        
        # P95 기준 내림차순 정렬
        hot_paths.sort(key=lambda x: x[3], reverse=True)
        
        return hot_paths[:top_n]
    
    def get_summary(self) -> Dict[str, Any]:
        """
        프로파일 요약 반환
        
        Returns:
            {
                "per_symbol_indicators": {...},
                "loop_latencies": {...},
                "queue_depths": {...},
                "system_resources": {...},
                "hot_paths": [...]
            }
        """
        summary = {
            "profiler_enabled": self.enabled,
            "duration_sec": time.time() - self._start_time,
            "per_symbol_indicators": {},
            "loop_latencies": {},
            "queue_depths": {},
            "system_resources": {},
            "hot_paths": []
        }
        
        # Per-symbol indicator 요약
        for symbol, indicators in self.per_symbol_indicators.items():
            summary["per_symbol_indicators"][symbol] = {}
            for indicator, latencies in indicators.items():
                if not latencies:
                    continue
                
                sorted_latencies = sorted(latencies)
                n = len(sorted_latencies)
                
                summary["per_symbol_indicators"][symbol][indicator] = {
                    "count": n,
                    "avg_ms": round(sum(latencies) / n, 2),
                    "p50_ms": round(sorted_latencies[int(n * 0.5)], 2),
                    "p95_ms": round(sorted_latencies[int(n * 0.95)], 2),
                    "p99_ms": round(sorted_latencies[int(n * 0.99)], 2),
                    "min_ms": round(min(latencies), 2),
                    "max_ms": round(max(latencies), 2),
                }
        
        # Loop latency 요약
        for symbol, latencies in self.loop_latencies.items():
            if not latencies:
                continue
            
            sorted_latencies = sorted(latencies)
            n = len(sorted_latencies)
            
            summary["loop_latencies"][symbol] = {
                "count": n,
                "avg_ms": round(sum(latencies) / n, 2),
                "p50_ms": round(sorted_latencies[int(n * 0.5)], 2),
                "p95_ms": round(sorted_latencies[int(n * 0.95)], 2),
                "p99_ms": round(sorted_latencies[int(n * 0.99)], 2),
                "min_ms": round(min(latencies), 2),
                "max_ms": round(max(latencies), 2),
            }
        
        # Queue depth 요약
        for symbol, depths in self.queue_depths.items():
            if not depths:
                continue
            
            summary["queue_depths"][symbol] = {
                "count": len(depths),
                "avg": round(sum(depths) / len(depths), 2),
                "max": max(depths),
                "min": min(depths),
            }
        
        # 시스템 리소스 요약
        if self.cpu_samples:
            summary["system_resources"]["cpu"] = {
                "avg_percent": round(sum(self.cpu_samples) / len(self.cpu_samples), 2),
                "max_percent": round(max(self.cpu_samples), 2),
                "min_percent": round(min(self.cpu_samples), 2),
            }
        
        if self.memory_samples:
            summary["system_resources"]["memory"] = {
                "avg_mb": round(sum(self.memory_samples) / len(self.memory_samples), 2),
                "max_mb": round(max(self.memory_samples), 2),
                "min_mb": round(min(self.memory_samples), 2),
            }
        
        # Hot paths
        summary["hot_paths"] = [
            {
                "symbol": symbol,
                "indicator": indicator,
                "avg_ms": round(avg_ms, 2),
                "p95_ms": round(p95_ms, 2)
            }
            for symbol, indicator, avg_ms, p95_ms in self.analyze_hot_paths(top_n=10)
        ]
        
        return summary
    
    def export_report(self, output_path: str):
        """
        프로파일 리포트를 JSON 파일로 Export
        
        Args:
            output_path: 출력 파일 경로 (.json)
        """
        data = {
            "summary": self.get_summary(),
            "exported_at": time.time()
        }
        
        Path(output_path).write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        logger.info(f"📊 프로파일 리포트 Export: {output_path}")
    
    def reset(self):
        """프로파일 데이터 초기화"""
        self.per_symbol_indicators.clear()
        self.loop_latencies.clear()
        self.queue_depths.clear()
        self.cpu_samples.clear()
        self.memory_samples.clear()
        self._start_time = time.time()
    
    def enable(self):
        """프로파일링 활성화"""
        self.enabled = True
    
    def disable(self):
        """프로파일링 비활성화"""
        self.enabled = False


# 전역 인스턴스
multi_symbol_profiler = MultiSymbolProfiler(enabled=False)  # 기본 비활성화


# ============================================
# 편의 함수
# ============================================

def profile_loop(symbol: str):
    """
    Loop latency 측정 컨텍스트 매니저 (전역 profiler)
    
    Usage:
        with profile_loop("BTCUSDT"):
            # 캔들 처리
            pass
    """
    return multi_symbol_profiler.profile_loop(symbol)


def log_indicator_latency(symbol: str, indicator: str, duration_ms: float):
    """Indicator latency 기록 (전역 profiler)"""
    multi_symbol_profiler.log_indicator_latency(symbol, indicator, duration_ms)


def log_queue_depth(symbol: str, depth: int):
    """Queue depth 기록 (전역 profiler)"""
    multi_symbol_profiler.log_queue_depth(symbol, depth)


def log_system_resource():
    """시스템 리소스 기록 (전역 profiler)"""
    multi_symbol_profiler.log_system_resource()


def analyze_hot_paths(top_n: int = 10) -> List[Tuple[str, str, float, float]]:
    """Hot path 분석 (전역 profiler)"""
    return multi_symbol_profiler.analyze_hot_paths(top_n)


def export_profile_report(output_path: str):
    """프로파일 리포트 Export (전역 profiler)"""
    multi_symbol_profiler.export_report(output_path)


def get_profile_summary() -> Dict[str, Any]:
    """프로파일 요약 반환 (전역 profiler)"""
    return multi_symbol_profiler.get_summary()


def enable_profiling():
    """전역 profiler 활성화"""
    multi_symbol_profiler.enable()


def disable_profiling():
    """전역 profiler 비활성화"""
    multi_symbol_profiler.disable()


def reset_profiler():
    """전역 profiler 초기화"""
    multi_symbol_profiler.reset()
