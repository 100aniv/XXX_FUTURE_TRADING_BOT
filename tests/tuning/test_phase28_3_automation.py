#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-3: Automation Script Tests
===================================
phase28_3_run_random_search_round1.py 자동화 스크립트 테스트
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest


# ========================================
# Test: Environment Check
# ========================================

def test_environment_check_python_version():
    """Python 버전이 3.9 이상인지 확인"""
    assert sys.version_info >= (3, 9), "Python 3.9+ required"


def test_environment_check_db_connection():
    """Postgres 연결 확인"""
    from database import get_db_connection
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                assert result[0] == 1
    except Exception as e:
        pytest.fail(f"DB connection failed: {e}")


# ========================================
# Test: ParamSpace Loading
# ========================================

def test_load_param_space():
    """ParamSpace YAML 로딩 테스트"""
    from tuning.algorithms.random_search import ParamSpace
    import yaml
    
    yaml_path = project_root / "configs" / "tuning" / "phase28_2_btc5m_baseline_paramspace.yml"
    
    assert yaml_path.exists(), f"ParamSpace YAML not found: {yaml_path}"
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    param_space_dict = data.get('param_space', {})
    assert len(param_space_dict) > 0, "param_space is empty"
    
    param_space = ParamSpace(space=param_space_dict)
    param_space.validate()
    
    # 샘플링 테스트
    params = param_space.sample(seed=42)
    assert isinstance(params, dict)
    assert len(params) == len(param_space_dict)


# ========================================
# Test: Run ID Generation
# ========================================

def test_run_id_generation():
    """Run ID 생성 및 uniqueness 확인"""
    from scripts.tuning.phase28_3_run_random_search_round1 import generate_run_id
    
    # 같은 base_name, 다른 시간 → 다른 run_id
    run_id_1 = generate_run_id("test_run")
    import time
    time.sleep(0.01)  # 시간 차이
    run_id_2 = generate_run_id("test_run")
    
    assert run_id_1 != run_id_2, "Run IDs should be unique"
    assert "test_run" in run_id_1
    assert "test_run" in run_id_2


# ========================================
# Test: Job Submission (Smoke)
# ========================================

def test_job_submission_smoke():
    """Job 제출 스모크 테스트 (DB 쓰기 확인)"""
    from tuning.algorithms.random_search import ParamSpace, RandomSearchConfig, RandomSearchTuner
    from database import get_db_connection
    import yaml
    
    # ParamSpace 로딩
    yaml_path = project_root / "configs" / "tuning" / "phase28_2_btc5m_baseline_paramspace.yml"
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    param_space_dict = data.get('param_space', {})
    param_space = ParamSpace(space=param_space_dict)
    
    # Base config
    base_config_path = str(project_root / "configs" / "backtest" / "phase28_2_btc5m_tuning_base.yml")
    
    # RandomSearchConfig
    run_name = f"test_smoke_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    config = RandomSearchConfig(
        run_name=run_name,
        phase="TEST",
        strategy_family="baseline",
        strategy_name="btc5m_baseline_v1",
        mode="backtest",
        tuning_method="random",
        target_metric="sharpe_like_ratio",
        n_trials=1,  # 스모크 테스트: 1 trial만
        base_config_path=base_config_path,
        param_space=param_space,
        seed=42
    )
    
    # Job 제출
    tuner = RandomSearchTuner()
    run_id, job_ids = tuner.create_run_and_jobs(config)
    
    assert run_id is not None
    assert len(job_ids) == 1
    
    # DB 확인
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Run 존재 확인
            cur.execute("SELECT run_id FROM tuning.runs WHERE run_id = %s", (run_id,))
            run_row = cur.fetchone()
            assert run_row is not None
            
            # Job 존재 확인
            cur.execute("SELECT job_id FROM tuning.jobs WHERE job_id = %s", (job_ids[0],))
            job_row = cur.fetchone()
            assert job_row is not None
    
    # 정리 (테스트 데이터 삭제)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tuning.jobs WHERE run_id = %s", (run_id,))
            cur.execute("DELETE FROM tuning.runs WHERE run_id = %s", (run_id,))


# ========================================
# Test: Result Aggregation (Mock)
# ========================================

def test_result_aggregation_empty():
    """빈 결과에 대한 집계 테스트"""
    from scripts.tuning.phase28_3_run_random_search_round1 import aggregate_results
    
    # 존재하지 않는 run_id (빈 결과)
    run_ids = ["nonexistent_run_id_12345"]
    aggregation = aggregate_results(run_ids, top_n=10)
    
    assert aggregation['total_valid_results'] == 0
    assert len(aggregation['overall_top_n']) == 0


# ========================================
# Test: Report Generation (Mock)
# ========================================

def test_markdown_report_generation():
    """Markdown 리포트 생성 테스트 (mock data)"""
    from scripts.tuning.phase28_3_run_random_search_round1 import generate_markdown_report
    import tempfile
    
    # Mock aggregation
    mock_aggregation = {
        'overall_top_n': [
            ('run_1', 'job_1', 100.0, 5.0, 1.5, 20, 0.6, 10.0, {'rsi': 45}, datetime.now())
        ],
        'period_top_n': {
            'bull': [
                ('run_1', 'job_1', 100.0, 5.0, 1.5, 20, 0.6, 10.0, {'rsi': 45}, datetime.now())
            ]
        },
        'all_results': [],
        'total_valid_results': 1,
        'generated_at': datetime.now().isoformat()
    }
    
    # Temp file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        temp_path = f.name
    
    try:
        generate_markdown_report(mock_aggregation, temp_path)
        
        # 파일 존재 확인
        assert Path(temp_path).exists()
        
        # 내용 확인
        with open(temp_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "PHASE28-3" in content
            assert "Overall Top" in content
            assert "job_1" in content
    finally:
        # 정리
        if Path(temp_path).exists():
            Path(temp_path).unlink()


def test_json_results_generation():
    """JSON 결과 생성 테스트 (mock data)"""
    from scripts.tuning.phase28_3_run_random_search_round1 import generate_json_results
    import tempfile
    import json
    
    # Mock aggregation
    mock_aggregation = {
        'overall_top_n': [
            ('run_1', 'job_1', 100.0, 5.0, 1.5, 20, 0.6, 10.0, {'rsi': 45}, datetime.now())
        ],
        'period_top_n': {
            'bull': [
                ('run_1', 'job_1', 100.0, 5.0, 1.5, 20, 0.6, 10.0, {'rsi': 45}, datetime.now())
            ]
        },
        'all_results': [],
        'total_valid_results': 1,
        'generated_at': datetime.now().isoformat()
    }
    
    # Temp file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name
    
    try:
        generate_json_results(mock_aggregation, temp_path)
        
        # 파일 존재 확인
        assert Path(temp_path).exists()
        
        # JSON 파싱 확인
        with open(temp_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert 'overall_top_n' in data
            assert 'period_top_n' in data
            assert data['total_valid_results'] == 1
    finally:
        # 정리
        if Path(temp_path).exists():
            Path(temp_path).unlink()


# ========================================
# pytest 실행
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
