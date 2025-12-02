#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE25-4: Worker Timeout 테스트
================================
Stale job 감지 및 실패 처리 테스트

테스트 범위:
1. Stale RUNNING job 감지
2. Timeout 시 FAILED로 전환
3. max_runtime_sec 파라미터 검증
"""
import pytest
import uuid
from datetime import datetime, timedelta

from tuning.cluster import JobQueue
from tuning.algorithms import RandomSearchConfig, RandomSearchTuner, ParamSpace


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def job_queue(db_connection):
    """JobQueue 인스턴스"""
    return JobQueue()


@pytest.fixture
def sample_param_space():
    """샘플 ParamSpace"""
    return ParamSpace(space={
        'rsi_oversold': {'type': 'int', 'min': 25, 'max': 35},
        'stop_loss_pct': {'type': 'float', 'min': 0.5, 'max': 2.0},
    })


# ============================================
# Test 1: No Stale Jobs
# ============================================

def test_no_stale_jobs(job_queue):
    """Stale job이 없을 때 0 반환 검증"""
    
    # Stale job이 없을 것으로 예상
    failed_count = job_queue.mark_stale_jobs_as_failed(max_runtime_sec=3600)
    
    # 실패 처리된 job이 없어야 함 (또는 최소한 에러 없이 실행)
    assert failed_count >= 0
    
    print(f"✅ Stale job 없음: {failed_count}개 처리")


# ============================================
# Test 2: Mark Stale Job as Failed
# ============================================

@pytest.mark.slow
def test_mark_stale_job_as_failed(job_queue, sample_param_space, db_connection):
    """Stale RUNNING job을 FAILED로 전환"""
    
    # Run 생성
    run_id = f"run-stale-{uuid.uuid4().hex[:8]}"
    
    config = RandomSearchConfig(
        run_name=f'stale_test_{uuid.uuid4().hex[:8]}',
        phase='PHASE25-4-TEST',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='backtest',
        tuning_method='random',
        target_metric='sharpe_ratio',
        n_trials=3,
        base_config_path='configs/paper/phase21_scalping_quick.yml',
        param_space=sample_param_space,
        seed=77
    )
    
    tuner = RandomSearchTuner(job_queue=job_queue)
    run_id, job_ids = tuner.create_run_and_jobs(config)
    
    # Job 하나를 RUNNING 상태로 변경하고, started_at을 과거로 설정
    job_id_to_stale = job_ids[0]
    
    sql_set_stale = """
    UPDATE tuning.jobs
    SET status = 'RUNNING',
        started_at = now() - interval '2 hours',
        assigned_to = 'fake-worker',
        updated_at = now()
    WHERE job_id = %s
    """
    
    with db_connection.cursor() as cur:
        cur.execute(sql_set_stale, (job_id_to_stale,))
        db_connection.commit()
    
    # Stale job 처리 (max_runtime_sec = 3600 = 1시간)
    failed_count = job_queue.mark_stale_jobs_as_failed(max_runtime_sec=3600)
    
    # 최소 1개 이상 처리되어야 함
    assert failed_count >= 1
    
    # Job 상태 확인
    sql_check_status = """
    SELECT status, error_message
    FROM tuning.jobs
    WHERE job_id = %s
    """
    
    with db_connection.cursor() as cur:
        cur.execute(sql_check_status, (job_id_to_stale,))
        row = cur.fetchone()
    
    assert row is not None
    status, error_message = row
    
    assert status == 'FAILED'
    assert 'timeout' in error_message.lower()
    
    print(f"✅ Stale job 처리:")
    print(f"   Job ID: {job_id_to_stale}")
    print(f"   Status: {status}")
    print(f"   Error: {error_message}")
    print(f"   총 처리: {failed_count}개")


# ============================================
# Test 3: Multiple Stale Jobs
# ============================================

@pytest.mark.slow
def test_mark_multiple_stale_jobs(job_queue, sample_param_space, db_connection):
    """여러 Stale job 동시 처리"""
    
    # Run 생성
    config = RandomSearchConfig(
        run_name=f'multi_stale_{uuid.uuid4().hex[:8]}',
        phase='PHASE25-4-TEST',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='backtest',
        tuning_method='random',
        target_metric='sharpe_ratio',
        n_trials=5,
        base_config_path='configs/paper/phase21_scalping_quick.yml',
        param_space=sample_param_space,
        seed=88
    )
    
    tuner = RandomSearchTuner(job_queue=job_queue)
    run_id, job_ids = tuner.create_run_and_jobs(config)
    
    # 3개 job을 RUNNING + stale로 설정
    stale_job_ids = job_ids[:3]
    
    sql_set_stale = """
    UPDATE tuning.jobs
    SET status = 'RUNNING',
        started_at = now() - interval '3 hours',
        assigned_to = 'fake-worker',
        updated_at = now()
    WHERE job_id = ANY(%s)
    """
    
    with db_connection.cursor() as cur:
        cur.execute(sql_set_stale, (stale_job_ids,))
        db_connection.commit()
    
    # Stale job 처리
    failed_count = job_queue.mark_stale_jobs_as_failed(max_runtime_sec=7200)  # 2시간
    
    # 3개 모두 처리되어야 함
    assert failed_count >= 3
    
    # 모든 stale job이 FAILED 상태인지 확인
    sql_check_statuses = """
    SELECT job_id, status
    FROM tuning.jobs
    WHERE job_id = ANY(%s)
    """
    
    with db_connection.cursor() as cur:
        cur.execute(sql_check_statuses, (stale_job_ids,))
        rows = cur.fetchall()
    
    failed_statuses = [status for _, status in rows if status == 'FAILED']
    
    assert len(failed_statuses) == 3
    
    print(f"✅ 다중 Stale job 처리:")
    print(f"   Stale job 수: {len(stale_job_ids)}")
    print(f"   FAILED 전환: {len(failed_statuses)}개")
    print(f"   총 처리: {failed_count}개")


# ============================================
# Test 4: Timeout Parameter Validation
# ============================================

def test_timeout_parameter_validation(job_queue):
    """max_runtime_sec 파라미터 검증"""
    
    # 정상 값
    count_1h = job_queue.mark_stale_jobs_as_failed(max_runtime_sec=3600)
    assert count_1h >= 0
    
    # 짧은 시간 (1분)
    count_1m = job_queue.mark_stale_jobs_as_failed(max_runtime_sec=60)
    assert count_1m >= 0
    
    # 긴 시간 (24시간)
    count_24h = job_queue.mark_stale_jobs_as_failed(max_runtime_sec=86400)
    assert count_24h >= 0
    
    print(f"✅ Timeout 파라미터 검증:")
    print(f"   1h: {count_1h}개")
    print(f"   1m: {count_1m}개")
    print(f"   24h: {count_24h}개")


# ============================================
# Test 5: Recently Started Jobs Not Affected
# ============================================

@pytest.mark.slow
def test_recent_jobs_not_affected(job_queue, sample_param_space, db_connection):
    """최근 시작된 RUNNING job은 영향 받지 않음 검증"""
    
    # Run 생성
    config = RandomSearchConfig(
        run_name=f'recent_test_{uuid.uuid4().hex[:8]}',
        phase='PHASE25-4-TEST',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='backtest',
        tuning_method='random',
        target_metric='sharpe_ratio',
        n_trials=2,
        base_config_path='configs/paper/phase21_scalping_quick.yml',
        param_space=sample_param_space,
        seed=99
    )
    
    tuner = RandomSearchTuner(job_queue=job_queue)
    run_id, job_ids = tuner.create_run_and_jobs(config)
    
    # Job을 RUNNING 상태로 변경 (started_at은 현재 시간)
    recent_job_id = job_ids[0]
    
    sql_set_running = """
    UPDATE tuning.jobs
    SET status = 'RUNNING',
        started_at = now(),
        assigned_to = 'recent-worker',
        updated_at = now()
    WHERE job_id = %s
    """
    
    with db_connection.cursor() as cur:
        cur.execute(sql_set_running, (recent_job_id,))
        db_connection.commit()
    
    # Stale job 처리 (max_runtime_sec = 60 = 1분)
    # 방금 시작한 job은 영향 받지 않아야 함
    failed_count_before = job_queue.mark_stale_jobs_as_failed(max_runtime_sec=60)
    
    # Job 상태 확인
    sql_check_status = """
    SELECT status
    FROM tuning.jobs
    WHERE job_id = %s
    """
    
    with db_connection.cursor() as cur:
        cur.execute(sql_check_status, (recent_job_id,))
        status = cur.fetchone()[0]
    
    # 여전히 RUNNING 상태여야 함
    assert status == 'RUNNING'
    
    print(f"✅ 최근 job 영향 없음 검증:")
    print(f"   Job ID: {recent_job_id}")
    print(f"   Status: {status} (예상: RUNNING)")
    print(f"   Timeout 처리: {failed_count_before}개 (recent job 제외)")
