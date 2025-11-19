#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE18-4: Monitoring Framework 테스트
====================================
MonitorRegistry, HeartbeatMonitor, Watchdog, LatencyMonitor, HealthChecker, ModuleStatus 검증
"""
import sys
import time
import threading
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_monitor_registry():
    """MonitorRegistry 동작 테스트"""
    print("=" * 60)
    print("TEST 1: MonitorRegistry")
    print("=" * 60)
    
    from common.monitoring import MonitorRegistry, BaseMonitor
    
    class DummyMonitor(BaseMonitor):
        def __init__(self, name):
            super().__init__(name)
            self.data = []
        
        def get_status(self):
            return {'data': self.data}
    
    registry = MonitorRegistry()
    
    # 모니터 등록
    mon1 = DummyMonitor('monitor1')
    mon2 = DummyMonitor('monitor2')
    registry.register('mon1', mon1)
    registry.register('mon2', mon2)
    
    # 가져오기
    assert registry.get('mon1') is mon1, "get() 실패"
    assert registry.get('mon2') is mon2, "get() 실패"
    print("✅ 모니터 등록 및 가져오기 성공")
    
    # 상태 조회
    status = registry.get_status()
    assert 'mon1' in status, "get_status() 키 누락"
    assert 'mon2' in status, "get_status() 키 누락"
    print(f"✅ 전체 상태 조회: {list(status.keys())}")
    
    # 모니터 해제
    registry.unregister('mon1')
    assert registry.get('mon1') is None, "unregister() 실패"
    print("✅ 모니터 해제 성공")
    
    # stop_all
    registry.stop_all()
    assert not mon2.is_running(), "stop_all() 실패"
    print("✅ stop_all() 성공")
    
    print("\n✅ TEST 1 PASSED\n")


def test_heartbeat_monitor():
    """HeartbeatMonitor 동작 테스트"""
    print("=" * 60)
    print("TEST 2: HeartbeatMonitor")
    print("=" * 60)
    
    from common.monitoring.heartbeat_monitor import HeartbeatMonitor
    
    heartbeat = HeartbeatMonitor()
    heartbeat.start()
    
    # Heartbeat 업데이트
    heartbeat.update('engine')
    heartbeat.update('websocket')
    time.sleep(0.1)
    
    # 활성 여부 확인
    assert heartbeat.is_alive('engine', max_age=1.0), "engine should be alive"
    assert heartbeat.is_alive('websocket', max_age=1.0), "websocket should be alive"
    print("✅ Heartbeat 업데이트 및 활성 체크 성공")
    
    # 경과 시간
    age = heartbeat.get_age('engine')
    assert age is not None and age < 0.5, f"age should be < 0.5s, got {age}"
    print(f"✅ Engine heartbeat age: {age:.3f}s")
    
    # 마지막 heartbeat 시간
    last_hb = heartbeat.get_last_heartbeat('engine')
    assert last_hb is not None, "last_heartbeat should not be None"
    print(f"✅ Last heartbeat: {last_hb}")
    
    # 전체 컴포넌트
    components = heartbeat.get_all_components()
    assert 'engine' in components, "engine should be in components"
    assert 'websocket' in components, "websocket should be in components"
    print(f"✅ 전체 컴포넌트: {components}")
    
    heartbeat.stop()
    print("\n✅ TEST 2 PASSED\n")


def test_watchdog():
    """Watchdog 동작 테스트"""
    print("=" * 60)
    print("TEST 3: Watchdog")
    print("=" * 60)
    
    from common.monitoring.heartbeat_monitor import HeartbeatMonitor
    from common.monitoring.watchdog import Watchdog
    
    heartbeat = HeartbeatMonitor()
    heartbeat.start()
    
    # Watchdog 시작 (짧은 체크 간격)
    watchdog = Watchdog(heartbeat, check_interval=0.5, max_age=1.0)
    watchdog.start()
    
    # 정상 heartbeat
    heartbeat.update('engine')
    time.sleep(0.7)  # 첫 체크 대기
    
    assert not watchdog.has_warnings(), "정상 heartbeat에서는 경고 없어야 함"
    print("✅ 정상 heartbeat - 경고 없음")
    
    # 오래된 heartbeat (경고 발생)
    time.sleep(1.5)  # max_age(1.0) 초과 대기
    
    # 경고 발생 확인 (watchdog이 체크할 때까지 대기)
    time.sleep(0.6)  # check_interval 대기
    
    assert watchdog.has_warnings(), "오래된 heartbeat에서는 경고 발생해야 함"
    print(f"✅ 오래된 heartbeat - 경고 발생: {watchdog.get_warning_components()}")
    
    # 정상 복귀
    heartbeat.update('engine')
    time.sleep(0.6)
    
    watchdog.stop()
    heartbeat.stop()
    print("\n✅ TEST 3 PASSED\n")


def test_latency_monitor():
    """LatencyMonitor 동작 테스트"""
    print("=" * 60)
    print("TEST 4: LatencyMonitor")
    print("=" * 60)
    
    from common.monitoring.latency_monitor import LatencyMonitor
    
    latency = LatencyMonitor(max_samples=100)
    latency.start()
    
    # Context manager 방식
    for i in range(10):
        with latency.measure('task1'):
            time.sleep(0.01)
    
    # 통계 조회
    stats = latency.get_stats('task1')
    assert stats is not None, "stats should not be None"
    assert stats['count'] == 10, f"count should be 10, got {stats['count']}"
    assert 0.008 < stats['mean'] < 0.015, f"mean should be ~0.01s, got {stats['mean']}"
    print(f"✅ Latency stats: count={stats['count']}, mean={stats['mean']:.4f}s")
    
    # 수동 방식
    start = latency.start_measure('task2')
    time.sleep(0.02)
    latency.end_measure('task2', start)
    
    stats2 = latency.get_stats('task2')
    assert stats2['count'] == 1, "task2 count should be 1"
    print(f"✅ Task2 latency: {stats2['mean']:.4f}s")
    
    # is_slow 체크
    assert not latency.is_slow('task1', threshold=0.05), "task1 should not be slow"
    print("✅ is_slow 체크 성공")
    
    # 전체 작업 목록
    tasks = latency.get_all_tasks()
    assert 'task1' in tasks and 'task2' in tasks, "tasks should contain task1 and task2"
    print(f"✅ 전체 작업: {tasks}")
    
    latency.stop()
    print("\n✅ TEST 4 PASSED\n")


def test_health_checker():
    """HealthChecker 동작 테스트"""
    print("=" * 60)
    print("TEST 5: HealthChecker")
    print("=" * 60)
    
    from common.monitoring.health_checker import HealthChecker
    
    config = {
        'monitoring': {
            'redis': {
                'host': 'localhost',
                'port': 6379
            }
        }
    }
    
    health = HealthChecker(config)
    health.start()
    
    # Redis 체크 (Docker 실행 중이어야 함)
    redis_ok = health.check_redis()
    print(f"  Redis 상태: {'✅ OK' if redis_ok else '❌ FAIL'}")
    
    # DB 체크
    db_ok = health.check_db()
    print(f"  DB 상태: {'✅ OK' if db_ok else '❌ FAIL'}")
    
    # Uptime
    uptime = health.get_uptime()
    assert uptime >= 0, "uptime should be >= 0"
    print(f"✅ Uptime: {uptime:.2f}s")
    
    # 전체 체크
    status = health.check_all()
    assert 'redis' in status, "status should contain 'redis'"
    assert 'db' in status, "status should contain 'db'"
    assert 'uptime' in status, "status should contain 'uptime'"
    print(f"✅ 전체 헬스 체크: {status}")
    
    health.stop()
    print("\n✅ TEST 5 PASSED\n")


def test_module_status():
    """ModuleStatus 동작 테스트"""
    print("=" * 60)
    print("TEST 6: ModuleStatus")
    print("=" * 60)
    
    from common.monitoring.module_status import ModuleStatus, StatusLevel
    
    status = ModuleStatus()
    status.start()
    
    # 상태 설정
    status.set_status('engine', StatusLevel.OK)
    status.set_status('websocket', StatusLevel.WARNING, "지연 발생")
    status.set_status('redis', StatusLevel.CRITICAL, "연결 끊김")
    
    # 상태 조회
    engine_status = status.get_module_status('engine')
    assert engine_status['level'] == StatusLevel.OK, "engine status should be OK"
    print(f"✅ Engine 상태: {engine_status}")
    
    # 전체 상태
    all_status = status.get_all_status()
    assert len(all_status) == 3, "should have 3 modules"
    print(f"✅ 전체 상태: {list(all_status.keys())}")
    
    # 전체 시스템 정상 여부
    assert not status.is_healthy(), "system should not be healthy (has WARNING/CRITICAL)"
    print("✅ is_healthy 체크 성공 (WARNING/CRITICAL 있음)")
    
    # CRITICAL 모듈
    critical_modules = status.get_critical_modules()
    assert 'redis' in critical_modules, "redis should be in critical_modules"
    print(f"✅ CRITICAL 모듈: {critical_modules}")
    
    # WARNING 모듈
    warning_modules = status.get_warning_modules()
    assert 'websocket' in warning_modules, "websocket should be in warning_modules"
    print(f"✅ WARNING 모듈: {warning_modules}")
    
    # 요약
    summary = status.get_summary()
    assert summary['ok'] == 1, "should have 1 OK module"
    assert summary['warning'] == 1, "should have 1 WARNING module"
    assert summary['critical'] == 1, "should have 1 CRITICAL module"
    print(f"✅ 요약: {summary}")
    
    status.stop()
    print("\n✅ TEST 6 PASSED\n")


def test_setup_monitoring():
    """setup_monitoring 통합 테스트"""
    print("=" * 60)
    print("TEST 7: setup_monitoring 통합")
    print("=" * 60)
    
    from common.runtime_context import RuntimeContext
    from common.monitoring import setup_monitoring
    
    runtime_ctx = RuntimeContext()
    runtime_ctx.run_id = '20251119_test_1234'
    runtime_ctx.env = 'paper'
    
    config = {
        'monitoring': {
            'watchdog_interval': 2.0,
            'watchdog_max_age': 30.0,
            'redis': {
                'host': 'localhost',
                'port': 6379
            }
        }
    }
    
    # 모니터링 설정
    registry = setup_monitoring(runtime_ctx, config)
    
    # Registry가 RuntimeContext에 등록되었는지 확인
    assert runtime_ctx.monitor_registry is registry, "registry should be set in runtime_ctx"
    print("✅ RuntimeContext에 registry 등록 성공")
    
    # 각 모니터 확인
    heartbeat = registry.get('heartbeat')
    assert heartbeat is not None, "heartbeat monitor should exist"
    print(f"✅ HeartbeatMonitor: {heartbeat}")
    
    watchdog = registry.get('watchdog')
    assert watchdog is not None, "watchdog should exist"
    print(f"✅ Watchdog: {watchdog}")
    
    latency = registry.get('latency')
    assert latency is not None, "latency monitor should exist"
    print(f"✅ LatencyMonitor: {latency}")
    
    health = registry.get('health')
    assert health is not None, "health checker should exist"
    print(f"✅ HealthChecker: {health}")
    
    status = registry.get('status')
    assert status is not None, "module status should exist"
    print(f"✅ ModuleStatus: {status}")
    
    # Heartbeat 테스트
    heartbeat.update('test_component')
    assert heartbeat.is_alive('test_component', max_age=5.0), "test_component should be alive"
    print("✅ Heartbeat 업데이트 테스트 성공")
    
    # 정리
    registry.stop_all()
    print("✅ 모니터링 시스템 중지")
    
    print("\n✅ TEST 7 PASSED\n")


def main():
    """전체 테스트 실행"""
    print("\n" + "=" * 60)
    print("PHASE18-4 Monitoring Framework 테스트 시작")
    print("=" * 60)
    
    tests = [
        test_monitor_registry,
        test_heartbeat_monitor,
        test_watchdog,
        test_latency_monitor,
        test_health_checker,
        test_module_status,
        test_setup_monitoring,
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
            import traceback
            traceback.print_exc()
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
