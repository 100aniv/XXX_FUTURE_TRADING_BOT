#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heartbeat Monitor
=================
PHASE18-4: 컴포넌트별 heartbeat 타임스탬프 관리
"""
import time
from typing import Dict, Optional, Any
from common.monitoring import BaseMonitor


class HeartbeatMonitor(BaseMonitor):
    """
    컴포넌트별 heartbeat 타임스탬프 관리
    
    **기능**:
    - update(component): Heartbeat 업데이트
    - get_last_heartbeat(component): 마지막 heartbeat 시간
    - get_age(component): 경과 시간 (초)
    - is_alive(component, max_age): 활성 여부 확인
    
    **사용 예시**:
    ```python
    heartbeat = HeartbeatMonitor()
    heartbeat.start()
    
    # Heartbeat 업데이트
    heartbeat.update('engine')
    heartbeat.update('websocket')
    
    # 활성 여부 확인
    if heartbeat.is_alive('engine', max_age=60.0):
        print("Engine is alive")
    
    # 경과 시간
    age = heartbeat.get_age('websocket')
    print(f"WebSocket last heartbeat: {age:.1f}s ago")
    ```
    """
    
    def __init__(self):
        super().__init__(name='heartbeat')
        self._heartbeats: Dict[str, float] = {}
    
    def update(self, component: str):
        """
        Heartbeat 업데이트
        
        Args:
            component: 컴포넌트 이름 (예: 'engine', 'websocket')
        """
        self._heartbeats[component] = time.time()
    
    def get_last_heartbeat(self, component: str) -> Optional[float]:
        """
        마지막 heartbeat 시간 반환
        
        Args:
            component: 컴포넌트 이름
        
        Returns:
            float: timestamp (seconds since epoch) 또는 None
        """
        return self._heartbeats.get(component)
    
    def get_age(self, component: str) -> Optional[float]:
        """
        마지막 heartbeat 이후 경과 시간 (초)
        
        Args:
            component: 컴포넌트 이름
        
        Returns:
            float: 경과 시간 (초) 또는 None
        """
        last_hb = self.get_last_heartbeat(component)
        if last_hb is None:
            return None
        return time.time() - last_hb
    
    def is_alive(self, component: str, max_age: float = 60.0) -> bool:
        """
        컴포넌트 활성 여부 확인
        
        Args:
            component: 컴포넌트 이름
            max_age: 최대 허용 경과 시간 (초)
        
        Returns:
            bool: True if alive (경과 시간 < max_age)
        """
        age = self.get_age(component)
        if age is None:
            return False
        return age < max_age
    
    def get_all_components(self) -> list:
        """등록된 모든 컴포넌트 목록"""
        return list(self._heartbeats.keys())
    
    def get_status(self) -> Dict[str, Any]:
        """
        현재 상태 반환
        
        Returns:
            Dict: {
                'components': {'engine': 1700123456.789, ...},
                'ages': {'engine': 5.2, ...}
            }
        """
        now = time.time()
        return {
            'components': dict(self._heartbeats),
            'ages': {
                comp: now - ts
                for comp, ts in self._heartbeats.items()
            }
        }
    
    def __repr__(self) -> str:
        return f"HeartbeatMonitor(components={list(self._heartbeats.keys())})"
