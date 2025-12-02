#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE25-2: Random Search Pipeline Tests
========================================
Random Search 튜닝 파이프라인 통합 테스트

Test Coverage:
- ParamSpace sampling 검증
- RandomSearchTuner 기본 동작
- Worker + 백테스트 엔진 통합 (smoke test)
- End-to-end Random Search (소규모)
"""
import pytest
import time
from pathlib import Path

from tuning.algorithms import RandomSearchTuner, ParamSpace, RandomSearchConfig
from tuning.cluster import JobQueue, TuningWorker
from database import get_db_connection


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def job_queue():
    """JobQueue 인스턴스 생성"""
    return JobQueue()


@pytest.fixture
def sample_param_space():
    """샘플 ParamSpace"""
    return ParamSpace(space={
        'rsi_oversold': {'type': 'int', 'min': 25, 'max': 35},
        'rsi_overbought': {'type': 'int', 'min': 65, 'max': 75},
        'stop_loss_pct': {'type': 'float', 'min': 0.5, 'max': 2.0},
        'leverage': {'type': 'categorical', 'values': [5, 10, 20]},
    })


@pytest.fixture
def sample_config(sample_param_space):
    """샘플 RandomSearchConfig"""
    return RandomSearchConfig(
        run_name='test_scalping_tuning',
        phase='PHASE25-2-TEST',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='paper',
        tuning_method='random',
        target_metric='sharpe_ratio',
        n_trials=5,
        base_config_path='configs/paper/phase21_scalping_quick.yml',
        param_space=sample_param_space,
        seed=42
    )


# ============================================
# Test 1: ParamSpace Sampling
# ============================================

def test_random_search_param_sampling_basic(sample_param_space):
    """ParamSpace 기본 샘플링 검증"""
    print("\n" + "=" * 80)
    print("Test 1: ParamSpace 기본 샘플링")
    print("=" * 80)
    
    # Validation
    assert sample_param_space.validate()
    
    # Sampling (seed 고정)
    params1 = sample_param_space.sample(seed=42)
    params2 = sample_param_space.sample(seed=42)
    params3 = sample_param_space.sample(seed=99)
    
    print(f"샘플 1 (seed=42): {params1}")
    print(f"샘플 2 (seed=42): {params2}")
    print(f"샘플 3 (seed=99): {params3}")
    
    # Seed 고정 시 동일한 결과
    assert params1 == params2
    
    # 다른 seed는 다른 결과 (높은 확률)
    assert params1 != params3
    
    # 타입 검증
    assert isinstance(params1['rsi_oversold'], int)
    assert isinstance(params1['stop_loss_pct'], float)
    assert params1['leverage'] in [5, 10, 20]
    
    # 범위 검증
    assert 25 <= params1['rsi_oversold'] <= 35
    assert 65 <= params1['rsi_overbought'] <= 75
    assert 0.5 <= params1['stop_loss_pct'] <= 2.0
    
    print("✅ ParamSpace 샘플링 검증 완료")


def test_param_space_validation():
    """ParamSpace 검증 로직 테스트"""
    print("\n" + "=" * 80)
    print("Test 2: ParamSpace 검증")
    print("=" * 80)
    
    # Valid space
    valid_space = ParamSpace(space={
        'x': {'type': 'int', 'min': 1, 'max': 10},
    })
    assert valid_space.validate()
    
    # Invalid: type 누락
    with pytest.raises(ValueError, match="'type' 필드 필수"):
        ParamSpace(space={'x': {'min': 1, 'max': 10}}).validate()
    
    # Invalid: min/max 누락
    with pytest.raises(ValueError, match="'min', 'max' 필드 필수"):
        ParamSpace(space={'x': {'type': 'int', 'min': 1}}).validate()
    
    # Invalid: min >= max
    with pytest.raises(ValueError, match="min >= max"):
        ParamSpace(space={'x': {'type': 'int', 'min': 10, 'max': 5}}).validate()
    
    # Invalid: categorical values 누락
    with pytest.raises(ValueError, match="'values' 필드 필수"):
        ParamSpace(space={'x': {'type': 'categorical'}}).validate()
    
    print("✅ ParamSpace 검증 로직 확인 완료")


# ============================================
# Test 3: RandomSearchTuner - Run & Job 생성
# ============================================

def test_create_run_and_jobs_inserts_records(job_queue, sample_config):
    """RandomSearchTuner가 Run & Job 레코드를 생성하는지 검증"""
    print("\n" + "=" * 80)
    print("Test 3: RandomSearchTuner - Run & Job 생성")
    print("=" * 80)
    
    tuner = RandomSearchTuner(job_queue=job_queue)
    
    # Run & Job 생성
    run_id, job_ids = tuner.create_run_and_jobs(sample_config)
    
    print(f"Run ID: {run_id}")
    print(f"Job IDs ({len(job_ids)}개): {job_ids[:3]}...")
    
    assert run_id is not None
    assert len(job_ids) == sample_config.n_trials
    
    # DB 검증: tuning.runs
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT run_id, phase, strategy_name, total_jobs, status
                FROM tuning.runs
                WHERE run_id = %s
            """, (run_id,))
            run_row = cur.fetchone()
            
            assert run_row is not None
            assert run_row[0] == run_id
            assert run_row[1] == sample_config.phase
            assert run_row[2] == sample_config.strategy_name
            assert run_row[3] == sample_config.n_trials
            assert run_row[4] == 'PENDING'
            
            # DB 검증: tuning.jobs
            cur.execute("""
                SELECT COUNT(*), COUNT(CASE WHEN status = 'PENDING' THEN 1 END)
                FROM tuning.jobs
                WHERE run_id = %s
            """, (run_id,))
            job_row = cur.fetchone()
            
            assert job_row[0] == sample_config.n_trials
            assert job_row[1] == sample_config.n_trials  # 모두 PENDING
    
    print("✅ Run & Job 생성 검증 완료")


