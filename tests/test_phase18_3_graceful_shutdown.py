#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE18-3: Graceful Shutdown & Signal Handling 테스트
===================================================
Runtime Context, Signal Handling, Resource Cleanup 검증
"""
import sys
import threading
import time
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_runtime_context():
    """Runtime Context 동작 테스트"""
    print("=" * 60)
    print("TEST 1: RuntimeContext 동작")
    print("=" * 60)
    
    from common.runtime_context import RuntimeContext
    
    # 1. 생성 및 초기 상태
    runtime_ctx = RuntimeContext()
    assert not runtime_ctx.is_shutdown_requested(), "초기 상태는 shutdown=False여야 함"
    print("✅ 초기 상태: shutdown=False")
    
    # 2. Shutdown 요청
    reason = runtime_ctx.request_shutdown(reason="TEST_SIGNAL")
    assert runtime_ctx.is_shutdown_requested(), "shutdown 요청 후 True여야 함"
    assert reason == "TEST_SIGNAL", f"반환된 reason이 일치하지 않음: {reason}"
    print(f"✅ Shutdown 요청: {reason}")
    
    # 3. Shutdown 사유 확인
    saved_reason = runtime_ctx.get_shutdown_reason()
    assert saved_reason == "TEST_SIGNAL", f"저장된 reason이 일치하지 않음: {saved_reason}"
    print(f"✅ Shutdown 사유 확인: {saved_reason}")
    
    # 4. Clear (테스트용)
    runtime_ctx.clear_shutdown()
    assert not runtime_ctx.is_shutdown_requested(), "clear 후 shutdown=False여야 함"
    print("✅ Clear 후 상태: shutdown=False")
    
    # 5. run_id, env 설정
    runtime_ctx.run_id = "20251119_test_abcd"
    runtime_ctx.env = "paper"
    assert runtime_ctx.run_id == "20251119_test_abcd", "run_id 설정 실패"
    assert runtime_ctx.env == "paper", "env 설정 실패"
    print(f"✅ Metadata: run_id={runtime_ctx.run_id}, env={runtime_ctx.env}")
    
    print("\n✅ TEST 1 PASSED\n")


def test_shutdown_event_threading():
    """Shutdown Event Threading 테스트"""
    print("=" * 60)
    print("TEST 2: Shutdown Event Threading")
    print("=" * 60)
    
    from common.runtime_context import RuntimeContext
    
    runtime_ctx = RuntimeContext()
    results = []
    
    def worker_thread():
        """Worker thread - shutdown 체크 루프"""
        for i in range(100):
            if runtime_ctx.is_shutdown_requested():
                results.append(f"Worker stopped at iteration {i}")
                break
            time.sleep(0.01)
        else:
            results.append("Worker completed (no shutdown)")
    
    # Worker 시작
    worker = threading.Thread(target=worker_thread)
    worker.start()
    
    # 0.3초 후 shutdown 요청
    time.sleep(0.3)
    runtime_ctx.request_shutdown(reason="Test Thread Shutdown")
    
    # Worker 종료 대기
    worker.join(timeout=2.0)
    assert not worker.is_alive(), "Worker thread가 종료되지 않음"
    
    # 결과 확인
    assert len(results) == 1, f"결과 개수가 1이 아님: {len(results)}"
    assert "Worker stopped" in results[0], f"Worker가 정상적으로 종료되지 않음: {results[0]}"
    print(f"✅ Worker thread: {results[0]}")
    
    print("\n✅ TEST 2 PASSED\n")


def test_websocket_collector_stop():
    """WebSocketCollector stop() 개선 테스트"""
    print("=" * 60)
    print("TEST 3: WebSocketCollector stop()")
    print("=" * 60)
    
    try:
        from collectors.websocket_collector import WebSocketCollector
        
        # 최소 설정으로 collector 생성 (실제 연결은 하지 않음)
        collector = WebSocketCollector(
            symbols=["BTCUSDT"],
            timeframe="1m",
            enable_dedup=False,
            enable_backfill=False,
            env='paper',
            run_id='test_shutdown'
        )
        
        # stop() 호출 (실제 WebSocket 없이도 정상 작동해야 함)
        collector.stop(timeout=1.0)
        
        # running 플래그 확인
        assert not collector.running, "stop() 후 running=False여야 함"
        print("✅ stop() 호출 성공: running=False")
        
        print("\n✅ TEST 3 PASSED\n")
        
    except ImportError as e:
        print(f"⚠️  WebSocketCollector import 실패 (의존성 없음): {e}")
        print("⚠️  TEST 3 SKIPPED\n")
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        raise


def test_config_injection():
    """Config에 RuntimeContext 주입 테스트"""
    print("=" * 60)
    print("TEST 4: Config Runtime Context 주입")
    print("=" * 60)
    
    from common.runtime_context import RuntimeContext
    
    # Config mock
    config = {
        'mode': 'paper',
        'symbol': 'BTCUSDT',
        'run_id': '20251119_test_1234',
        'env': 'paper'
    }
    
    # RuntimeContext 생성 및 주입
    runtime_ctx = RuntimeContext()
    runtime_ctx.run_id = config['run_id']
    runtime_ctx.env = config['env']
    config['runtime_context'] = runtime_ctx
    
    # Config에서 추출
    extracted_ctx = config.get('runtime_context')
    assert extracted_ctx is not None, "Config에서 runtime_context 추출 실패"
    assert extracted_ctx.run_id == '20251119_test_1234', "run_id 불일치"
    assert extracted_ctx.env == 'paper', "env 불일치"
    print(f"✅ Config 주입 성공: {extracted_ctx}")
    
    # Shutdown 요청 전파 테스트
    extracted_ctx.request_shutdown(reason="TEST_CONFIG")
    assert config['runtime_context'].is_shutdown_requested(), "Shutdown 요청 전파 실패"
    print("✅ Shutdown 요청 전파 성공")
    
    print("\n✅ TEST 4 PASSED\n")


def test_engine_shutdown_simulation():
    """Engine shutdown 체크 시뮬레이션"""
    print("=" * 60)
    print("TEST 5: Engine Shutdown 시뮬레이션")
    print("=" * 60)
    
    from common.runtime_context import RuntimeContext
    
    # Fake config
    config = {
        'runtime_context': RuntimeContext()
    }
    runtime_ctx = config['runtime_context']
    
    # Fake candle feed (generator)
    def fake_feed():
        for i in range(100):
            yield {'symbol': 'BTCUSDT', 'close': 50000 + i}
    
    # Engine 메인 루프 시뮬레이션
    candles_processed = 0
    for candle in fake_feed():
        # Shutdown 체크 (Engine과 동일한 로직)
        if runtime_ctx and runtime_ctx.is_shutdown_requested():
            reason = runtime_ctx.get_shutdown_reason()
            print(f"🛑 Shutdown requested ({reason}) - 루프 종료")
            break
        
        # 가짜 처리
        candles_processed += 1
        
        # 30번째 캔들에서 shutdown 요청
        if candles_processed == 30:
            runtime_ctx.request_shutdown(reason="Simulation Test")
    
    # 결과 확인
    assert candles_processed == 30, f"캔들 처리 개수가 30이 아님: {candles_processed}"
    print(f"✅ Engine 루프 시뮬레이션: 30개 캔들 처리 후 정상 종료")
    
    print("\n✅ TEST 5 PASSED\n")


def main():
    """전체 테스트 실행"""
    print("\n" + "=" * 60)
    print("PHASE18-3 Graceful Shutdown 테스트 시작")
    print("=" * 60)
    
    tests = [
        test_runtime_context,
        test_shutdown_event_threading,
        test_websocket_collector_stop,
        test_config_injection,
        test_engine_shutdown_simulation,
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
