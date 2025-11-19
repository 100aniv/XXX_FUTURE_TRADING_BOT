#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE18-2: Redis/DB 네임스페이스 유틸
======================================
run_id 기반 키 생성 표준화

목표: 실행 간 Redis 키 격리를 통해 멀티 실행/멀티 봇 환경 지원
"""

def build_redis_key(domain: str, env: str, run_id: str, symbol: str, extra: str = None) -> str:
    """
    Redis 키 생성 (네임스페이스 표준)
    
    Args:
        domain: 키 도메인 (cooldown, candle_seen, signal 등)
        env: 실행 모드 (backtest, paper, live)
        run_id: 실행 인스턴스 ID
        symbol: 심볼 (BTCUSDT 등)
        extra: 추가 식별자 (strategy, timeframe 등)
    
    Returns:
        str: Redis 키 (예: cooldown:paper:20251119_140530_a7f3:BTCUSDT:scalping)
    
    Examples:
        >>> build_redis_key('cooldown', 'paper', '20251119_140530_a7f3', 'BTCUSDT', 'scalping')
        'cooldown:paper:20251119_140530_a7f3:BTCUSDT:scalping'
        
        >>> build_redis_key('signal', 'backtest', '20251119_140530_a7f3', 'ETHUSDT')
        'signal:backtest:20251119_140530_a7f3:ETHUSDT'
    """
    parts = [domain, env, run_id, symbol]
    if extra:
        parts.append(extra)
    
    return ':'.join(parts)


def build_candle_seen_key(env: str, run_id: str, symbol: str, timeframe: str, timestamp: int) -> str:
    """
    Candle dedup 키 생성
    
    Args:
        env: 실행 모드
        run_id: 실행 인스턴스 ID
        symbol: 심볼
        timeframe: 타임프레임 (1m, 3m, 5m 등)
        timestamp: 캔들 타임스탬프
    
    Returns:
        str: Redis 키 (예: candle:seen:paper:20251119_140530_a7f3:BTCUSDT:1m:1700000000)
    
    Examples:
        >>> build_candle_seen_key('paper', '20251119_140530_a7f3', 'BTCUSDT', '1m', 1700000000)
        'candle:seen:paper:20251119_140530_a7f3:BTCUSDT:1m:1700000000'
    """
    return f"candle:seen:{env}:{run_id}:{symbol}:{timeframe}:{timestamp}"


def parse_redis_key(key: str) -> dict:
    """
    Redis 키 파싱 (역변환)
    
    Args:
        key: Redis 키
    
    Returns:
        dict: 파싱 결과 (domain, env, run_id, symbol, extra)
    
    Examples:
        >>> parse_redis_key('cooldown:paper:20251119_140530_a7f3:BTCUSDT:scalping')
        {'domain': 'cooldown', 'env': 'paper', 'run_id': '20251119_140530_a7f3', 'symbol': 'BTCUSDT', 'extra': 'scalping'}
        
        >>> parse_redis_key('signal:backtest:20251119_140530_a7f3:ETHUSDT')
        {'domain': 'signal', 'env': 'backtest', 'run_id': '20251119_140530_a7f3', 'symbol': 'ETHUSDT', 'extra': None}
    """
    parts = key.split(':')
    
    result = {
        'domain': parts[0] if len(parts) > 0 else None,
        'env': parts[1] if len(parts) > 1 else None,
        'run_id': parts[2] if len(parts) > 2 else None,
        'symbol': parts[3] if len(parts) > 3 else None,
        'extra': ':'.join(parts[4:]) if len(parts) > 4 else None,
    }
    
    return result


def get_env_from_mode(mode: str) -> str:
    """
    mode → env 변환 (네임스페이스용)
    
    Args:
        mode: 실행 모드 (backtest_clean, paper, live 등)
    
    Returns:
        str: env (backtest, paper, live)
    
    Examples:
        >>> get_env_from_mode('backtest_clean')
        'backtest'
        
        >>> get_env_from_mode('paper')
        'paper'
        
        >>> get_env_from_mode('live')
        'live'
    """
    if 'backtest' in mode.lower():
        return 'backtest'
    elif 'paper' in mode.lower():
        return 'paper'
    elif 'live' in mode.lower():
        return 'live'
    else:
        return mode  # 그대로 반환
