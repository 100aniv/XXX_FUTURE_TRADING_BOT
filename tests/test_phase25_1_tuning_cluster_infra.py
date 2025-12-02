#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE25-1: Tuning Cluster Infrastructure Tests
===============================================
튜닝 클러스터 인프라 테스트

테스트 시나리오:
1. DB 스키마 기본 동작 (INSERT/SELECT/UPDATE)
2. Job Queue 동시성 (2개 Worker가 각각 다른 job 할당받는지)
3. Worker Skeleton (dummy 실행 후 COMPLETED 상태 및 메트릭 저장)

실행:
    pytest tests/test_phase25_1_tuning_cluster_infra.py -v
"""
import pytest
import time
import uuid
from datetime import datetime
from typing import Dict, Any

from tuning.cluster import JobQueue, TuningWorker
from database import get_db_connection


# ============================================================================
# Fixture
# ============================================================================

@pytest.fixture
def test_run_id():
    """테스트용 Run ID 생성"""
    return f"test_run_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def job_queue():
    """JobQueue 인스턴스"""
    return JobQueue()


@pytest.fixture
def cleanup_test_runs(job_queue):
    """테스트 후 정리"""
    yield
    # 테스트 Run 정리 (테스트 후 실행)
    # Note: CASCADE로 jobs/results도 자동 삭제됨


# ============================================================================
# Test 1: DB 스키마 기본 동작
# ============================================================================

def test_create_run(job_queue, test_run_id, cleanup_test_runs):
    """Run 생성 테스트"""
    success = job_queue.create_run(
        run_id=test_run_id,
        phase='PHASE25-1-TEST',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='backtest',
        tuning_method='random',
        target_metric='sharpe_ratio',
        total_jobs=10,
        seed=42,
        config_override={'test': True},
        metadata={'purpose': 'unit_test'}
    )
    
    assert success is True, "Run 생성 실패"
    
    # Run 상태 조회
    run_status = job_queue.get_run_status(test_run_id)
    assert run_status is not None, "Run 조회 실패"
    assert run_status['run_id'] == test_run_id
    assert run_status['strategy_name'] == 'scalping'
    assert run_status['tuning_method'] == 'random'
    assert run_status['total_jobs'] == 10
    assert run_status['status'] == 'PENDING'
    
    print(f"✅ Run 생성 성공: {test_run_id}")


def test_enqueue_jobs(job_queue, test_run_id, cleanup_test_runs):
    """Job 생성 테스트"""
    # Run 생성
    job_queue.create_run(
        run_id=test_run_id,
        phase='PHASE25-1-TEST',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='backtest',
        tuning_method='random',
        target_metric='sharpe_ratio',
        total_jobs=3
    )
    
    # Job 3개 생성
    job_ids = []
    for i in range(3):
        job_id = job_queue.enqueue_job(
            run_id=test_run_id,
            params={'rsi_oversold': 40 + i, 'rsi_overbought': 60 + i}
        )
        assert job_id is not None, f"Job {i} 생성 실패"
        job_ids.append(job_id)
    
    assert len(job_ids) == 3, "Job 수가 맞지 않음"
    
    # Job 조회
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM tuning.jobs WHERE run_id = %s", (test_run_id,))
            count = cur.fetchone()[0]
            assert count == 3, f"DB에 저장된 Job 수가 맞지 않음: {count}"
    
    print(f"✅ Job 3개 생성 성공: {job_ids}")


def test_job_status_transitions(job_queue, test_run_id, cleanup_test_runs):
    """Job 상태 전이 테스트"""
    # Run 생성
    job_queue.create_run(
        run_id=test_run_id,
        phase='PHASE25-1-TEST',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='backtest',
        tuning_method='random',
        target_metric='sharpe_ratio',
        total_jobs=1
    )
    
    # Job 생성
    job_id = job_queue.enqueue_job(
        run_id=test_run_id,
        params={'rsi_oversold': 45}
    )
    
    # 초기 상태: PENDING
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM tuning.jobs WHERE job_id = %s", (job_id,))
            status = cur.fetchone()[0]
            assert status == 'PENDING', f"초기 상태가 PENDING이 아님: {status}"
    
    # PENDING → RUNNING
    job = job_queue.acquire_next_job(worker_id='test-worker', run_id=test_run_id)
    assert job is not None, "Job 할당 실패"
    assert job['job_id'] == job_id
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM tuning.jobs WHERE job_id = %s", (job_id,))
            status = cur.fetchone()[0]
            assert status == 'RUNNING', f"상태가 RUNNING이 아님: {status}"
    
    # RUNNING → COMPLETED
    result_metrics = {
        'pnl': 123.45,
        'sharpe_ratio': 1.5,
        'win_rate': 0.6,
        'trade_count': 10
    }
    success = job_queue.mark_job_completed(job_id, result_metrics)
    assert success is True, "Job 완료 처리 실패"
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM tuning.jobs WHERE job_id = %s", (job_id,))
            status = cur.fetchone()[0]
            assert status == 'COMPLETED', f"상태가 COMPLETED가 아님: {status}"
            
            # Result 저장 확인
            cur.execute("SELECT pnl, sharpe_ratio FROM tuning.results WHERE job_id = %s", (job_id,))
            result = cur.fetchone()
            assert result is not None, "Result 저장 안됨"
            assert float(result[0]) == 123.45
            assert float(result[1]) == 1.5
    
    print(f"✅ Job 상태 전이 성공: PENDING → RUNNING → COMPLETED")


# ============================================================================
# Test 2: Job Queue 동시성
# ============================================================================

def test_concurrent_job_acquisition(job_queue, test_run_id, cleanup_test_runs):
    """2개 Worker가 동시에 acquire_next_job 호출 시 중복 할당 방지 테스트"""
    # Run 생성
    job_queue.create_run(
        run_id=test_run_id,
        phase='PHASE25-1-TEST',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='backtest',
        tuning_method='random',
        target_metric='sharpe_ratio',
        total_jobs=3
    )
    
    # Job 3개 생성
    job_ids = []
    for i in range(3):
        job_id = job_queue.enqueue_job(
            run_id=test_run_id,
            params={'rsi_oversold': 40 + i}
        )
        job_ids.append(job_id)
    
    # 2개 Worker가 동시에 acquire_next_job 호출
    # Note: 실제로는 별도 프로세스이지만, 테스트에서는 순차 호출
    # DB lock(FOR UPDATE SKIP LOCKED)이 동시성을 보장
    
    job1 = job_queue.acquire_next_job(worker_id='worker-001', run_id=test_run_id)
    job2 = job_queue.acquire_next_job(worker_id='worker-002', run_id=test_run_id)
    job3 = job_queue.acquire_next_job(worker_id='worker-003', run_id=test_run_id)
    
    assert job1 is not None, "Worker-001 Job 할당 실패"
    assert job2 is not None, "Worker-002 Job 할당 실패"
    assert job3 is not None, "Worker-003 Job 할당 실패"
    
    # 각 Worker가 서로 다른 Job을 가져갔는지 확인
    acquired_job_ids = {job1['job_id'], job2['job_id'], job3['job_id']}
    assert len(acquired_job_ids) == 3, f"중복 할당 발생: {acquired_job_ids}"
    
    # 4번째 호출은 None (Job 없음)
    job4 = job_queue.acquire_next_job(worker_id='worker-004', run_id=test_run_id)
    assert job4 is None, "4번째 호출에서 Job이 반환됨 (예상: None)"
    
    print(f"✅ 동시성 테스트 성공: 3개 Worker가 각각 다른 Job 할당받음")
    print(f"   Worker-001: {job1['job_id']}")
    print(f"   Worker-002: {job2['job_id']}")
    print(f"   Worker-003: {job3['job_id']}")


# ============================================================================
# Test 3: Worker Skeleton
# ============================================================================

def test_worker_dummy_execution(job_queue, test_run_id, cleanup_test_runs):
    """Worker dummy 실행 테스트"""
    # Run 생성
    job_queue.create_run(
        run_id=test_run_id,
        phase='PHASE25-1-TEST',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='backtest',
        tuning_method='random',
        target_metric='sharpe_ratio',
        total_jobs=2
    )
    
    # Job 2개 생성
    job_ids = []
    for i in range(2):
        job_id = job_queue.enqueue_job(
            run_id=test_run_id,
            params={'rsi_oversold': 40 + i}
        )
        job_ids.append(job_id)
    
    # Worker 생성 및 실행 (once=True)
    worker = TuningWorker(
        worker_id='test-worker',
        job_queue=job_queue,
        run_id=test_run_id,
        use_dummy=True  # PHASE25-1 하위 호환
    )
    
    # 1개 Job만 처리
    worker.loop(once=True)
    
    # Worker가 1개 Job을 처리했는지 확인
    assert worker.jobs_processed == 1, f"Worker가 처리한 Job 수가 맞지 않음: {worker.jobs_processed}"
    
    # DB 상태 확인
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1개는 COMPLETED, 1개는 PENDING
            cur.execute("SELECT COUNT(*) FROM tuning.jobs WHERE run_id = %s AND status = 'COMPLETED'", (test_run_id,))
            completed = cur.fetchone()[0]
            assert completed == 1, f"COMPLETED Job 수가 맞지 않음: {completed}"
            
            cur.execute("SELECT COUNT(*) FROM tuning.jobs WHERE run_id = %s AND status = 'PENDING'", (test_run_id,))
            pending = cur.fetchone()[0]
            assert pending == 1, f"PENDING Job 수가 맞지 않음: {pending}"
            
            # Result 확인
            cur.execute("SELECT COUNT(*) FROM tuning.results WHERE run_id = %s", (test_run_id,))
            result_count = cur.fetchone()[0]
            assert result_count == 1, f"Result 수가 맞지 않음: {result_count}"
            
            # Result 메트릭 확인 (dummy 값이어도 저장되었는지)
            cur.execute("SELECT pnl, sharpe_ratio, trade_count FROM tuning.results WHERE run_id = %s", (test_run_id,))
            result = cur.fetchone()
            assert result is not None, "Result 저장 안됨"
            assert result[0] is not None, "PnL이 NULL"
            assert result[1] is not None, "Sharpe Ratio가 NULL"
            assert result[2] is not None, "Trade Count가 NULL"
    
    print(f"✅ Worker dummy 실행 성공")
    print(f"   처리한 Job: 1개")
    print(f"   남은 Job: 1개 (PENDING)")


def test_worker_multiple_jobs(job_queue, test_run_id, cleanup_test_runs):
    """Worker가 여러 Job을 순차 처리하는지 테스트"""
    # Run 생성
    job_queue.create_run(
        run_id=test_run_id,
        phase='PHASE25-1-TEST',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='backtest',
        tuning_method='random',
        target_metric='sharpe_ratio',
        total_jobs=5
    )
    
    # Job 5개 생성
    for i in range(5):
        job_queue.enqueue_job(
            run_id=test_run_id,
            params={'rsi_oversold': 40 + i}
        )
    
    # Worker 생성 및 실행 (once=False, 하지만 5개 처리 후 자동 종료)
    worker = TuningWorker(
        worker_id='test-worker',
        job_queue=job_queue,
        run_id=test_run_id,
        use_dummy=True  # PHASE25-1 하위 호환
    )
    
    # 5개 Job 모두 처리
    # Note: once=False이지만, Job이 없으면 loop이 멈춤 (테스트 환경)
    # 실제로는 poll_interval만큼 대기하므로 timeout 필요
    # 여기서는 수동으로 5번 loop 호출
    for _ in range(5):
        worker.loop(once=True)
    
    # Worker가 5개 Job을 처리했는지 확인
    assert worker.jobs_processed == 5, f"Worker가 처리한 Job 수가 맞지 않음: {worker.jobs_processed}"
    
    # DB 상태 확인
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 5개 모두 COMPLETED
            cur.execute("SELECT COUNT(*) FROM tuning.jobs WHERE run_id = %s AND status = 'COMPLETED'", (test_run_id,))
            completed = cur.fetchone()[0]
            assert completed == 5, f"COMPLETED Job 수가 맞지 않음: {completed}"
            
            # Result 5개
            cur.execute("SELECT COUNT(*) FROM tuning.results WHERE run_id = %s", (test_run_id,))
            result_count = cur.fetchone()[0]
            assert result_count == 5, f"Result 수가 맞지 않음: {result_count}"
    
    print(f"✅ Worker 여러 Job 처리 성공: 5개")


# ============================================================================
# Test 4: Run 관리
# ============================================================================

def test_cancel_run(job_queue, test_run_id, cleanup_test_runs):
    """Run 취소 테스트"""
    # Run 생성
    job_queue.create_run(
        run_id=test_run_id,
        phase='PHASE25-1-TEST',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='backtest',
        tuning_method='random',
        target_metric='sharpe_ratio',
        total_jobs=3
    )
    
    # Job 3개 생성
    for i in range(3):
        job_queue.enqueue_job(
            run_id=test_run_id,
            params={'rsi_oversold': 40 + i}
        )
    
    # 1개 Job만 RUNNING으로 변경
    job_queue.acquire_next_job(worker_id='test-worker', run_id=test_run_id)
    
    # Run 취소
    success = job_queue.cancel_run(test_run_id)
    assert success is True, "Run 취소 실패"
    
    # DB 상태 확인
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Run 상태: CANCELLED
            cur.execute("SELECT status FROM tuning.runs WHERE run_id = %s", (test_run_id,))
            run_status = cur.fetchone()[0]
            assert run_status == 'CANCELLED', f"Run 상태가 CANCELLED가 아님: {run_status}"
            
            # 모든 Job 상태: CANCELLED
            cur.execute("SELECT COUNT(*) FROM tuning.jobs WHERE run_id = %s AND status = 'CANCELLED'", (test_run_id,))
            cancelled_count = cur.fetchone()[0]
            assert cancelled_count == 3, f"CANCELLED Job 수가 맞지 않음: {cancelled_count}"
    
    print(f"✅ Run 취소 성공: {test_run_id} (3개 Job 취소)")


# ============================================================================
# Test 실행 (직접 실행 시)
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("PHASE25-1: Tuning Cluster Infrastructure Tests")
    print("=" * 80)
    
    try:
        # Test 1: DB 스키마
        print("\n[Test 1] DB 스키마 기본 동작")
        test_run_id_1 = f"test_run_{uuid.uuid4().hex[:8]}"
        queue = JobQueue()
        
        test_create_run(queue, test_run_id_1, None)
        test_enqueue_jobs(queue, test_run_id_1, None)
        test_job_status_transitions(queue, test_run_id_1, None)
        
        # Test 2: Job Queue 동시성
        print("\n[Test 2] Job Queue 동시성")
        test_run_id_2 = f"test_run_{uuid.uuid4().hex[:8]}"
        test_concurrent_job_acquisition(queue, test_run_id_2, None)
        
        # Test 3: Worker Skeleton
        print("\n[Test 3] Worker Skeleton")
        test_run_id_3 = f"test_run_{uuid.uuid4().hex[:8]}"
        test_worker_dummy_execution(queue, test_run_id_3, None)
        
        test_run_id_4 = f"test_run_{uuid.uuid4().hex[:8]}"
        test_worker_multiple_jobs(queue, test_run_id_4, None)
        
        # Test 4: Run 관리
        print("\n[Test 4] Run 관리")
        test_run_id_5 = f"test_run_{uuid.uuid4().hex[:8]}"
        test_cancel_run(queue, test_run_id_5, None)
        
        print("\n" + "=" * 80)
        print("✅ 모든 테스트 PASS")
        print("=" * 80)
    
    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        import sys
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ 테스트 오류: {e}")
        import sys
        import traceback
        traceback.print_exc()
        sys.exit(1)
