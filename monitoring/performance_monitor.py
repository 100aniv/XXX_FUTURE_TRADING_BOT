#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Monitor - System Performance Metrics Collection
============================================================

시스템 성능 지표 수집 및 모니터링:
- CPU/Memory/Latency 성능 점수 계산
- Backfill 통계 추적
- WebSocket 연결 상태 모니터링
- Queue 상태 샘플링
- API/WS 레이턴시 추적

Note: 
- 이 모듈은 common/performance.py의 일부 기능을 이관받았습니다.
- 프로파일링 기능(PerformanceMonitor)은 monitoring/telemetry_profiler.py로 이관되었습니다.
"""

import time
import psutil
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


# ============================================
# 성능 점수 계산
# ============================================

def calculate_performance_scores() -> Dict[str, Any]:
    """
    성능 지표별 점수 계산 (0-100)
    
    Returns:
        {
            'cpu_score': float,  # CPU 효율 점수
            'memory_score': float,  # 메모리 효율 점수
            'speed_score': float,  # 처리 속도 점수
            'latency_score': float,  # 지연시간 점수
            'overall_score': float,  # 종합 점수
            'grade': str  # 등급 (S/A/B/C/D/F)
        }
    """
    process = psutil.Process()
    
    # 1. CPU 점수 (낮을수록 좋음)
    cpu_percent = process.cpu_percent(interval=0.1)
    cpu_score = max(0, 100 - cpu_percent)
    
    # 2. 메모리 점수 (낮을수록 좋음, 1GB 기준)
    memory_mb = process.memory_info().rss / 1024 / 1024
    memory_target = 1000  # 1GB
    memory_score = max(0, 100 - (memory_mb / memory_target * 100))
    
    # 3. 처리 속도 점수 (기본값, 실시간 측정 어려움)
    speed_score = 50
    candle_per_sec = 0
    
    # 4. 지연시간 점수 (latency_tracker 사용)
    latency_report = latency_tracker.get_report()
    latency_ms = latency_report.get("api_latency_ms_p50", 0)
    
    # 레이턴시 점수 계산 (낮을수록 좋음, 100ms 기준)
    if latency_ms == 0:
        latency_score = 50  # 샘플 없을 때 기본값
    else:
        latency_score = max(0, 100 - (latency_ms / 100 * 100))
    
    # 5. 종합 점수 (가중 평균)
    overall_score = (
        cpu_score * 0.3 +
        memory_score * 0.3 +
        speed_score * 0.2 +
        latency_score * 0.2
    )
    
    # 6. 등급 계산
    if overall_score >= 90:
        grade = 'S'
    elif overall_score >= 80:
        grade = 'A'
    elif overall_score >= 70:
        grade = 'B'
    elif overall_score >= 60:
        grade = 'C'
    elif overall_score >= 50:
        grade = 'D'
    else:
        grade = 'F'
    
    return {
        'cpu_score': round(cpu_score, 1),
        'cpu_percent': round(cpu_percent, 1),
        'memory_score': round(memory_score, 1),
        'memory_mb': round(memory_mb, 1),
        'speed_score': round(speed_score, 1),
        'candle_per_sec': round(candle_per_sec, 1),
        'latency_score': round(latency_score, 1),
        'latency_ms': round(latency_ms, 2),
        'overall_score': round(overall_score, 1),
        'grade': grade
    }


def get_performance_report(strategy: str = 'UNKNOWN') -> str:
    """
    성능 리포트 문자열 생성 (한 줄, 로그 + 텔레그램용)
    
    Args:
        strategy: 전략명
    
    Returns:
        한 줄 성능 리포트 문자열
    """
    scores = calculate_performance_scores()
    
    # 한 줄 포맷: CPU/Memory/Speed/Latency 모두 포함
    grade_emoji = {'S': '🌟', 'A': '✅', 'B': '⚠️ ', 'C': '⚠️ ', 'D': '❌', 'F': '❌'}
    emoji = grade_emoji.get(scores['grade'], '❓')
    
    # PR7-2: 앙상블 모드에서는 strategy가 None일 수 있음
    strategy_name = strategy.upper() if strategy else "ENSEMBLE"
    report = f"⚙️  [{strategy_name}] 성능: {emoji}{scores['grade']} ({scores['overall_score']:.0f}/100) | CPU {scores['cpu_percent']:.0f}% | Mem {scores['memory_mb']:.0f}MB | Speed {scores['candle_per_sec']:.1f}/s | Latency {scores['latency_ms']:.1f}ms"
    
    return report


# ============================================
# 백필 통계 추적
# ============================================

class BackfillStats:
    """
    백필 통계 추적 클래스
    
    **기능:**
    - Gap 발견 수 추적
    - 복구 성공/실패 카운트
    - 심볼별 통계
    - 복구율 계산
    
    **사용 예:**
    ```python
    stats = BackfillStats()
    
    # Gap 발견
    stats.record_gap("BTCUSDT")
    
    # 복구 성공
    stats.record_recovery("BTCUSDT", recovered=5, failed=0)
    
    # 리포트 조회
    report = stats.get_report()
    ```
    """
    
    def __init__(self):
        self.stats = {
            'total_gaps': 0,
            'total_recovered': 0,
            'total_failed': 0,
            'by_symbol': {}
        }
    
    def record_gap(self, symbol: str):
        """
        Gap 발견 기록
        
        Args:
            symbol: 심볼명
        """
        self.stats['total_gaps'] += 1
        
        if symbol not in self.stats['by_symbol']:
            self.stats['by_symbol'][symbol] = {
                'gaps': 0,
                'recovered': 0,
                'failed': 0
            }
        
        self.stats['by_symbol'][symbol]['gaps'] += 1
    
    def record_recovery(self, symbol: str, recovered: int, failed: int = 0):
        """
        복구 결과 기록
        
        Args:
            symbol: 심볼명
            recovered: 복구 성공 수
            failed: 복구 실패 수
        """
        self.stats['total_recovered'] += recovered
        self.stats['total_failed'] += failed
        
        if symbol not in self.stats['by_symbol']:
            self.stats['by_symbol'][symbol] = {
                'gaps': 0,
                'recovered': 0,
                'failed': 0
            }
        
        self.stats['by_symbol'][symbol]['recovered'] += recovered
        self.stats['by_symbol'][symbol]['failed'] += failed
    
    def get_report(self) -> Dict[str, Any]:
        """
        백필 통계 리포트 반환
        
        Returns:
            dict: 백필 통계 정보
                - total_gaps: 총 Gap 발견 수
                - total_recovered: 총 복구된 캔들 수
                - total_failed: 총 실패 수
                - recovery_rate: 복구율 (%)
                - by_symbol: 심볼별 통계
        """
        total = self.stats['total_gaps']
        recovered = self.stats['total_recovered']
        failed = self.stats['total_failed']
        
        recovery_rate = (recovered / total * 100) if total > 0 else 0
        
        return {
            'total_gaps': total,
            'total_recovered': recovered,
            'total_failed': failed,
            'recovery_rate': f"{recovery_rate:.1f}%",
            'by_symbol': self.stats['by_symbol']
        }
    
    def reset(self):
        """통계 초기화"""
        self.stats = {
            'total_gaps': 0,
            'total_recovered': 0,
            'total_failed': 0,
            'by_symbol': {}
        }


# 전역 백필 통계 인스턴스
backfill_stats = BackfillStats()


# ============================================
# WebSocket 연결 상태 모니터링
# ============================================

class ConnectionStats:
    """
    WebSocket 연결 상태 모니터링 클래스
    
    **기능:**
    - 연결/재연결 횟수 추적
    - 연결 상태 및 지속 시간 모니터링
    - 하트비트 및 타임아웃 추적
    - 연결 품질 리포트 생성
    
    **사용 예:**
    ```python
    stats = ConnectionStats()
    
    # 연결 이벤트
    stats.record_connect()
    stats.record_disconnect("network_error")
    
    # 하트비트
    stats.record_heartbeat()
    
    # 리포트 조회
    report = stats.get_report()
    ```
    """
    
    def __init__(self):
        self.stats = {
            'total_connects': 0,
            'total_disconnects': 0,
            'current_connected': False,
            'connection_start_time': None,
            'last_heartbeat_time': None,
            'heartbeat_count': 0,
            'disconnect_reasons': {},
            'connection_durations': [],
            'reconnect_attempts': 0
        }
    
    def record_connect(self):
        """연결 성공 기록"""
        now = time.time()
        
        self.stats['total_connects'] += 1
        self.stats['current_connected'] = True
        self.stats['connection_start_time'] = now
        self.stats['last_heartbeat_time'] = now
        self.stats['reconnect_attempts'] = 0
    
    def record_disconnect(self, reason: str = "unknown"):
        """연결 끊김 기록"""
        now = time.time()
        
        self.stats['total_disconnects'] += 1
        self.stats['current_connected'] = False
        
        # 연결 지속 시간 기록
        if self.stats['connection_start_time']:
            duration = now - self.stats['connection_start_time']
            self.stats['connection_durations'].append(duration)
        
        # 끊김 이유 카운트
        if reason not in self.stats['disconnect_reasons']:
            self.stats['disconnect_reasons'][reason] = 0
        self.stats['disconnect_reasons'][reason] += 1
        
        self.stats['connection_start_time'] = None
    
    def record_reconnect_attempt(self):
        """재연결 시도 기록"""
        self.stats['reconnect_attempts'] += 1
    
    def record_heartbeat(self):
        """하트비트 기록"""
        self.stats['last_heartbeat_time'] = time.time()
        self.stats['heartbeat_count'] += 1
    
    def get_report(self) -> Dict[str, Any]:
        """
        연결 상태 리포트 반환
        
        Returns:
            dict: 연결 상태 정보
                - current_connected: 현재 연결 상태
                - total_connects: 총 연결 수
                - total_disconnects: 총 끊김 수
                - avg_connection_duration: 평균 연결 지속 시간
                - last_heartbeat_ago: 마지막 하트비트 경과 시간
                - disconnect_reasons: 끊김 이유별 통계
        """
        now = time.time()
        
        # 평균 연결 지속 시간
        durations = self.stats['connection_durations']
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # 현재 연결 지속 시간
        current_duration = 0
        if self.stats['current_connected'] and self.stats['connection_start_time']:
            current_duration = now - self.stats['connection_start_time']
        
        # 마지막 하트비트 경과 시간
        last_heartbeat_ago = 0
        if self.stats['last_heartbeat_time']:
            last_heartbeat_ago = now - self.stats['last_heartbeat_time']
        
        return {
            'current_connected': self.stats['current_connected'],
            'total_connects': self.stats['total_connects'],
            'total_disconnects': self.stats['total_disconnects'],
            'reconnect_attempts': self.stats['reconnect_attempts'],
            'avg_connection_duration_sec': round(avg_duration, 1),
            'current_connection_duration_sec': round(current_duration, 1),
            'last_heartbeat_ago_sec': round(last_heartbeat_ago, 1),
            'heartbeat_count': self.stats['heartbeat_count'],
            'disconnect_reasons': self.stats['disconnect_reasons']
        }
    
    def reset(self):
        """통계 초기화"""
        self.stats = {
            'total_connects': 0,
            'total_disconnects': 0,
            'current_connected': False,
            'connection_start_time': None,
            'last_heartbeat_time': None,
            'heartbeat_count': 0,
            'disconnect_reasons': {},
            'connection_durations': [],
            'reconnect_attempts': 0
        }


# 전역 연결 통계 인스턴스
connection_stats = ConnectionStats()


# ============================================
# 시스템 성능 모니터
# ============================================

class SystemPerformanceMonitor:
    """
    시스템 성능 모니터
    
    CPU, Memory, Latency 등을 측정합니다.
    """
    
    def __init__(self):
        self.process = psutil.Process()
        self.start_time = time.time()
        self.latency_samples: List[float] = []
    
    def get_report(self) -> Dict[str, Any]:
        """
        시스템 성능 리포트 반환
        
        Returns:
            {cpu_pct, mem_mb, rss_mb, avg_latency_ms, score, grade}
        """
        try:
            # CPU
            cpu_pct = self.process.cpu_percent(interval=0.1)
            
            # Memory
            mem_info = self.process.memory_info()
            mem_mb = mem_info.rss / 1024 / 1024
            rss_mb = mem_info.rss / 1024 / 1024
            
            # Latency (최근 샘플 평균)
            avg_latency_ms = 0
            if self.latency_samples:
                avg_latency_ms = sum(self.latency_samples) / len(self.latency_samples)
                # 최근 100개만 유지
                if len(self.latency_samples) > 100:
                    self.latency_samples = self.latency_samples[-100:]
            
            # 성능 점수
            scores = calculate_performance_scores()
            
            return {
                "cpu_pct": round(cpu_pct, 1),
                "mem_mb": round(mem_mb, 1),
                "rss_mb": round(rss_mb, 1),
                "avg_latency_ms": round(avg_latency_ms, 2),
                "score": scores.get("overall_score", 0),
                "grade": scores.get("grade", "N/A")
            }
        except Exception as e:
            logger.warning(f"⚠️ SystemPerformanceMonitor.get_report 실패: {e}")
            return {
                "cpu_pct": 0,
                "mem_mb": 0,
                "rss_mb": 0,
                "avg_latency_ms": 0,
                "score": 0,
                "grade": "N/A"
            }
    
    def record_latency(self, latency_ms: float):
        """레이턴시 샘플 기록"""
        self.latency_samples.append(latency_ms)


# 전역 시스템 모니터 인스턴스
system_monitor = SystemPerformanceMonitor()


def get_system_metrics() -> Dict[str, Any]:
    """시스템 성능 지표 반환 (편의 함수)"""
    return system_monitor.get_report()


# ============================================
# Queue 상태 모니터
# ============================================

class QueueHealth:
    """
    큐 상태 모니터
    
    candle_queue 등 핵심 큐의 크기/드롭률을 추적합니다.
    """
    
    def __init__(self):
        self.queue_samples: Dict[str, List[Dict[str, Any]]] = {}
    
    def record_sample(self, queue_name: str, size: int, maxsize: int, drops: int = 0):
        """
        큐 상태 샘플 기록
        
        Args:
            queue_name: 큐 이름
            size: 현재 큐 크기
            maxsize: 최대 큐 크기
            drops: 드롭된 아이템 수
        """
        if queue_name not in self.queue_samples:
            self.queue_samples[queue_name] = []
        
        self.queue_samples[queue_name].append({
            "ts": time.time(),
            "size": size,
            "maxsize": maxsize,
            "drops": drops
        })
        
        # 최근 100개만 유지
        if len(self.queue_samples[queue_name]) > 100:
            self.queue_samples[queue_name] = self.queue_samples[queue_name][-100:]
    
    def get_report(self, queue_name: str = "candle_queue") -> Dict[str, Any]:
        """
        큐 상태 리포트 반환
        
        Args:
            queue_name: 큐 이름
        
        Returns:
            {size, maxsize, drop_rate, utilization}
        """
        samples = self.queue_samples.get(queue_name, [])
        
        if not samples:
            return {
                "size": 0,
                "maxsize": 0,
                "drop_rate": 0.0,
                "utilization": 0.0
            }
        
        # 최근 샘플
        latest = samples[-1]
        size = latest["size"]
        maxsize = latest["maxsize"]
        
        # 드롭률 계산 (최근 샘플들 기준)
        total_drops = sum(s["drops"] for s in samples)
        drop_rate = (total_drops / len(samples)) if samples else 0.0
        
        # 사용률 (%)
        utilization = (size / maxsize * 100) if maxsize > 0 else 0.0
        
        return {
            "size": size,
            "maxsize": maxsize,
            "drop_rate": round(drop_rate, 2),
            "utilization": round(utilization, 1)
        }


# 전역 큐 모니터 인스턴스
queue_health = QueueHealth()


def get_queue_health(queue_name: str = "candle_queue") -> Dict[str, Any]:
    """큐 상태 반환 (편의 함수)"""
    return queue_health.get_report(queue_name)


# ============================================
# API/WS 레이턴시 추적
# ============================================

class LatencyTracker:
    """
    API/WS 레이턴시 추적
    
    REST API, WebSocket 메시지 지연을 측정하고 백분위수를 계산합니다.
    """
    
    def __init__(self):
        self.latency_samples: List[float] = []
    
    def record(self, latency_ms: float):
        """레이턴시 샘플 기록"""
        self.latency_samples.append(latency_ms)
        
        # 최근 1000개만 유지
        if len(self.latency_samples) > 1000:
            self.latency_samples = self.latency_samples[-1000:]
    
    def get_report(self) -> Dict[str, Any]:
        """
        레이턴시 리포트 반환 (백분위수)
        
        Returns:
            {api_latency_ms_p50, api_latency_ms_p95, api_latency_ms_p99, sample_count}
        """
        if not self.latency_samples:
            return {
                "api_latency_ms_p50": 0,
                "api_latency_ms_p95": 0,
                "api_latency_ms_p99": 0,
                "sample_count": 0
            }
        
        sorted_samples = sorted(self.latency_samples)
        n = len(sorted_samples)
        
        p50_idx = int(n * 0.5)
        p95_idx = int(n * 0.95)
        p99_idx = int(n * 0.99)
        
        return {
            "api_latency_ms_p50": round(sorted_samples[p50_idx], 2),
            "api_latency_ms_p95": round(sorted_samples[p95_idx], 2),
            "api_latency_ms_p99": round(sorted_samples[p99_idx], 2),
            "sample_count": n
        }


# 전역 레이턴시 추적 인스턴스
latency_tracker = LatencyTracker()


def get_latency_report() -> Dict[str, Any]:
    """레이턴시 리포트 반환 (편의 함수)"""
    return latency_tracker.get_report()


# ============================================
# 모듈 공개 인터페이스
# ============================================

__all__ = [
    # 성능 점수
    "calculate_performance_scores",
    "get_performance_report",
    # 백필 통계
    "BackfillStats",
    "backfill_stats",
    # 연결 통계
    "ConnectionStats",
    "connection_stats",
    # 시스템 모니터
    "SystemPerformanceMonitor",
    "system_monitor",
    "get_system_metrics",
    # 큐 모니터
    "QueueHealth",
    "queue_health",
    "get_queue_health",
    # 레이턴시 추적
    "LatencyTracker",
    "latency_tracker",
    "get_latency_report"
]
