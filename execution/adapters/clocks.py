#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clock Adapters
==============
시간 제공자 인터페이스

- SimClock: 백테스트 (데이터의 시간 사용)
- LiveClock: 실시간 (현재 시각)
"""
import time
from common.logger import setup_logger

logger = setup_logger(__name__)


class SimClock:
    """
    백테스트용 시계
    데이터의 timestamp를 시간으로 사용
    """
    
    def __init__(self):
        self.current_time = 0
        logger.info(f"✅ SimClock 초기화")
    
    def update(self, candle_time: int):
        """
        캔들 시간으로 업데이트
        
        Args:
            candle_time: unix milliseconds
        """
        self.current_time = candle_time
    
    def now(self) -> int:
        """
        현재 시각 반환
        
        Returns:
            unix milliseconds
        """
        return self.current_time


class LiveClock:
    """
    실시간 시계
    시스템 현재 시각 사용
    """
    
    def __init__(self):
        logger.info(f"✅ LiveClock 초기화")
    
    def update(self, candle_time: int):
        """업데이트 불필요 (실시간이므로)"""
        pass
    
    def now(self) -> int:
        """
        현재 시각 반환
        
        Returns:
            unix milliseconds
        """
        return int(time.time() * 1000)
