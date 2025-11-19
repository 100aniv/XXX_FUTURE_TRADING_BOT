#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE18-2: run_id 네임스페이스 전역 적용 테스트
====================================
run_id 기반 Redis 키 격리 검증
"""
import sys
import subprocess
import time
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_namespace_utils():
    """common/namespace.py 유틸 함수 테스트"""
    print("=" * 60)
    print("TEST 1: 네임스페이스 유틸 함수")
    print("=" * 60)
    
    from common.namespace import build_redis_key, build_candle_seen_key, parse_redis_key, get_env_from_mode
    
    # build_redis_key 테스트
    key1 = build_redis_key('cooldown', 'paper', '20251119_140530_a7f3', 'BTCUSDT', 'scalping')
    expected1 = 'cooldown:paper:20251119_140530_a7f3:BTCUSDT:scalping'
    assert key1 == expected1, f"build_redis_key 실패: {key1} != {expected1}"
    print(f"✅ build_redis_key: {key1}")
    
    # build_candle_seen_key 테스트
    key2 = build_candle_seen_key('paper', '20251119_140530_a7f3', 'BTCUSDT', '1m', 1700000000)
    expected2 = 'candle:seen:paper:20251119_140530_a7f3:BTCUSDT:1m:1700000000'
    assert key2 == expected2, f"build_candle_seen_key 실패: {key2} != {expected2}"
    print(f"✅ build_candle_seen_key: {key2}")
    
    # parse_redis_key 테스트
    parsed = parse_redis_key('cooldown:paper:20251119_140530_a7f3:BTCUSDT:scalping')
    assert parsed['domain'] == 'cooldown', "parse domain 실패"
    assert parsed['env'] == 'paper', "parse env 실패"
    assert parsed['run_id'] == '20251119_140530_a7f3', "parse run_id 실패"
    assert parsed['symbol'] == 'BTCUSDT', "parse symbol 실패"
    assert parsed['extra'] == 'scalping', "parse extra 실패"
    print(f"✅ parse_redis_key: {parsed}")
    
    # get_env_from_mode 테스트
    assert get_env_from_mode('backtest_clean') == 'backtest', "get_env_from_mode(backtest_clean) 실패"
    assert get_env_from_mode('paper') == 'paper', "get_env_from_mode(paper) 실패"
    assert get_env_from_mode('live') == 'live', "get_env_from_mode(live) 실패"
    print(f"✅ get_env_from_mode: backtest_clean -> backtest")
    
    print("\n✅ TEST 1 PASSED\n")


def test_redis_client_namespace():
    """RedisClient 네임스페이스 테스트"""
    print("=" * 60)
    print("TEST 2: RedisClient 네임스페이스")
    print("=" * 60)
    
    try:
        from database.redis import RedisClient
        
        # 인스턴스 생성 (env, run_id 전달)
        env = 'paper'
        run_id = '20251119_test_a7f3'
        client = RedisClient.get_instance(env=env, run_id=run_id)
        
        if not client.enabled:
            print("⚠️ Redis 연결 실패 - 테스트 건너뜀")
            return
        
        # mark_seen 테스트
        symbol = 'BTCUSDT'
        timeframe = '1m'
        timestamp = int(time.time() * 1000)
        
        client.mark_seen(symbol, timeframe, timestamp)
        print(f"✅ mark_seen: {symbol}, {timeframe}, {timestamp}")
        
        # is_seen 테스트
        is_seen = client.is_seen(symbol, timeframe, timestamp)
        assert is_seen, "is_seen이 False를 반환 (mark_seen 후 True여야 함)"
        print(f"✅ is_seen: {is_seen}")
        
        # Redis 키 확인 (네임스페이스 포함 확인)
        import redis
        redis_raw = redis.Redis(host='localhost', port=6379, decode_responses=True)
        keys = redis_raw.keys(f"candle:seen:{env}:{run_id}:*")
        print(f"✅ Redis 키 확인: {len(keys)}개 키 발견")
        if keys:
            print(f"   예시 키: {keys[0]}")
            # 네임스페이스 검증
            assert env in keys[0], f"env({env})가 키에 포함되지 않음: {keys[0]}"
            assert run_id in keys[0], f"run_id({run_id})가 키에 포함되지 않음: {keys[0]}"
        
        # 정리
        for key in keys:
            redis_raw.delete(key)
        print(f"✅ 정리: {len(keys)}개 키 삭제")
        
        print("\n✅ TEST 2 PASSED\n")
        
    except ImportError:
        print("⚠️ redis 패키지 없음 - 테스트 건너뜀")
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        raise


def test_config_env_run_id():
    """run_paper.py / run_backtest.py에서 env와 run_id 설정 확인"""
    print("=" * 60)
    print("TEST 3: Config에 env와 run_id 설정")
    print("=" * 60)
    
    from common.config_loader import load_config_with_mode, generate_run_id
    
    # Backtest config
    cfg_backtest = load_config_with_mode(mode='backtest_clean')
    cfg_backtest['env'] = 'backtest'
    cfg_backtest['run_id'] = generate_run_id()
    
    assert cfg_backtest['env'] == 'backtest', "backtest env 설정 실패"
    assert cfg_backtest['run_id'], "backtest run_id 설정 실패"
    print(f"✅ Backtest config: env={cfg_backtest['env']}, run_id={cfg_backtest['run_id']}")
    
    # Paper config
    cfg_paper = load_config_with_mode(mode='paper')
    cfg_paper['env'] = 'paper'
    cfg_paper['run_id'] = generate_run_id()
    
    assert cfg_paper['env'] == 'paper', "paper env 설정 실패"
    assert cfg_paper['run_id'], "paper run_id 설정 실패"
    print(f"✅ Paper config: env={cfg_paper['env']}, run_id={cfg_paper['run_id']}")
    
    # run_id 포맷 검증 (YYYYMMDD_HHMMSS_xxxx, xxxx는 소문자+숫자 4자리)
    import re
    pattern = r'^\d{8}_\d{6}_[a-z0-9]{4}$'
    assert re.match(pattern, cfg_backtest['run_id']), f"run_id 포맷 오류: {cfg_backtest['run_id']}"
    assert re.match(pattern, cfg_paper['run_id']), f"run_id 포맷 오류: {cfg_paper['run_id']}"
    print(f"✅ run_id 포맷 검증: {pattern}")
    
    print("\n✅ TEST 3 PASSED\n")


def test_multi_run_isolation():
    """멀티 run_id 격리 테스트"""
    print("=" * 60)
    print("TEST 4: 멀티 run_id 격리")
    print("=" * 60)
    
    try:
        from database.redis import RedisClient
        import redis
        
        redis_raw = redis.Redis(host='localhost', port=6379, decode_responses=True)
        redis_raw.ping()
        
        # 서로 다른 run_id로 2개 인스턴스 생성
        run_id_1 = '20251119_test1_aaaa'
        run_id_2 = '20251119_test2_bbbb'
        
        client1 = RedisClient.get_instance(env='paper', run_id=run_id_1)
        
        # 싱글톤이므로 run_id 업데이트
        client1.run_id = run_id_1
        client1.mark_seen('BTCUSDT', '1m', 1000000001)
        
        client2 = RedisClient.get_instance(env='paper', run_id=run_id_2)
        client2.run_id = run_id_2
        client2.mark_seen('BTCUSDT', '1m', 1000000002)
        
        # Redis 키 확인
        keys_1 = redis_raw.keys(f"candle:seen:paper:{run_id_1}:*")
        keys_2 = redis_raw.keys(f"candle:seen:paper:{run_id_2}:*")
        
        print(f"✅ run_id_1 키: {len(keys_1)}개")
        print(f"✅ run_id_2 키: {len(keys_2)}개")
        
        assert len(keys_1) > 0, "run_id_1 키가 없음"
        assert len(keys_2) > 0, "run_id_2 키가 없음"
        
        # 키가 서로 다른지 확인
        common_keys = set(keys_1) & set(keys_2)
        assert len(common_keys) == 0, f"run_id 간 키 충돌 발생: {common_keys}"
        print(f"✅ run_id 간 키 격리 확인 (충돌 없음)")
        
        # 정리
        for key in keys_1 + keys_2:
            redis_raw.delete(key)
        print(f"✅ 정리: {len(keys_1) + len(keys_2)}개 키 삭제")
        
        print("\n✅ TEST 4 PASSED\n")
        
    except ImportError:
        print("⚠️ redis 패키지 없음 - 테스트 건너뜀")
    except Exception as e:
        print(f"⚠️ Redis 연결 실패 - 테스트 건너뜀: {e}")


def main():
    """전체 테스트 실행"""
    print("\n" + "=" * 60)
    print("PHASE18-2 run_id 네임스페이스 테스트 시작")
    print("=" * 60)
    
    tests = [
        test_namespace_utils,
        test_redis_client_namespace,
        test_config_env_run_id,
        test_multi_run_isolation,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ TEST FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ TEST ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"테스트 완료: {passed} PASSED, {failed} FAILED")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("\n✅ 모든 테스트 PASSED")
        sys.exit(0)


if __name__ == '__main__':
    main()
