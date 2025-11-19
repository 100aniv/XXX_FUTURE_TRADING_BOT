#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Latency Monitor
===============
PHASE18-4: 작업별 처리 시간 측정 및 지연 감지
"""
import time
from collections import deque, defaultdict
from typing import Dict, Any, Optional
from contextlib import contextmanager
from common.monitoring import BaseMonitor


class LatencyMonitor(BaseMonitor):
    """
    작업별 처리 시간 측정 및 지연 감지
    
    **기능**:
    - measure(task_name): Context manager로 측정
    - start_measure(task_name): 측정 시작
    - end_measure(task_name, start_time): 측정 종료
    - get_stats(task_name): 통계 조회 (count, mean, max, p95, p99)
    
    **사용 예시**:
    ```python
    latency = LatencyMonitor()
    latency.start()
    
    # Context manager 방식
    with latency.measure('candle_processing'):
        process_candle(candle)
    
    # 수동 방식
    start = latency.start_measure('signal_generation')
    generate_signal(df)
    latency.end_measure('signal_generation', start)
    
    # 통계 조회
    stats = latency.get_stats('candle_processing')
    # {'count': 100, 'mean': 0.05, 'max': 0.12, 'p95': 0.08}
    ```
    """
    
    def __init__(self, max_samples: int = 1000):
        """
        Args:
            max_samples: Task당 최대 샘플 수 (메모리 절약)
        """
        super().__init__(name='latency')
        self.max_samples = max_samples
        # {task_name: deque([latency1, latency2, ...], maxlen=max_samples)}
        self._latencies: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
    
    @contextmanager
    def measure(self, task_name: str):
        """
        Context manager로 처리 시간 측정
        
        Args:
            task_name: 작업 이름
        
        Usage:
            with latency.measure('task'):
                do_work()
        """
        start = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start
            self._latencies[task_name].append(elapsed)
    
    def start_measure(self, task_name: str) -> float:
        """
        측정 시작 (수동 방식)
        
        Args:
            task_name: 작업 이름
        
        Returns:
            float: 시작 timestamp
        """
        return time.time()
    
    def end_measure(self, task_name: str, start_time: float):
        """
        측정 종료 (수동 방식)
        
        Args:
            task_name: 작업 이름
            start_time: start_measure에서 반환된 timestamp
        """
        elapsed = time.time() - start_time
        self._latencies[task_name].append(elapsed)
    
    def get_stats(self, task_name: str) -> Optional[Dict[str, float]]:
        """
        통계 조회
        
        Args:
            task_name: 작업 이름
        
        Returns:
            Dict: {'count', 'mean', 'max', 'min', 'p95', 'p99'} 또는 None
        """
        if task_name not in self._latencies or not self._latencies[task_name]:
            return None
        
        samples = sorted(self._latencies[task_name])
        count = len(samples)
        
        mean = sum(samples) / count
        max_val = max(samples)
        min_val = min(samples)
        
        # Percentiles
        p95_idx = int(count * 0.95)
        p99_idx = int(count * 0.99)
        p95 = samples[min(p95_idx, count - 1)]
        p99 = samples[min(p99_idx, count - 1)]
        
        return {
            'count': count,
            'mean': mean,
            'max': max_val,
            'min': min_val,
            'p95': p95,
            'p99': p99,
        }
    
    def is_slow(self, task_name: str, threshold: float) -> bool:
        """
        평균 처리 시간이 threshold 초과 여부
        
        Args:
            task_name: 작업 이름
            threshold: 임계값 (초)
        
        Returns:
            bool: True if mean latency > threshold
        """
        stats = self.get_stats(task_name)
        if stats is None:
            return False
        return stats['mean'] > threshold
    
    def get_all_tasks(self) -> list:
        """측정된 모든 작업 목록"""
        return list(self._latencies.keys())
    
    def get_status(self) -> Dict[str, Any]:
        """
        현재 상태 반환
        
        Returns:
            Dict: {
                'tasks': ['task1', 'task2', ...],
                'stats': {'task1': {...}, 'task2': {...}}
            }
        """
        return {
            'tasks': self.get_all_tasks(),
            'stats': {
                task: self.get_stats(task)
                for task in self.get_all_tasks()
            }
        }
    
    def clear(self, task_name: Optional[str] = None):
        """
        통계 초기화
        
        Args:
            task_name: 특정 작업만 초기화 (None이면 전체 초기화)
        """
        if task_name:
            if task_name in self._latencies:
                self._latencies[task_name].clear()
        else:
            self._latencies.clear()
    
    def __repr__(self) -> str:
        return f"LatencyMonitor(tasks={len(self._latencies)}, max_samples={self.max_samples})"
