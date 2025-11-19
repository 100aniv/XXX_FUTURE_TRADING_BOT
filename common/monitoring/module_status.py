#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Status
=============
PHASE18-4: 모듈별 상태 집계 및 리포트
"""
import time
from typing import Dict, Any, Optional
from enum import Enum
from common.monitoring import BaseMonitor


class StatusLevel(str, Enum):
    """상태 레벨"""
    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class ModuleStatus(BaseMonitor):
    """
    모듈별 상태 집계 및 리포트
    
    **상태 레벨**:
    - OK: 정상
    - WARNING: 경고 (일부 지연/경고)
    - CRITICAL: 심각 (연결 끊김, 장애)
    
    **사용 예시**:
    ```python
    status = ModuleStatus()
    status.start()
    
    # 상태 설정
    status.set_status('engine', StatusLevel.OK)
    status.set_status('websocket', StatusLevel.WARNING, "지연 발생")
    status.set_status('redis', StatusLevel.CRITICAL, "연결 끊김")
    
    # 상태 조회
    engine_status = status.get_status('engine')
    # {'level': 'OK', 'message': '', 'timestamp': 1700123456.789}
    
    # 전체 상태
    all_status = status.get_all_status()
    
    # 전체 시스템 정상 여부
    if status.is_healthy():
        print("All modules OK")
    ```
    """
    
    def __init__(self):
        super().__init__(name='module_status')
        # {module_name: {'level': StatusLevel, 'message': str, 'timestamp': float}}
        self._statuses: Dict[str, Dict[str, Any]] = {}
    
    def set_status(self, 
                   module: str, 
                   level: StatusLevel, 
                   message: str = ""):
        """
        모듈 상태 설정
        
        Args:
            module: 모듈 이름 (예: 'engine', 'websocket')
            level: StatusLevel (OK, WARNING, CRITICAL)
            message: 상태 메시지 (선택적)
        """
        self._statuses[module] = {
            'level': level,
            'message': message,
            'timestamp': time.time()
        }
    
    def get_module_status(self, module: str) -> Optional[Dict[str, Any]]:
        """
        모듈 상태 조회
        
        Args:
            module: 모듈 이름
        
        Returns:
            Dict: {'level', 'message', 'timestamp'} 또는 None
        """
        return self._statuses.get(module)
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """
        전체 모듈 상태 조회
        
        Returns:
            Dict[str, Dict]: {module_name: status_dict}
        """
        return dict(self._statuses)
    
    def is_healthy(self) -> bool:
        """
        전체 시스템 정상 여부
        
        Returns:
            bool: True if no WARNING or CRITICAL
        """
        for status in self._statuses.values():
            if status['level'] in [StatusLevel.WARNING, StatusLevel.CRITICAL]:
                return False
        return True
    
    def get_critical_modules(self) -> list:
        """CRITICAL 상태 모듈 목록"""
        return [
            mod for mod, status in self._statuses.items()
            if status['level'] == StatusLevel.CRITICAL
        ]
    
    def get_warning_modules(self) -> list:
        """WARNING 상태 모듈 목록"""
        return [
            mod for mod, status in self._statuses.items()
            if status['level'] == StatusLevel.WARNING
        ]
    
    def clear_status(self, module: Optional[str] = None):
        """
        상태 초기화
        
        Args:
            module: 특정 모듈만 초기화 (None이면 전체 초기화)
        """
        if module:
            if module in self._statuses:
                del self._statuses[module]
        else:
            self._statuses.clear()
    
    def get_summary(self) -> Dict[str, int]:
        """
        상태 요약
        
        Returns:
            Dict: {'ok': 3, 'warning': 1, 'critical': 0}
        """
        summary = {
            'ok': 0,
            'warning': 0,
            'critical': 0
        }
        for status in self._statuses.values():
            level = status['level'].lower()
            if level in summary:
                summary[level] += 1
        return summary
    
    def get_status(self) -> Dict[str, Any]:
        """
        현재 상태 반환 (BaseMonitor 인터페이스)
        
        Returns:
            Dict: {
                'statuses': {...},
                'summary': {...},
                'healthy': True/False
            }
        """
        return {
            'statuses': self.get_all_status(),
            'summary': self.get_summary(),
            'healthy': self.is_healthy()
        }
    
    def __repr__(self) -> str:
        summary = self.get_summary()
        return (
            f"ModuleStatus(ok={summary['ok']}, warning={summary['warning']}, "
            f"critical={summary['critical']})"
        )
