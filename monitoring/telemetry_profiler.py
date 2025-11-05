"""
Telemetry Profiler - Deep Performance Profiling
===============================================

심층 성능 프로파일링:
- 함수 실행 시간/메모리 측정 (데코레이터 방식)
- 이벤트 단위 처리 시간 측정
- 처리량/지연 분포 분석
- 핫스팟 이벤트 감지
- 프로파일 데이터 Export

Note:
- 이 모듈은 common/performance.py의 PerformanceMonitor 클래스를 이관받았습니다.
- 시스템 성능 측정(CPU/Memory 점수)은 monitoring/performance_monitor.py를 사용하세요.
"""

import time
import psutil
import functools
import threading
import json
from pathlib import Path
from typing import Dict, Any, List, Callable
from collections import defaultdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TelemetryProfiler:
    """
    Telemetry Profiler - 이벤트 기반 프로파일링
    
    Usage:
        profiler = TelemetryProfiler()
        
        with profiler.profile("candle_processing"):
            # 처리 로직
            pass
        
        summary = profiler.get_summary()
    """
    
    def __init__(self):
        self.events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.enabled = True
    
    def log_event(self, event_name: str, duration_ms: float, metadata: Dict[str, Any] = None):
        """
        이벤트 기록
        
        Args:
            event_name: 이벤트 이름
            duration_ms: 실행 시간 (ms)
            metadata: 추가 메타데이터
        """
        if not self.enabled:
            return
        
        self.events[event_name].append({
            "ts": time.time(),
            "duration_ms": duration_ms,
            "metadata": metadata or {}
        })
        
        # 최근 1000개만 유지
        if len(self.events[event_name]) > 1000:
            self.events[event_name] = self.events[event_name][-1000:]
    
    def profile(self, event_name: str):
        """
        컨텍스트 매니저로 자동 프로파일링
        
        Usage:
            with profiler.profile("my_function"):
                # 처리 로직
                pass
        """
        return ProfileContext(self, event_name)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        프로파일 요약 반환
        
        Returns:
            {
                event_name: {
                    count, avg_ms, p50_ms, p95_ms, p99_ms, min_ms, max_ms
                },
                ...
            }
        """
        summary = {}
        
        for event_name, samples in self.events.items():
            if not samples:
                continue
            
            durations = [s["duration_ms"] for s in samples]
            durations_sorted = sorted(durations)
            n = len(durations_sorted)
            
            summary[event_name] = {
                "count": n,
                "avg_ms": round(sum(durations) / n, 2),
                "p50_ms": round(durations_sorted[int(n * 0.5)], 2),
                "p95_ms": round(durations_sorted[int(n * 0.95)], 2),
                "p99_ms": round(durations_sorted[int(n * 0.99)], 2),
                "min_ms": round(min(durations), 2),
                "max_ms": round(max(durations), 2)
            }
        
        return summary
    
    def export_profile(self, output_path: str):
        """
        프로파일 데이터를 JSON 파일로 Export
        
        Args:
            output_path: 출력 파일 경로
        """
        import json
        from pathlib import Path
        
        data = {
            "summary": self.get_summary(),
            "raw_events": {k: v[-100:] for k, v in self.events.items()},  # 최근 100개만
            "exported_at": time.time()
        }
        
        Path(output_path).write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        logger.info(f"📊 프로파일 Export: {output_path}")
    
    def reset(self):
        """프로파일 데이터 초기화"""
        self.events.clear()


class ProfileContext:
    """프로파일링 컨텍스트 매니저"""
    
    def __init__(self, profiler: TelemetryProfiler, event_name: str):
        self.profiler = profiler
        self.event_name = event_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        self.profiler.log_event(self.event_name, duration_ms)


# 전역 인스턴스
telemetry_profiler = TelemetryProfiler()


def profile(event_name: str):
    """프로파일링 컨텍스트 매니저 (편의 함수)"""
    return telemetry_profiler.profile(event_name)


def log_event(event_name: str, duration_ms: float, metadata: Dict[str, Any] = None):
    """이벤트 기록 (편의 함수)"""
    telemetry_profiler.log_event(event_name, duration_ms, metadata)


def get_profile_summary() -> Dict[str, Any]:
    """프로파일 요약 반환 (편의 함수)"""
    return telemetry_profiler.get_summary()


# ============================================
# PerformanceMonitor (from common/performance.py)
# ============================================

class PerformanceMonitor:
    """
    성능 모니터링 클래스 (함수 프로파일링)
    
    함수 실행 시간/메모리를 측정하고 성능 경고를 생성합니다.
    """
    
    def __init__(self):
        self.metrics = {
            'function_calls': {},
            'system_stats': [],
            'alerts': []
        }
        self.monitoring = False
        self.monitor_thread = None
    
    def measure_time(self, func: Callable):
        """
        함수 실행 시간 측정 데코레이터
        
        사용법:
        @performance.measure_time
        def my_function():
            ...
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            try:
                result = func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                result = None
                success = False
                error = str(e)
                raise
            finally:
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024
                
                execution_time = end_time - start_time
                memory_used = end_memory - start_memory
                
                # 메트릭 저장
                func_name = f"{func.__module__}.{func.__name__}"
                
                if func_name not in self.metrics['function_calls']:
                    self.metrics['function_calls'][func_name] = []
                
                self.metrics['function_calls'][func_name].append({
                    'timestamp': datetime.now().isoformat(),
                    'execution_time': execution_time,
                    'memory_used': memory_used,
                    'success': success,
                    'error': error
                })
                
                # 성능 경고 (3초 이상 또는 100MB 이상)
                if execution_time > 3.0:
                    self.add_alert(f"⚠️  느린 실행: {func_name} ({execution_time:.2f}s)")
                
                if memory_used > 100:
                    self.add_alert(f"⚠️  메모리 과다 사용: {func_name} ({memory_used:.2f}MB)")
            
            return result
        
        return wrapper
    
    def add_alert(self, message: str):
        """성능 경고 추가"""
        self.metrics['alerts'].append({
            'timestamp': datetime.now().isoformat(),
            'message': message
        })
    
    def start_monitoring(self, interval: float = 5.0):
        """
        시스템 리소스 모니터링 시작
        
        Args:
            interval: 측정 간격 (초)
        """
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
    
    def _monitor_loop(self, interval: float):
        """모니터링 루프"""
        process = psutil.Process()
        
        while self.monitoring:
            try:
                cpu_percent = process.cpu_percent(interval=0.1)
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                
                # 시스템 전체
                system_cpu = psutil.cpu_percent(interval=0.1)
                system_memory = psutil.virtual_memory()
                
                self.metrics['system_stats'].append({
                    'timestamp': datetime.now().isoformat(),
                    'process_cpu': cpu_percent,
                    'process_memory_mb': memory_mb,
                    'system_cpu': system_cpu,
                    'system_memory_percent': system_memory.percent,
                    'system_memory_available_mb': system_memory.available / 1024 / 1024
                })
                
                # CPU 과부하 경고
                if cpu_percent > 80:
                    self.add_alert(f"⚠️  CPU 과부하: {cpu_percent:.1f}%")
                
                # 메모리 과다 경고
                if memory_mb > 1000:  # 1GB
                    self.add_alert(f"⚠️  메모리 과다: {memory_mb:.1f}MB")
                
            except Exception as e:
                logger.warning(f"모니터링 오류: {e}")
            
            time.sleep(interval)
    
    def get_summary(self) -> Dict[str, Any]:
        """성능 요약 정보"""
        summary = {
            'total_functions': len(self.metrics['function_calls']),
            'total_alerts': len(self.metrics['alerts']),
            'function_stats': {},
            'system_stats_summary': None
        }
        
        # 함수별 통계
        for func_name, calls in self.metrics['function_calls'].items():
            if not calls:
                continue
            
            exec_times = [c['execution_time'] for c in calls]
            memory_used = [c['memory_used'] for c in calls]
            success_count = sum(1 for c in calls if c['success'])
            
            summary['function_stats'][func_name] = {
                'call_count': len(calls),
                'success_rate': success_count / len(calls) if calls else 0,
                'avg_time': sum(exec_times) / len(exec_times) if exec_times else 0,
                'max_time': max(exec_times) if exec_times else 0,
                'min_time': min(exec_times) if exec_times else 0,
                'avg_memory': sum(memory_used) / len(memory_used) if memory_used else 0,
                'max_memory': max(memory_used) if memory_used else 0
            }
        
        # 시스템 통계 요약
        if self.metrics['system_stats']:
            cpu_values = [s['process_cpu'] for s in self.metrics['system_stats']]
            memory_values = [s['process_memory_mb'] for s in self.metrics['system_stats']]
            
            summary['system_stats_summary'] = {
                'avg_cpu': sum(cpu_values) / len(cpu_values),
                'max_cpu': max(cpu_values),
                'avg_memory_mb': sum(memory_values) / len(memory_values),
                'max_memory_mb': max(memory_values),
                'sample_count': len(self.metrics['system_stats'])
            }
        
        return summary
    
    def export(self, output_path: str):
        """성능 메트릭 저장"""
        data = {
            'metrics': self.metrics,
            'summary': self.get_summary(),
            'exported_at': datetime.now().isoformat()
        }
        
        Path(output_path).write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        logger.info(f"📊 성능 메트릭 저장: {output_path}")
    
    def print_summary(self):
        """성능 요약 출력"""
        summary = self.get_summary()
        
        print("\n" + "="*60)
        print("📊 성능 요약")
        print("="*60)
        
        # 함수별 통계
        if summary['function_stats']:
            print("\n📈 함수 실행 통계:")
            for func_name, stats in summary['function_stats'].items():
                print(f"\n  {func_name}:")
                print(f"    호출 횟수: {stats['call_count']}")
                print(f"    성공률: {stats['success_rate']:.1%}")
                print(f"    평균 시간: {stats['avg_time']:.3f}s")
                print(f"    최대 시간: {stats['max_time']:.3f}s")
                print(f"    평균 메모리: {stats['avg_memory']:.2f}MB")
        
        # 시스템 통계
        if summary['system_stats_summary']:
            sys_stats = summary['system_stats_summary']
            print(f"\n💻 시스템 리소스:")
            print(f"    평균 CPU: {sys_stats['avg_cpu']:.1f}%")
            print(f"    최대 CPU: {sys_stats['max_cpu']:.1f}%")
            print(f"    평균 메모리: {sys_stats['avg_memory_mb']:.1f}MB")
            print(f"    최대 메모리: {sys_stats['max_memory_mb']:.1f}MB")
            print(f"    측정 횟수: {sys_stats['sample_count']}")
        
        # 경고
        if self.metrics['alerts']:
            print(f"\n⚠️  경고 ({len(self.metrics['alerts'])}건):")
            for alert in self.metrics['alerts'][-5:]:  # 최근 5개만
                print(f"    {alert['message']}")
        
        print("="*60)


# 전역 프로파일러 인스턴스
performance = PerformanceMonitor()


# 편의 함수 (PerformanceMonitor용)
def measure_time(func):
    """함수 실행 시간 측정 데코레이터"""
    return performance.measure_time(func)


def start_monitoring(interval: float = 5.0):
    """시스템 모니터링 시작"""
    performance.start_monitoring(interval)


def stop_monitoring():
    """시스템 모니터링 중지"""
    performance.stop_monitoring()


def get_performance_summary() -> Dict[str, Any]:
    """성능 요약 정보"""
    return performance.get_summary()


def export_performance(output_path: str):
    """성능 메트릭 저장"""
    performance.export(output_path)


def print_performance_summary():
    """성능 요약 출력"""
    performance.print_summary()


# ============================================
# 모듈 공개 인터페이스
# ============================================

__all__ = [
    # TelemetryProfiler (이벤트 기반)
    "TelemetryProfiler",
    "telemetry_profiler",
    "profile",
    "log_event",
    "get_profile_summary",
    # PerformanceMonitor (함수 프로파일링)
    "PerformanceMonitor",
    "performance",
    "measure_time",
    "start_monitoring",
    "stop_monitoring",
    "get_performance_summary",
    "export_performance",
    "print_performance_summary"
]
