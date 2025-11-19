#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Health Checker
==============
PHASE18-4: 시스템 전반의 헬스 상태 확인
"""
import time
from typing import Dict, Any, Optional
from common.monitoring import BaseMonitor
from common.logger import setup_logger

logger = setup_logger(__name__)


class HealthChecker(BaseMonitor):
    """
    시스템 전반의 헬스 상태 확인
    
    **체크 항목**:
    - Redis 연결 상태
    - DB 연결 상태
    - 시스템 uptime
    
    **사용 예시**:
    ```python
    health = HealthChecker(config)
    health.start()
    
    # 전체 헬스 체크
    status = health.check_all()
    # {'redis': True, 'db': True, 'uptime': 123.45}
    
    # 개별 체크
    if health.check_redis():
        print("Redis OK")
    ```
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(name='health')
        self.config = config
        self.start_time = time.time()
        self._redis_client = None
        self._db_conn = None
    
    def check_redis(self) -> bool:
        """
        Redis 연결 확인
        
        Returns:
            bool: True if connected
        """
        try:
            import redis
            redis_config = self.config.get('monitoring', {}).get('redis', {})
            host = redis_config.get('host', 'localhost')
            port = redis_config.get('port', 6379)
            
            r = redis.Redis(host=host, port=port, decode_responses=True, socket_timeout=1.0)
            r.ping()
            return True
        except Exception as e:
            logger.debug(f"Redis 헬스 체크 실패: {e}")
            return False
    
    def check_db(self) -> bool:
        """
        DB 연결 확인
        
        Returns:
            bool: True if connected
        """
        try:
            from common.database import get_db_connection
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    return result is not None
        except Exception as e:
            logger.debug(f"DB 헬스 체크 실패: {e}")
            return False
    
    def get_uptime(self) -> float:
        """
        시스템 uptime (초)
        
        Returns:
            float: uptime in seconds
        """
        return time.time() - self.start_time
    
    def check_all(self) -> Dict[str, Any]:
        """
        전체 헬스 체크
        
        Returns:
            Dict: {
                'redis': True/False,
                'db': True/False,
                'uptime': 123.45
            }
        """
        return {
            'redis': self.check_redis(),
            'db': self.check_db(),
            'uptime': self.get_uptime()
        }
    
    def is_healthy(self) -> bool:
        """
        전체 시스템 정상 여부
        
        Returns:
            bool: True if all checks pass
        """
        status = self.check_all()
        return status['redis'] and status['db']
    
    def get_status(self) -> Dict[str, Any]:
        """
        현재 상태 반환
        
        Returns:
            Dict: check_all() 결과 + is_healthy
        """
        status = self.check_all()
        status['healthy'] = self.is_healthy()
        return status
    
    def __repr__(self) -> str:
        return f"HealthChecker(healthy={self.is_healthy()})"
