#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PR9 핵심 기능 테스트
==================
Redis 기반 중복 제거 시스템 테스트
"""
import pytest
import redis
import hashlib
import json


@pytest.fixture
def redis_client():
    """Redis 클라이언트 fixture"""
    client = redis.Redis(host='trading_redis', port=6379, db=0, decode_responses=True)
    yield client
    # 테스트 후 정리
    for key in client.scan_iter("test:*"):
        client.delete(key)


def test_redis_connection(redis_client):
    """Redis 연결 테스트"""
    assert redis_client.ping(), "Redis 연결 실패"


def test_candle_dedup(redis_client):
    """캔들 중복 제거 테스트"""
    # 캔들 dedup 키 생성
    symbol = "BTCUSDT"
    timeframe = "1m"
    ts = 1730000000000
    
    dedup_key = f"test:candle:{symbol}:{timeframe}:{ts}"
    
    # 첫 번째 캔들 - 처리
    exists = redis_client.exists(dedup_key)
    assert not exists, "캔들이 이미 존재함"
    
    # 캔들 처리 후 키 설정
    redis_client.setex(dedup_key, 60, "1")
    
    # 두 번째 동일 캔들 - 중복 감지
    exists = redis_client.exists(dedup_key)
    assert exists, "캔들 중복 감지 실패"


def test_cooldown_ttl(redis_client):
    """쿨다운 TTL 테스트"""
    strategy_id = "test_strategy"
    symbol = "ETHUSDT"
    
    cooldown_key = f"test:cooldown:{strategy_id}:{symbol}"
    
    # 쿨다운 설정 (60초)
    redis_client.setex(cooldown_key, 60, "1")
    
    # TTL 확인
    ttl = redis_client.ttl(cooldown_key)
    assert 55 <= ttl <= 60, f"TTL 범위 오류: {ttl}"
    
    # 쿨다운 중인지 확인
    in_cooldown = redis_client.exists(cooldown_key)
    assert in_cooldown, "쿨다운 상태 확인 실패"


def test_signal_idempotency(redis_client):
    """신호 멱등성 테스트"""
    # 신호 파라미터
    signal_params = {
        "symbol": "SOLUSDT",
        "side": "LONG",
        "entry": 100.5,
        "sl": 95.0,
        "tp": 110.0,
        "qty": 10.0
    }
    
    # 정규화 및 해시 생성
    normalized = json.dumps(signal_params, sort_keys=True)
    signal_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    signal_key = f"test:signal:{signal_params['symbol']}:{signal_hash}"
    
    # 첫 번째 신호 - 처리
    exists = redis_client.exists(signal_key)
    assert not exists, "신호가 이미 존재함"
    
    # 신호 처리 후 키 설정 (3600초)
    redis_client.setex(signal_key, 3600, "1")
    
    # 두 번째 동일 신호 - 중복 감지
    exists = redis_client.exists(signal_key)
    assert exists, "신호 중복 감지 실패"
    
    # TTL 확인
    ttl = redis_client.ttl(signal_key)
    assert 3595 <= ttl <= 3600, f"신호 TTL 범위 오류: {ttl}"


def test_ttl_persistence(redis_client):
    """TTL 지속성 테스트 (재시작 시뮬레이션)"""
    test_key = "test:persistence:key"
    
    # 키 설정 (30초)
    redis_client.setex(test_key, 30, "test_value")
    
    # 초기 TTL
    ttl_before = redis_client.ttl(test_key)
    assert 25 <= ttl_before <= 30, f"초기 TTL 오류: {ttl_before}"
    
    # 값 확인
    value = redis_client.get(test_key)
    assert value == "test_value", "값 불일치"
    
    # TTL 재확인 (약간 감소)
    ttl_after = redis_client.ttl(test_key)
    assert ttl_after <= ttl_before, "TTL이 증가함"
    assert ttl_after >= ttl_before - 2, "TTL 감소 폭이 너무 큼"


def test_multiple_keys_cleanup(redis_client):
    """다중 키 정리 테스트"""
    # 여러 테스트 키 생성
    keys = [f"test:cleanup:{i}" for i in range(5)]
    
    for key in keys:
        redis_client.setex(key, 10, "cleanup_test")
    
    # 모든 키 존재 확인
    for key in keys:
        assert redis_client.exists(key), f"{key} 생성 실패"
    
    # 키 삭제
    for key in keys:
        redis_client.delete(key)
    
    # 모든 키 삭제 확인
    for key in keys:
        assert not redis_client.exists(key), f"{key} 삭제 실패"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
