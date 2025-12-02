#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE25-4: Local Grid Search Tuner 테스트
==========================================
Local Grid Search 튜닝 알고리즘 테스트

테스트 범위:
1. Grid 생성 로직 검증
2. Top K 후보 조회
3. Run/Job 레코드 생성
4. Config validation
"""
import pytest
import uuid
from datetime import datetime

from tuning.algorithms import (
    LocalGridSearchConfig,
    LocalGridSearchTuner,
    RandomSearchConfig,
    RandomSearchTuner,
    ParamSpace
)
from tuning.cluster import JobQueue


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
        'rsi_oversold': {'type': 'int', 'min': 20, 'max': 40},
        'rsi_overbought': {'type': 'int', 'min': 60, 'max': 80},
        'stop_loss_pct': {'type': 'float', 'min': 0.5, 'max': 2.0},
        'take_profit_mult': {'type': 'float', 'min': 1.5, 'max': 3.0},
        'leverage': {'type': 'categorical', 'values': [5, 10, 20]}
    })


# ============================================
# Test 1: Config Validation
# ============================================

def test_local_grid_config_validation():
    """LocalGridSearchConfig validation 테스트"""
    
    # Valid config
    config = LocalGridSearchConfig(
        run_name='test_local_grid',
        phase='PHASE25-4-TEST',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='backtest',
        target_metric='sharpe_ratio',
        base_run_id='run-base-123',
        top_k=3,
        grid_steps=3,
        step_factor=0.1,
        base_config_path='configs/paper/phase21_scalping_quick.yml'
    )
    
    assert config.validate() is True
    assert config.tuning_method == 'local_grid'
    
    # Invalid: no base_run_id
    with pytest.raises(ValueError, match="base_run_id"):
        config = LocalGridSearchConfig(
            run_name='test',
            phase='PHASE25-4',
            strategy_family='momentum',
            strategy_name='scalping',
            mode='backtest',
            base_run_id='',  # Empty
            base_config_path='configs/test.yml'
        )
        config.validate()
    
    # Invalid: top_k <= 0
    with pytest.raises(ValueError, match="top_k"):
        config = LocalGridSearchConfig(
            run_name='test',
            phase='PHASE25-4',
            strategy_family='momentum',
            strategy_name='scalping',
            mode='backtest',
            base_run_id='run-123',
            top_k=0,  # Invalid
            base_config_path='configs/test.yml'
        )
        config.validate()
    
    # Invalid: step_factor out of range
    with pytest.raises(ValueError, match="step_factor"):
        config = LocalGridSearchConfig(
            run_name='test',
            phase='PHASE25-4',
            strategy_family='momentum',
            strategy_name='scalping',
            mode='backtest',
            base_run_id='run-123',
            step_factor=1.5,  # > 1.0
            base_config_path='configs/test.yml'
        )
        config.validate()


# ============================================
# Test 2: Grid Generation Logic
# ============================================

def test_grid_generation_around_candidate(sample_param_space):
    """후보 주변 그리드 생성 로직 테스트"""
    
    tuner = LocalGridSearchTuner()
    
    # 중심 파라미터
    center_params = {
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'stop_loss_pct': 1.0,
        'take_profit_mult': 2.0,
        'leverage': 10
    }
    
    # Grid 생성
    grid = tuner._generate_grid_around_candidate(
        params=center_params,
        param_space=sample_param_space,
        grid_steps=3,
        step_factor=0.1
    )
    
    # 검증
    assert len(grid) > 0
    
    # int 파라미터: center ± 1
    rsi_oversold_values = set(p['rsi_oversold'] for p in grid)
    assert 29 in rsi_oversold_values or 30 in rsi_oversold_values or 31 in rsi_oversold_values
    
    # float 파라미터: center ± delta
    stop_loss_values = [p['stop_loss_pct'] for p in grid]
    assert any(0.85 <= v <= 1.15 for v in stop_loss_values)  # 1.0 ± 0.15 (1.5 * 0.1)
    
    # categorical: 중심값만
    leverage_values = set(p['leverage'] for p in grid)
    assert leverage_values == {10}
    
    print(f"✅ Grid 생성: {len(grid)}개 조합")
    print(f"   RSI Oversold: {rsi_oversold_values}")
    print(f"   Stop Loss: {set(p['stop_loss_pct'] for p in grid)}")


# ============================================
# Test 3: Grid Size Calculation
# ============================================

def test_grid_size_calculation():
    """Grid 크기 계산 검증"""
    
    tuner = LocalGridSearchTuner()
    
    # ParamSpace: 2개 int, 1개 categorical
    param_space = ParamSpace(space={
        'rsi_oversold': {'type': 'int', 'min': 20, 'max': 40},
        'rsi_overbought': {'type': 'int', 'min': 60, 'max': 80},
        'leverage': {'type': 'categorical', 'values': [5, 10, 20]}
    })
    
    center_params = {
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'leverage': 10
    }
    
    # Grid steps = 3 → 3 x 3 x 1 = 9
    grid = tuner._generate_grid_around_candidate(
        params=center_params,
        param_space=param_space,
        grid_steps=3,
        step_factor=0.1
    )
    
    assert len(grid) == 9
    print(f"✅ Grid 크기: {len(grid)} (예상: 9)")


# ============================================
# Test 4: Run and Jobs Creation (Slow)
# ============================================

@pytest.mark.slow
def test_local_grid_creates_run_and_jobs(job_queue, sample_param_space, db_connection):
    """Local Grid Search Run/Jobs 생성 (DB 통합)"""
    
    # 1. Base run (Random) 생성
    base_run_id = f"run-base-{uuid.uuid4().hex[:8]}"
    
    random_config = RandomSearchConfig(
        run_name=f'base_random_{uuid.uuid4().hex[:8]}',
        phase='PHASE25-4-TEST',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='backtest',
        tuning_method='random',
        target_metric='sharpe_ratio',
        n_trials=5,
        base_config_path='configs/paper/phase21_scalping_quick.yml',
        param_space=sample_param_space,
        seed=42
    )
    
    random_tuner = RandomSearchTuner(job_queue=job_queue)
    base_run_id, _ = random_tuner.create_run_and_jobs(random_config)
    
    # 2. Base run의 jobs에 임의 결과 삽입
    import random
    
    sql_get_jobs = """
    SELECT job_id FROM tuning.jobs
    WHERE run_id = %s
    ORDER BY job_index ASC
    LIMIT 5
    """
    
    with db_connection.cursor() as cur:
        cur.execute(sql_get_jobs, (base_run_id,))
        job_ids = [row[0] for row in cur.fetchall()]
    
    # 결과 삽입 (sharpe_ratio 기준으로 정렬 가능하도록)
    for i, job_id in enumerate(job_ids):
        sharpe = random.uniform(0.5, 2.0)
        metrics = {
            'pnl': random.uniform(-100, 500),
            'pnl_pct': random.uniform(-5, 20),
            'sharpe_ratio': sharpe,
            'win_rate': random.uniform(0.3, 0.7),
            'trade_count': random.randint(10, 50)
        }
        
        job_queue.mark_job_completed(job_id, metrics)
    
    # 3. Local Grid Search 실행
    local_config = LocalGridSearchConfig(
        run_name=f'local_grid_{uuid.uuid4().hex[:8]}',
        phase='PHASE25-4-TEST',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='backtest',
        target_metric='sharpe_ratio',
        base_run_id=base_run_id,
        top_k=2,
        grid_steps=3,
        step_factor=0.1,
        base_config_path='configs/paper/phase21_scalping_quick.yml'
    )
    
    local_tuner = LocalGridSearchTuner(job_queue=job_queue)
    local_run_id = local_tuner.create_run_and_jobs(local_config)
    
    assert local_run_id is not None
    
    # 4. 생성된 Run 검증
    run_status = job_queue.get_run_status(local_run_id)
    assert run_status is not None
    assert run_status['status'] == 'PENDING'
    assert run_status['total_jobs'] > 0
    
    # 5. 생성된 Jobs 검증
    sql_count_jobs = """
    SELECT COUNT(*) FROM tuning.jobs
    WHERE run_id = %s
    """
    
    with db_connection.cursor() as cur:
        cur.execute(sql_count_jobs, (local_run_id,))
        job_count = cur.fetchone()[0]
    
    assert job_count > 0
    print(f"✅ Local Grid Run 생성: {local_run_id}")
    print(f"   Base Run: {base_run_id}")
    print(f"   총 Jobs: {job_count}개")


# ============================================
# Test 5: Top K Candidates Retrieval
# ============================================

@pytest.mark.slow
def test_get_top_k_candidates(job_queue, sample_param_space, db_connection):
    """Top K 후보 조회 테스트"""
    
    # Base run 생성
    base_run_id = f"run-topk-{uuid.uuid4().hex[:8]}"
    
    random_config = RandomSearchConfig(
        run_name=f'topk_test_{uuid.uuid4().hex[:8]}',
        phase='PHASE25-4-TEST',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='backtest',
        tuning_method='random',
        target_metric='sharpe_ratio',
        n_trials=10,
        base_config_path='configs/paper/phase21_scalping_quick.yml',
        param_space=sample_param_space,
        seed=99
    )
    
    random_tuner = RandomSearchTuner(job_queue=job_queue)
    base_run_id, _ = random_tuner.create_run_and_jobs(random_config)
    
    # 결과 삽입
    import random
    
    sql_get_jobs = """
    SELECT job_id FROM tuning.jobs
    WHERE run_id = %s
    ORDER BY job_index ASC
    """
    
    with db_connection.cursor() as cur:
        cur.execute(sql_get_jobs, (base_run_id,))
        job_ids = [row[0] for row in cur.fetchall()]
    
    sharpe_values = []
    for job_id in job_ids:
        sharpe = random.uniform(0.5, 3.0)
        sharpe_values.append(sharpe)
        metrics = {
            'sharpe_ratio': sharpe,
            'pnl': random.uniform(-100, 500),
            'win_rate': random.uniform(0.3, 0.7)
        }
        job_queue.mark_job_completed(job_id, metrics)
    
    # Top K 후보 조회
    local_tuner = LocalGridSearchTuner(job_queue=job_queue)
    top_3 = local_tuner._get_top_k_candidates(
        base_run_id=base_run_id,
        target_metric='sharpe_ratio',
        k=3
    )
    
    assert len(top_3) == 3
    
    # Sharpe 값이 내림차순인지 확인
    sharpe_from_top3 = [c['metrics']['sharpe_ratio'] for c in top_3]
    assert sharpe_from_top3 == sorted(sharpe_from_top3, reverse=True)
    
    print(f"✅ Top 3 후보 조회 성공")
    print(f"   Sharpe 값: {sharpe_from_top3}")
    print(f"   최고: {max(sharpe_values):.4f}, Top3 최고: {sharpe_from_top3[0]:.4f}")
