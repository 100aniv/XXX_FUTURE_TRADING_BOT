#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-4: Bayesian Search Round 1 - Unit Tests
================================================
Bayesian Search 자동화 스크립트 및 Top-N 후보 선정 로직 테스트
"""
import sys
import os
import json
import tempfile
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
import yaml


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
# Test: Config Loading
# ========================================

def test_load_config():
    """Config YAML 로딩 테스트"""
    config_path = project_root / "configs" / "tuning" / "phase28_4_btc5m_bayesian_search.yml"
    
    assert config_path.exists(), f"Config not found: {config_path}"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    assert config is not None
    assert 'run_metadata' in config
    assert 'bayesian_search' in config
    assert 'market_periods' in config
    assert config['run_metadata']['phase'] == "PHASE28-4"


def test_load_param_space():
    """ParamSpace YAML 로딩 테스트"""
    from tuning.algorithms.random_search import ParamSpace
    
    ps_path = project_root / "configs" / "tuning" / "phase28_2_btc5m_baseline_paramspace.yml"
    
    assert ps_path.exists(), f"ParamSpace YAML not found: {ps_path}"
    
    with open(ps_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    param_space_dict = data.get('param_space', {})
    assert len(param_space_dict) > 0
    
    param_space = ParamSpace(space=param_space_dict)
    param_space.validate()
    
    # 샘플링 테스트
    params = param_space.sample(seed=84)
    assert isinstance(params, dict)
    assert len(params) == len(param_space_dict)


# ========================================
# Test: Top-N Candidate Selection
# ========================================

def test_select_top_n_candidates_with_sample_data():
    """Top-N 후보 추출 테스트 (샘플 데이터)"""
    from tuning.utils.result_selection import select_top_n_candidates
    
    # 샘플 JSON 생성
    sample_data = {
        "phase": "PHASE28-3",
        "execution_time": "2025-12-06T14:59:30",
        "summary": {"total_trials": 5, "passed_trials": 5, "filtered_trials": 0},
        "passed_trials": [
            {
                "run_id": "test_run_1",
                "job_id": "job_1",
                "trade_count": 10,
                "pnl": 50.0,
                "pnl_pct": 0.05,
                "sharpe_ratio": 2.5,
                "win_rate": 0.6,
                "max_drawdown": -10.0,
                "params": {
                    "rsi_long_threshold": 44,
                    "rsi_short_threshold": 55,
                    "bb_std_main": 1.0,
                    "bb_std_strong": 1.5,
                    "atr_mult_sl": 1.2,
                    "rr": 1.5
                }
            },
            {
                "run_id": "test_run_2",
                "job_id": "job_2",
                "trade_count": 8,
                "pnl": 30.0,
                "pnl_pct": 0.03,
                "sharpe_ratio": 1.8,
                "win_rate": 0.5,
                "max_drawdown": -12.0,
                "params": {
                    "rsi_long_threshold": 45,
                    "rsi_short_threshold": 54,
                    "bb_std_main": 1.1,
                    "bb_std_strong": 1.6,
                    "atr_mult_sl": 1.3,
                    "rr": 1.6
                }
            },
            {
                "run_id": "test_run_3",
                "job_id": "job_3",
                "trade_count": 6,
                "pnl": 10.0,
                "pnl_pct": 0.01,
                "sharpe_ratio": 0.5,
                "win_rate": 0.4,
                "max_drawdown": -8.0,
                "params": {
                    "rsi_long_threshold": 42,
                    "rsi_short_threshold": 56,
                    "bb_std_main": 0.9,
                    "bb_std_strong": 1.4,
                    "atr_mult_sl": 1.1,
                    "rr": 1.4
                }
            },
            {
                "run_id": "test_run_4",
                "job_id": "job_4",
                "trade_count": 3,  # 최소 거래 수 미달
                "pnl": -20.0,
                "pnl_pct": -0.02,
                "sharpe_ratio": -0.5,
                "win_rate": 0.3,
                "max_drawdown": -15.0,
                "params": {
                    "rsi_long_threshold": 40,
                    "rsi_short_threshold": 58,
                    "bb_std_main": 0.8,
                    "bb_std_strong": 1.3,
                    "atr_mult_sl": 1.0,
                    "rr": 1.3
                }
            },
            {
                "run_id": "test_run_5",
                "job_id": "job_5",
                "trade_count": 12,
                "pnl": -100.0,
                "pnl_pct": -0.10,
                "sharpe_ratio": -5.0,
                "win_rate": 0.2,
                "max_drawdown": -25.0,  # MaxDD 임계 초과
                "params": {
                    "rsi_long_threshold": 48,
                    "rsi_short_threshold": 52,
                    "bb_std_main": 1.2,
                    "bb_std_strong": 1.7,
                    "atr_mult_sl": 1.5,
                    "rr": 1.7
                }
            }
        ]
    }
    
    # 임시 JSON 파일 생성
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(sample_data, f)
        temp_json_path = f.name
    
    try:
        # Top-N 추출
        candidates = select_top_n_candidates(
            results_json_path=temp_json_path,
            top_n=3,
            min_trades=5,
            max_drawdown_threshold=-20.0
        )
        
        # 검증
        assert len(candidates) > 0, "Candidates should not be empty"
        assert len(candidates) <= 3, "Should return at most 3 candidates"
        
        # 필터링 확인: job_4(거래 수 3)와 job_5(MaxDD -25%) 제외되어야 함
        job_ids = [c['job_id'] for c in candidates]
        assert 'job_4' not in job_ids, "job_4 should be filtered out (trade_count < 5)"
        assert 'job_5' not in job_ids, "job_5 should be filtered out (MaxDD < -20%)"
        
        # 스코어 순서 확인 (내림차순)
        scores = [c['score'] for c in candidates]
        assert scores == sorted(scores, reverse=True), "Candidates should be sorted by score (desc)"
        
        # job_1이 최상위여야 함 (Sharpe 2.5, PnL 50.0)
        assert candidates[0]['job_id'] == 'job_1', "job_1 should be top candidate"
        
    finally:
        # 임시 파일 삭제
        os.unlink(temp_json_path)


def test_calculate_score():
    """스코어 계산 함수 테스트"""
    from tuning.utils.result_selection import calculate_score
    
    # 좋은 trial
    trial_good = {
        'trade_count': 15,
        'pnl': 100.0,
        'sharpe_ratio': 3.0,
        'max_drawdown': -10.0
    }
    score_good = calculate_score(trial_good, min_trades=10)
    assert score_good > 0
    
    # 나쁜 trial (거래 수 부족)
    trial_bad_trades = {
        'trade_count': 5,
        'pnl': 50.0,
        'sharpe_ratio': 2.0,
        'max_drawdown': -10.0
    }
    score_bad_trades = calculate_score(trial_bad_trades, min_trades=10)
    assert score_bad_trades < score_good  # 패널티로 인해 점수 낮음
    
    # 나쁜 trial (과도한 MaxDD)
    trial_bad_dd = {
        'trade_count': 15,
        'pnl': 100.0,
        'sharpe_ratio': 3.0,
        'max_drawdown': -20.0
    }
    score_bad_dd = calculate_score(trial_bad_dd, min_trades=10)
    assert score_bad_dd < score_good  # 패널티로 인해 점수 낮음


def test_is_similar_params():
    """파라미터 유사도 판단 테스트"""
    from tuning.utils.result_selection import is_similar_params
    
    params1 = {
        'rsi_long_threshold': 44,
        'rsi_short_threshold': 55,
        'bb_std_main': 1.0,
        'bb_std_strong': 1.5,
        'atr_mult_sl': 1.2,
        'rr': 1.5
    }
    
    # 유사한 파라미터 (int ±2, float ±0.2 이내)
    params2 = {
        'rsi_long_threshold': 45,  # +1 (유사)
        'rsi_short_threshold': 56,  # +1 (유사)
        'bb_std_main': 1.1,  # +0.1 (유사)
        'bb_std_strong': 1.6,  # +0.1 (유사)
        'atr_mult_sl': 1.3,  # +0.1 (유사)
        'rr': 1.6  # +0.1 (유사)
    }
    assert is_similar_params(params1, params2), "Should be similar"
    
    # 상이한 파라미터 (int ±2 초과)
    params3 = {
        'rsi_long_threshold': 40,  # -4 (상이)
        'rsi_short_threshold': 55,
        'bb_std_main': 1.0,
        'bb_std_strong': 1.5,
        'atr_mult_sl': 1.2,
        'rr': 1.5
    }
    assert not is_similar_params(params1, params3), "Should not be similar"
    
    # 상이한 파라미터 (float ±0.2 초과)
    params4 = {
        'rsi_long_threshold': 44,
        'rsi_short_threshold': 55,
        'bb_std_main': 1.5,  # +0.5 (상이)
        'bb_std_strong': 1.5,
        'atr_mult_sl': 1.2,
        'rr': 1.5
    }
    assert not is_similar_params(params1, params4), "Should not be similar"


# ========================================
# Test: Bayesian Objective Function
# ========================================

def test_bayesian_objective_penalty():
    """Bayesian objective 함수 패널티 로직 테스트 (개념 검증)"""
    # 실제 objective 함수는 BayesianSearchTuner 내부에 있지만,
    # 여기서는 패널티 로직의 개념을 검증
    
    # Base score
    base_score = 2.0  # Sharpe ratio
    
    # Penalty: 거래 수 부족
    trade_count = 5
    min_trades = 10
    trade_penalty = (min_trades - trade_count) * 2.0 if trade_count < min_trades else 0.0
    
    # Penalty: MaxDD 초과
    max_dd = -20.0
    max_allowed_dd = -15.0
    dd_penalty = (abs(max_dd) - abs(max_allowed_dd)) * 50.0 if max_dd < max_allowed_dd else 0.0
    
    # Final score
    final_score = base_score - trade_penalty - dd_penalty
    
    # 검증
    assert trade_penalty == 10.0, f"Expected 10.0, got {trade_penalty}"
    assert dd_penalty == 250.0, f"Expected 250.0, got {dd_penalty}"
    assert final_score < base_score, "Final score should be lower due to penalties"
    assert final_score == 2.0 - 10.0 - 250.0, "Final score calculation incorrect"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
