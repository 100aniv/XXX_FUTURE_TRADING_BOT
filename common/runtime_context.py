#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Runtime Context
===============
PHASE18-3: 실행 시점 공용 컨텍스트
PHASE18-4: 모니터링 레지스트리 추가

- shutdown_event: Graceful Shutdown 플래그
- run_id: 실행 인스턴스 ID
- env: 실행 환경 (backtest, paper, live)
- monitor_registry: 모니터링 시스템 레지스트리 (PHASE18-4)
"""
import threading
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from common.monitoring import MonitorRegistry


class RuntimeContext:
    """
    실행 시점 공용 컨텍스트
    
    **기능**:
    - Graceful Shutdown 요청 관리
    - 실행 메타데이터 (run_id, env) 보유
    
    **사용 예시**:
    ```python
    # Runner에서 생성
    runtime_ctx = RuntimeContext()
    runtime_ctx.run_id = '20251119_140530_a7f3'
    runtime_ctx.env = 'paper'
    
    # Config에 주입
    config['runtime_context'] = runtime_ctx
    
    # Signal Handler에서 shutdown 요청
    runtime_ctx.request_shutdown(reason="SIGINT")
    
    # Engine/Collector에서 체크
    if runtime_ctx.is_shutdown_requested():
        break  # 메인 루프 탈출
    ```
    """
    
    def __init__(self):
        """Runtime Context 초기화"""
        self.shutdown_event = threading.Event()
        self.run_id: Optional[str] = None
        self.env: Optional[str] = None
        self._shutdown_reason: Optional[str] = None
        
        # ⭐ PHASE18-4: 모니터링 레지스트리
        self.monitor_registry: Optional['MonitorRegistry'] = None
    
    def request_shutdown(self, reason: str = "Unknown") -> str:
        """
        Graceful Shutdown 요청
        
        Args:
            reason: 종료 사유 (예: "SIGINT", "SIGTERM", "Duration")
        
        Returns:
            str: 종료 사유
        """
        self._shutdown_reason = reason
        self.shutdown_event.set()
        return reason
    
    def is_shutdown_requested(self) -> bool:
        """
        Shutdown 요청 여부 확인
        
        Returns:
            bool: True if shutdown requested
        """
        return self.shutdown_event.is_set()
    
    def get_shutdown_reason(self) -> Optional[str]:
        """
        Shutdown 사유 반환
        
        Returns:
            Optional[str]: 종료 사유 또는 None
        """
        return self._shutdown_reason
    
    def clear_shutdown(self):
        """Shutdown 플래그 초기화 (테스트용)"""
        self.shutdown_event.clear()
        self._shutdown_reason = None
    
    def __repr__(self) -> str:
        return (
            f"RuntimeContext(run_id={self.run_id}, env={self.env}, "
            f"shutdown={'REQUESTED' if self.is_shutdown_requested() else 'NORMAL'})"
        )
    
    def __getstate__(self):
        """Pickle/deepcopy 지원: threading.Event 및 monitor_registry 제외"""
        state = self.__dict__.copy()
        # threading.Event는 직렬화 불가이므로 제외
        state.pop('shutdown_event', None)
        # ⭐ PHASE18-4: monitor_registry도 직렬화 불가 (복잡한 객체 트리)
        state.pop('monitor_registry', None)
        return state
    
    def __setstate__(self, state):
        """Pickle/deepcopy 복원: threading.Event 재생성"""
        self.__dict__.update(state)
        # threading.Event 재생성
        self.shutdown_event = threading.Event()
        # shutdown 상태 복원
        if self._shutdown_reason:
            self.shutdown_event.set()
    
    def __deepcopy__(self, memo):
        """deepcopy 지원: 새 인스턴스 생성 (threading.Event는 공유 안 함)"""
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        # 기본 필드 복사
        result.run_id = self.run_id
        result.env = self.env
        result._shutdown_reason = self._shutdown_reason
        # threading.Event는 새로 생성
        result.shutdown_event = threading.Event()
        if self.is_shutdown_requested():
            result.shutdown_event.set()
        # ⭐ PHASE18-4: monitor_registry는 원본 참조 (공유)
        result.monitor_registry = self.monitor_registry
        return result
