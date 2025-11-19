#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitoring Framework
====================
PHASE18-4: 프로덕션 운영 수준의 모니터링 인프라

Components:
- MonitorRegistry: 중앙 레지스트리
- HeartbeatMonitor: 컴포넌트 활성 체크
- Watchdog: 비정상 상태 감지
- LatencyMonitor: 처리 시간 측정
- HealthChecker: 시스템 헬스 체크
- ModuleStatus: 상태 집계
"""
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod


class BaseMonitor(ABC):
    """
    모든 모니터의 기본 클래스
    
    **인터페이스**:
    - start(): 모니터 시작
    - stop(): 모니터 중지
    - get_status(): 현재 상태 반환
    """
    
    def __init__(self, name: str):
        self.name = name
        self._running = False
    
    def start(self):
        """모니터 시작"""
        self._running = True
    
    def stop(self):
        """모니터 중지"""
        self._running = False
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """현재 상태 반환 (서브클래스에서 구현)"""
        pass
    
    def is_running(self) -> bool:
        """실행 중 여부"""
        return self._running


class MonitorRegistry:
    """
    모든 모니터 인스턴스의 중앙 레지스트리
    
    **사용 예시**:
    ```python
    registry = MonitorRegistry()
    
    # 모니터 등록
    heartbeat = HeartbeatMonitor()
    registry.register('heartbeat', heartbeat)
    
    # 모니터 가져오기
    monitor = registry.get('heartbeat')
    
    # 전체 상태 조회
    status = registry.get_status()
    
    # 전체 중지
    registry.stop_all()
    ```
    """
    
    def __init__(self):
        self._monitors: Dict[str, BaseMonitor] = {}
    
    def register(self, name: str, monitor: BaseMonitor):
        """
        모니터 등록
        
        Args:
            name: 모니터 이름
            monitor: BaseMonitor 인스턴스
        """
        self._monitors[name] = monitor
    
    def unregister(self, name: str):
        """
        모니터 해제
        
        Args:
            name: 모니터 이름
        """
        if name in self._monitors:
            self._monitors[name].stop()
            del self._monitors[name]
    
    def get(self, name: str) -> Optional[BaseMonitor]:
        """
        모니터 가져오기
        
        Args:
            name: 모니터 이름
        
        Returns:
            BaseMonitor 인스턴스 또는 None
        """
        return self._monitors.get(name)
    
    def stop_all(self):
        """모든 모니터 중지"""
        for monitor in self._monitors.values():
            monitor.stop()
    
    def get_status(self) -> Dict[str, Any]:
        """
        전체 모니터 상태 집계
        
        Returns:
            Dict[str, Any]: {monitor_name: status}
        """
        return {
            name: monitor.get_status()
            for name, monitor in self._monitors.items()
        }
    
    def __repr__(self) -> str:
        return f"MonitorRegistry(monitors={list(self._monitors.keys())})"


def setup_monitoring(runtime_ctx, config: Dict[str, Any]):
    """
    모니터링 시스템 초기화 (헬퍼 함수)
    
    Args:
        runtime_ctx: RuntimeContext 인스턴스
        config: 설정 딕셔너리
    
    Usage:
        setup_monitoring(runtime_ctx, cfg)
    """
    from common.monitoring.heartbeat_monitor import HeartbeatMonitor
    from common.monitoring.watchdog import Watchdog
    from common.monitoring.latency_monitor import LatencyMonitor
    from common.monitoring.health_checker import HealthChecker
    from common.monitoring.module_status import ModuleStatus
    
    # MonitorRegistry 생성
    registry = MonitorRegistry()
    
    # HeartbeatMonitor
    heartbeat = HeartbeatMonitor()
    heartbeat.start()
    registry.register('heartbeat', heartbeat)
    
    # Watchdog (HeartbeatMonitor 참조)
    watchdog_interval = config.get('monitoring', {}).get('watchdog_interval', 5.0)
    watchdog_max_age = config.get('monitoring', {}).get('watchdog_max_age', 60.0)
    watchdog = Watchdog(heartbeat, check_interval=watchdog_interval, max_age=watchdog_max_age)
    watchdog.start()
    registry.register('watchdog', watchdog)
    
    # LatencyMonitor
    latency = LatencyMonitor()
    latency.start()
    registry.register('latency', latency)
    
    # HealthChecker
    health = HealthChecker(config)
    health.start()
    registry.register('health', health)
    
    # ModuleStatus
    status = ModuleStatus()
    status.start()
    registry.register('status', status)
    
    # RuntimeContext에 등록
    runtime_ctx.monitor_registry = registry
    
    return registry


# Exports
__all__ = [
    'BaseMonitor',
    'MonitorRegistry',
    'setup_monitoring',
]