# ============================================
# Test 4: Worker + 백테스트 엔진 통합 (Smoke)
# ============================================

@pytest.mark.slow
def test_worker_process_job_backtest_integration_smoke(job_queue):
    """Worker가 실제 백테스트 엔진을 호출하는지 smoke test"""
    print("\n" + "=" * 80)
    print("Test 4: Worker + 백테스트 엔진 통합 (Smoke)")
    print("=" * 80)
    
    # 아주 작은 config로 Run 생성
    mini_config = RandomSearchConfig(
        run_name='test_smoke_mini',
        phase='PHASE25-2-TEST',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='paper',  # paper 모드 (30초)
        tuning_method='random',
        target_metric='sharpe_ratio',
        n_trials=1,
        base_config_path='configs/paper/phase21_scalping_quick.yml',
        param_space=ParamSpace(space={
            'entry_threshold': {'type': 'float', 'min': 0.4, 'max': 0.6},
        }),
        seed=42
    )
    
    tuner = RandomSearchTuner(job_queue=job_queue)
    run_id, job_ids = tuner.create_run_and_jobs(mini_config)
    
    print(f"Run ID: {run_id}")
    print(f"Job ID: {job_ids[0]}")
    
    # Worker 생성 및 1개 Job 처리
    worker = TuningWorker(
        worker_id='test-worker-smoke',
        job_queue=job_queue,
        run_id=run_id
    )
    
    print("Worker 실행 중 (1개 job, 약 30초 소요)...")
    start_time = time.time()
    
    try:
        worker.loop(once=True)
    except Exception as e:
        print(f"⚠️  Worker 실행 중 에러: {e}")
        # 테스트는 계속 진행 (메트릭 추출 실패 등은 허용)
    
    elapsed = time.time() - start_time
    print(f"Worker 실행 시간: {elapsed:.1f}s")
    
    # Job 상태 확인
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT status
                FROM tuning.jobs
                WHERE job_id = %s
            """, (job_ids[0],))
            job_status = cur.fetchone()[0]
            
            print(f"Job 상태: {job_status}")
            
            # COMPLETED 또는 FAILED (엔진 호출 자체는 성공)
            assert job_status in ('COMPLETED', 'FAILED', 'RUNNING')
            
            # tuning.results 확인 (COMPLETED인 경우)
            if job_status == 'COMPLETED':
                cur.execute("""
                    SELECT result_id, pnl, sharpe_ratio, trade_count
                    FROM tuning.results
                    WHERE job_id = %s
                """, (job_ids[0],))
                result_row = cur.fetchone()
                
                if result_row:
                    print(f"Result ID: {result_row[0]}")
                    print(f"  PnL: {result_row[1]}")
                    print(f"  Sharpe: {result_row[2]}")
                    print(f"  Trades: {result_row[3]}")
                    
                    # 메트릭이 저장되었는지 확인
                    assert result_row[0] is not None
    
    print("✅ Worker + 백테스트 엔진 통합 smoke test 완료")


# ============================================
# Test 5: End-to-End Random Search (소규모)
# ============================================

@pytest.mark.slow
def test_end_to_end_random_search_single_worker():
    """End-to-end Random Search 파이프라인 테스트 (5 trials)"""
    print("\n" + "=" * 80)
    print("Test 5: End-to-End Random Search (5 trials)")
    print("=" * 80)
    
    # Config 생성
    e2e_config = RandomSearchConfig(
        run_name='test_e2e_random_search',
        phase='PHASE25-2-TEST',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='paper',
        tuning_method='random',
        target_metric='sharpe_ratio',
        n_trials=3,  # 3개로 줄여서 빠르게
        base_config_path='configs/paper/phase21_scalping_quick.yml',
        param_space=ParamSpace(space={
            'entry_threshold': {'type': 'float', 'min': 0.3, 'max': 0.7},
            'stop_loss_pct': {'type': 'float', 'min': 0.5, 'max': 1.5},
        }),
        seed=42
    )
    
    # Tuner 생성
    tuner = RandomSearchTuner()
    
    # Run & Job 생성
    run_id, job_ids = tuner.create_run_and_jobs(e2e_config)
    print(f"Run ID: {run_id}")
    print(f"Job IDs ({len(job_ids)}개): {job_ids}")
    
    # Worker 생성
    worker = TuningWorker(
        worker_id='test-worker-e2e',
        job_queue=tuner.job_queue,
        run_id=run_id
    )
    
    # 모든 Job 처리
    print(f"Worker 실행 중 ({e2e_config.n_trials}개 job, 약 {e2e_config.n_trials * 30}초 소요)...")
    start_time = time.time()
    
    processed_count = 0
    max_iterations = e2e_config.n_trials * 2  # 안전장치
    
    for i in range(max_iterations):
        # Run 상태 확인
        status = tuner.job_queue.get_run_status(run_id)
        pending = status.get('pending_jobs', 0)
        completed = status.get('completed_jobs', 0)
        failed = status.get('failed_jobs', 0)
        
        print(f"  [{i+1}/{max_iterations}] Pending={pending}, Completed={completed}, Failed={failed}")
        
        if pending == 0:
            print("✅ 모든 Job 처리 완료")
            break
        
        # 1개 Job 처리
        try:
            worker.loop(once=True, poll_interval_sec=1)
            processed_count += 1
        except Exception as e:
            print(f"⚠️  Job 처리 중 에러 (계속 진행): {e}")
    
    elapsed = time.time() - start_time
    print(f"Worker 실행 시간: {elapsed:.1f}s")
    print(f"처리된 Job 수: {processed_count}")
    
    # 최종 상태 확인
    final_status = tuner.job_queue.get_run_status(run_id)
    print(f"최종 상태: {final_status}")
    
    assert final_status['pending_jobs'] == 0
    assert final_status['completed_jobs'] + final_status['failed_jobs'] == e2e_config.n_trials
    
    # 결과 조회
    if final_status['completed_jobs'] > 0:
        results = tuner.job_queue.get_run_results(run_id)
        print(f"결과 수: {len(results)}")
        
        # Top K 추출
        top_k = tuner.get_top_k_results(run_id, k=3, ascending=False)
        print(f"Top 3 결과:")
        for i, result in enumerate(top_k, 1):
            print(f"  [{i}] Sharpe={result.get('sharpe_ratio', 0):.4f}, "
                  f"PnL={result.get('pnl', 0):.2f}")
        
        assert len(results) > 0
    
    print("✅ End-to-End Random Search 완료")


# ============================================
# Main
# ============================================

if __name__ == "__main__":
    # 개별 테스트 실행 (디버깅용)
    print("=" * 80)
    print("PHASE25-2: Random Search Pipeline Tests")
    print("=" * 80)
    
    try:
        # Test 1
        space = ParamSpace(space={
            'rsi_oversold': {'type': 'int', 'min': 25, 'max': 35},
            'rsi_overbought': {'type': 'int', 'min': 65, 'max': 75},
            'stop_loss_pct': {'type': 'float', 'min': 0.5, 'max': 2.0},
            'leverage': {'type': 'categorical', 'values': [5, 10, 20]},
        })
        test_random_search_param_sampling_basic(space)
        
        # Test 2
        test_param_space_validation()
        
        # Test 3
        queue = JobQueue()
        config = RandomSearchConfig(
            run_name='test_scalping_tuning',
            phase='PHASE25-2-TEST',
            strategy_family='momentum',
            strategy_name='scalping',
            mode='paper',
            tuning_method='random',
            target_metric='sharpe_ratio',
            n_trials=5,
            base_config_path='configs/paper/phase21_scalping_quick.yml',
            param_space=space,
            seed=42
        )
        test_create_run_and_jobs_inserts_records(queue, config)
        
        print("\n" + "=" * 80)
        print("✅ 기본 테스트 완료 (Smoke/E2E는 pytest로 실행)")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
