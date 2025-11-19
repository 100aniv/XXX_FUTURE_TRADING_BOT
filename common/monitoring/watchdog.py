#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Watchdog Monitor
================
PHASE18-4: 주기적으로 heartbeat를 체크하고 비정상 상태 감지
"""
import time
import threading
from typing import Dict, Any
from common.monitoring import BaseMonitor
from common.monitoring.heartbeat_monitor import HeartbeatMonitor
from common.logger import setup_logger

logger = setup_logger(__name__)


class Watchdog(BaseMonitor):
    """
    주기적으로 heartbeat를 체크하고 비정상 상태 감지
    
    **동작**:
    - 별도 thread에서 check_interval마다 실행
    - HeartbeatMonitor의 모든 컴포넌트 체크
    - max_age 초과 시 경고 로그
    
    **사용 예시**:
    ```python
    heartbeat = HeartbeatMonitor()
    watchdog = Watchdog(heartbeat, check_interval=5.0, max_age=60.0)
    watchdog.start()
    
    # ... 시스템 실행 ...
    
    watchdog.stop()
    ```
    """
    
    def __init__(self, 
                 heartbeat_monitor: HeartbeatMonitor,
                 check_interval: float = 5.0,
                 max_age: float = 60.0):
        """
        Args:
            heartbeat_monitor: HeartbeatMonitor 인스턴스
            check_interval: 체크 주기 (초)
            max_age: heartbeat 최대 허용 시간 (초)
        """
        super().__init__(name='watchdog')
        self.heartbeat_monitor = heartbeat_monitor
        self.check_interval = check_interval
        self.max_age = max_age
        
        self._thread: threading.Thread = None
        self._warnings: Dict[str, int] = {}  # {component: warning_count}
    
    def start(self):
        """Watchdog thread 시작"""
        super().start()
        self._thread = threading.Thread(target=self._check_loop, daemon=True)
        self._thread.start()
        logger.info(f"🐕 Watchdog 시작 (interval={self.check_interval}s, max_age={self.max_age}s)")
    
    def stop(self):
        """Watchdog thread 중지"""
        super().stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.check_interval + 1.0)
        logger.info("🐕 Watchdog 중지")
    
    def _check_loop(self):
        """체크 루프 (thread)"""
        while self._running:
            try:
                self._check_all_components()
            except Exception as e:
                logger.error(f"❌ Watchdog 체크 실패: {e}")
            
            time.sleep(self.check_interval)
    
    def _check_all_components(self):
        """모든 컴포넌트 체크"""
        components = self.heartbeat_monitor.get_all_components()
        
        for comp in components:
            age = self.heartbeat_monitor.get_age(comp)
            if age is None:
                continue
            
            if age > self.max_age:
                # 경고 카운트 증가
                self._warnings[comp] = self._warnings.get(comp, 0) + 1
                logger.warning(
                    f"⚠️  [{comp}] Heartbeat 지연: {age:.1f}s (max: {self.max_age}s) "
                    f"[경고 {self._warnings[comp]}회]"
                )
            else:
                # 정상 복귀 시 경고 카운트 초기화
                if comp in self._warnings:
                    logger.info(f"✅ [{comp}] Heartbeat 정상 복귀 (age={age:.1f}s)")
                    del self._warnings[comp]
    
    def get_status(self) -> Dict[str, Any]:
        """
        현재 상태 반환
        
        Returns:
            Dict: {
                'running': True/False,
                'warnings': {'engine': 3, ...},
                'check_interval': 5.0,
                'max_age': 60.0
            }
        """
        return {
            'running': self._running,
            'warnings': dict(self._warnings),
            'check_interval': self.check_interval,
            'max_age': self.max_age
        }
    
    def has_warnings(self) -> bool:
        """경고 발생 여부"""
        return len(self._warnings) > 0
    
    def get_warning_components(self) -> list:
        """경고 발생 컴포넌트 목록"""
        return list(self._warnings.keys())
    
    def __repr__(self) -> str:
        return (
            f"Watchdog(interval={self.check_interval}s, max_age={self.max_age}s, "
            f"warnings={len(self._warnings)})"
        )
