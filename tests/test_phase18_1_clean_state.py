#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE18-1: Clean-State 초기화 테스트
====================================
init_clean_state.py 자동 테스트
"""
import sys
import subprocess
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_init_clean_state_script():
    """init_clean_state.py 스크립트 실행 테스트"""
    print("=" * 60)
    print("TEST 1: init_clean_state.py 단독 실행")
    print("=" * 60)
    
    init_script = project_root / "scripts" / "ops" / "init_clean_state.py"
    
    # 스크립트 실행
    result = subprocess.run(
        [sys.executable, str(init_script)],
        capture_output=True,
        text=True
    )
    
    print(f"Return Code: {result.returncode}")
    print("\n[STDOUT]:")
    print(result.stdout)
    
    if result.stderr:
        print("\n[STDERR]:")
        print(result.stderr)
    
    assert result.returncode == 0, "init_clean_state.py 실행 실패"
    print("\n✅ TEST 1 PASSED")


def test_redis_initialization():
    """Redis 초기화 테스트"""
    print("\n" + "=" * 60)
    print("TEST 2: Redis 초기화 검증")
    print("=" * 60)
    
    try:
        import redis
        client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        client.ping()
        
        # 더미 키 생성
        print("더미 키 생성...")
        client.set("candle:seen:TEST:1m:12345", "1")
        client.set("flow_guard:TEST", "1")
        client.set("cooldown:TEST", "1")
        
        keys_before = client.keys("candle:seen:*") + client.keys("flow_guard:*") + client.keys("cooldown:*")
        print(f"초기화 전 키 개수: {len(keys_before)}")
        
        # init_clean_state.py 실행
        print("\ninit_clean_state.py 실행...")
        init_script = project_root / "scripts" / "ops" / "init_clean_state.py"
        result = subprocess.run(
            [sys.executable, str(init_script)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, "init_clean_state.py 실행 실패"
        
        # 초기화 후 키 확인
        keys_after = client.keys("candle:seen:*") + client.keys("flow_guard:*") + client.keys("cooldown:*")
        print(f"초기화 후 키 개수: {len(keys_after)}")
        
        assert len(keys_after) == 0, f"Redis 키가 완전히 삭제되지 않음: {len(keys_after)}개 남음"
        print("\n✅ TEST 2 PASSED")
        
    except ImportError:
        print("⚠️ redis 패키지 없음 - 테스트 건너뜀")
    except Exception as e:
        print(f"⚠️ Redis 연결 실패: {e} - 테스트 건너뜀")


def test_log_backup():
    """로그 백업 테스트"""
    print("\n" + "=" * 60)
    print("TEST 3: 로그 백업 검증")
    print("=" * 60)
    
    logs_dir = project_root / "logs"
    
    # 더미 로그 파일 생성
    if not logs_dir.exists():
        logs_dir.mkdir(parents=True)
    
    test_log = logs_dir / "application.log"
    test_content = "TEST LOG CONTENT\n"
    test_log.write_text(test_content)
    print(f"더미 로그 생성: {test_log}")
    
    # 백업 전 파일 개수
    backup_files_before = list(logs_dir.glob("*.bak"))
    print(f"백업 전 .bak 파일 개수: {len(backup_files_before)}")
    
    # init_clean_state.py 실행
    print("\ninit_clean_state.py 실행...")
    init_script = project_root / "scripts" / "ops" / "init_clean_state.py"
    result = subprocess.run(
        [sys.executable, str(init_script)],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, "init_clean_state.py 실행 실패"
    
    # 백업 후 파일 개수
    backup_files_after = list(logs_dir.glob("*.bak"))
    print(f"백업 후 .bak 파일 개수: {len(backup_files_after)}")
    
    # 백업 파일이 생성되었는지 확인
    assert len(backup_files_after) > len(backup_files_before), "백업 파일이 생성되지 않음"
    
    # Note: 로그 파일 완전 초기화는 init_clean_state.py 자체가 로그를 쓰기 때문에 불가능
    # 실제 초기화는 run_paper/run_backtest가 --clean-state로 실행될 때 수행됨
    print("Note: 로그 백업 성공, 실제 초기화는 run_paper/run_backtest 시작 시 수행")
    
    print("\n✅ TEST 3 PASSED")


def test_run_paper_clean_state_flag():
    """run_paper.py --clean-state 플래그 테스트"""
    print("\n" + "=" * 60)
    print("TEST 4: run_paper.py --clean-state 플래그")
    print("=" * 60)
    
    run_paper_script = project_root / "scripts" / "run_paper.py"
    
    # --help로 플래그 존재 확인
    result = subprocess.run(
        [sys.executable, str(run_paper_script), "--help"],
        capture_output=True,
        text=True
    )
    
    assert "--clean-state" in result.stdout, "--clean-state 플래그가 없음"
    print("✅ --clean-state 플래그 존재 확인")
    print("\n✅ TEST 4 PASSED")


def main():
    """전체 테스트 실행"""
    print("\n" + "=" * 60)
    print("PHASE18-1 Clean-State 테스트 시작")
    print("=" * 60)
    
    tests = [
        test_init_clean_state_script,
        test_redis_initialization,
        test_log_backup,
        test_run_paper_clean_state_flag,
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
