#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis Client Module
===================
Redis 기반 캐싱 및 중복 제거

⚠️ 리팩토링: common/redis_client.py → database/redis.py (2025-11-02)

- RedisClient: Redis 연결 및 기본 작업
- 폴백: Redis 실패 시 메모리 모드 자동 전환
- TTL 자동 적용

⚠️ PHASE18-2: run_id 네임스페이스 적용 (2025-11-19)
- 실행 간 Redis 키 격리
- env + run_id 기반 네임스페이스
"""
from typing import Optional
import time

from common.logger import setup_logger
from common.namespace import build_candle_seen_key

logger = setup_logger('redis', log_type='application')


class RedisClient:
    """
    Redis 클라이언트 (싱글톤 패턴)
    
    **기능:**
    - 캔들 중복 제거 (seen_candles)
    - TTL 자동 적용
    - 재시작 시에도 데이터 유지
    - 분산 환경 지원
    - Redis 실패 시 메모리 폴백
    
    **사용 예:**
    ```python
    redis_client = RedisClient.get_instance()
    
    # 중복 체크
    if not redis_client.is_seen("BTCUSDT", "5m", 1234567890):
        redis_client.mark_seen("BTCUSDT", "5m", 1234567890)
        # 캔들 처리...
    ```
    """
    
    _instance = None
    _lock = None
    
    @classmethod
    def get_instance(cls, host: str = 'localhost', port: int = 6379, ttl_seconds: int = 3600,
                     env: str = 'paper', run_id: str = 'unknown'):
        """싱글톤 인스턴스 반환 (PHASE18-2: env/run_id 추가)"""
        if cls._instance is None:
            if cls._lock is None:
                import threading
                cls._lock = threading.Lock()
            
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(host, port, ttl_seconds, env, run_id)
        else:
            # 싱글톤이지만 env/run_id는 업데이트 가능
            cls._instance.env = env
            cls._instance.run_id = run_id
        
        return cls._instance
    
    def __init__(self, host: str = 'localhost', port: int = 6379, ttl_seconds: int = 3600,
                 env: str = 'paper', run_id: str = 'unknown'):
        """
        Redis 연결 초기화
        
        Args:
            host: Redis 호스트
            port: Redis 포트
            ttl_seconds: TTL (초, 기본 1시간)
            env: 실행 모드 (backtest, paper, live) - PHASE18-2
            run_id: 실행 인스턴스 ID - PHASE18-2
        """
        self.host = host
        self.port = port
        self.ttl_seconds = ttl_seconds
        self.env = env  # PHASE18-2
        self.run_id = run_id  # PHASE18-2
        self.enabled = False
        self.redis_client = None
        self._memory_cache = {}
        
        self._connect()
    
    def _connect(self):
        """Redis 연결 시도 (최대 3회 재시도)"""
        max_retries = 3
        retry_delay = 2  # 초
        
        for attempt in range(1, max_retries + 1):
            try:
                import redis
                self.redis_client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # 연결 테스트
                self.redis_client.ping()
                self.enabled = True
                logger.info(f"✅ Redis 연결 성공: {self.host}:{self.port} (TTL: {self.ttl_seconds}초)")
                return
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"⚠️ Redis 연결 실패 ({attempt}/{max_retries}): {e} - {retry_delay}초 후 재시도...")
                    time.sleep(retry_delay)
                else:
                    logger.warning(f"⚠️ Redis 연결 최종 실패 ({max_retries}회 시도), 메모리 모드로 폴백")
                    self.redis_client = None
                    self.enabled = False
    
    def is_seen(self, symbol: str, timeframe: str, closed_at: int) -> bool:
        """
        캔들이 이미 처리되었는지 확인
        
        Args:
            symbol: 심볼
            timeframe: 타임프레임
            closed_at: 캔들 닫힌 시간 (ms)
        
        Returns:
            bool: True이면 이미 처리됨
        """
        # PHASE18-2: run_id 네임스페이스 적용
        key = build_candle_seen_key(self.env, self.run_id, symbol, timeframe, closed_at)
        
        if self.enabled and self.redis_client:
            try:
                return self.redis_client.exists(key) > 0
            except Exception as e:
                logger.error(f"❌ Redis exists 실패: {e}")
                # 폴백: 메모리 체크
                return self._is_seen_memory(key)
        else:
            # 메모리 모드
            return self._is_seen_memory(key)
    
    def _is_seen_memory(self, key: str) -> bool:
        """메모리 기반 중복 체크 (폴백)"""
        if key in self._memory_cache:
            # TTL 체크
            ts = self._memory_cache[key]
            if time.time() - ts < self.ttl_seconds:
                return True
            else:
                # TTL 만료
                del self._memory_cache[key]
                return False
        return False
    
    def mark_seen(self, symbol: str, timeframe: str, closed_at: int) -> bool:
        """
        캔들을 처리됨으로 표시 (TTL 자동 적용)
        
        Args:
            symbol: 심볼
            timeframe: 타임프레임
            closed_at: 캔들 닫힌 시간 (ms)
        
        Returns:
            bool: 성공 여부
        """
        # PHASE18-2: run_id 네임스페이스 적용
        key = build_candle_seen_key(self.env, self.run_id, symbol, timeframe, closed_at)
        
        if self.enabled and self.redis_client:
            try:
                self.redis_client.setex(key, self.ttl_seconds, "1")
                return True
            except Exception as e:
                logger.error(f"❌ Redis setex 실패: {e}")
                # 폴백: 메모리에 저장
                self._mark_seen_memory(key)
                return False
        else:
            # 메모리 모드
            self._mark_seen_memory(key)
            return True
    
    def _mark_seen_memory(self, key: str):
        """메모리 기반 표시 (폴백)"""
        self._memory_cache[key] = time.time()
        
        # 메모리 정리 (1000개 초과 시)
        if len(self._memory_cache) > 1000:
            now = time.time()
            expired = [k for k, ts in self._memory_cache.items() 
                      if now - ts > self.ttl_seconds]
            for k in expired:
                del self._memory_cache[k]
            if expired:
                logger.debug(f"🗑️ 메모리 캐시 정리: {len(expired)}개 제거")
    
    def get(self, key: str) -> Optional[str]:
        """키 값 조회"""
        if self.enabled and self.redis_client:
            try:
                return self.redis_client.get(key)
            except Exception as e:
                logger.error(f"❌ Redis get 실패: {e}")
                return None
        return None
    
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """키 값 설정"""
        if self.enabled and self.redis_client:
            try:
                if ttl:
                    self.redis_client.setex(key, ttl, value)
                else:
                    self.redis_client.set(key, value)
                return True
            except Exception as e:
                logger.error(f"❌ Redis set 실패: {e}")
                return False
        return False
    
    def delete(self, key: str) -> bool:
        """키 삭제"""
        if self.enabled and self.redis_client:
            try:
                self.redis_client.delete(key)
                return True
            except Exception as e:
                logger.error(f"❌ Redis delete 실패: {e}")
                return False
        return False
    
    def close(self):
        """Redis 연결 종료"""
        if self.enabled and self.redis_client:
            try:
                self.redis_client.close()
                logger.info("🔌 Redis 연결 종료")
            except:
                pass
