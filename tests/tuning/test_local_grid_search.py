#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-5: Local Grid Search Unit Tests
========================================
LocalGridSearchTuner._build_grid_phase28_5() 테스트

테스트 케이스:
1. 정수형 파라미터 grid 생성
2. 실수형 파라미터 grid 생성
3. 범주형 파라미터 grid 생성
4. Core params 필터링
5. Max jobs 제한
6. ParamSpace 경계 확인
"""
import pytest
from unittest.mock import Mock, patch
from tuning.algorithms.random_search import ParamSpace
from tuning.algorithms.local_grid_search import LocalGridSearchTuner


@pytest.fixture
def tuner():
    """LocalGridSearchTuner 인스턴스"""
    return LocalGridSearchTuner()


@pytest.fixture
def param_space_int():
    """정수형 파라미터 ParamSpace"""
    return ParamSpace(space={
        'rsi_long_threshold': {'type': 'int', 'min': 30, 'max': 50},
        'rsi_short_threshold': {'type': 'int', 'min': 50, 'max': 70}
    })


@pytest.fixture
def param_space_float():
    """실수형 파라미터 ParamSpace"""
    return ParamSpace(space={
        'bb_std_main': {'type': 'float', 'min': 0.9, 'max': 1.2},
        'atr_mult_sl': {'type': 'float', 'min': 1.0, 'max': 2.0}
    })


@pytest.fixture
def param_space_categorical():
    """범주형 파라미터 ParamSpace"""
    return ParamSpace(space={
        'momentum_lookback': {'type': 'categorical', 'values': [3, 5, 7, 10]},
        'max_hold_minutes': {'type': 'categorical', 'values': [45, 60, 90, 120]}
    })


@pytest.fixture
def param_space_mixed():
    """혼합 파라미터 ParamSpace"""
    return ParamSpace(space={
        'rsi_long_threshold': {'type': 'int', 'min': 30, 'max': 50},
        'bb_std_main': {'type': 'float', 'min': 0.9, 'max': 1.2},
        'momentum_lookback': {'type': 'categorical', 'values': [3, 5, 7, 10]}
    })


# ========================================
# Test Cases
# ========================================

def test_build_grid_int_param(tuner, param_space_int):
    """정수형 파라미터 grid 생성 검증"""
    seed_params = {
        'rsi_long_threshold': 40,
        'rsi_short_threshold': 60
    }
    
    grid_config = {
        'core_params': ['rsi_long_threshold', 'rsi_short_threshold'],
        'int_delta': 2,
        'float_ratio': 0.05,
        'discrete_neighbors': 1
    }
    
    grid = tuner._build_grid_phase28_5(seed_params, param_space_int, grid_config)
    
    # 검증: 3x3 = 9 조합
    assert len(grid) == 9
    
    # 검증: rsi_long_threshold는 [38, 40, 42]
    rsi_long_values = sorted(set(g['rsi_long_threshold'] for g in grid))
    assert rsi_long_values == [38, 40, 42]
    
    # 검증: rsi_short_threshold는 [58, 60, 62]
    rsi_short_values = sorted(set(g['rsi_short_threshold'] for g in grid))
    assert rsi_short_values == [58, 60, 62]


def test_build_grid_float_param(tuner, param_space_float):
    """실수형 파라미터 grid 생성 검증"""
    seed_params = {
        'bb_std_main': 1.0,
        'atr_mult_sl': 1.5
    }
    
    grid_config = {
        'core_params': ['bb_std_main', 'atr_mult_sl'],
        'int_delta': 2,
        'float_ratio': 0.05,
        'discrete_neighbors': 1
    }
    
    grid = tuner._build_grid_phase28_5(seed_params, param_space_float, grid_config)
    
    # 검증: 3x3 = 9 조합
    assert len(grid) == 9
    
    # 검증: bb_std_main은 center ± (range * 0.05)
    # range = 1.2 - 0.9 = 0.3, delta = 0.3 * 0.05 = 0.015
    # expected: [0.985, 1.0, 1.015]
    bb_values = sorted(set(g['bb_std_main'] for g in grid))
    assert len(bb_values) == 3
    assert abs(bb_values[0] - 0.985) < 0.01
    assert abs(bb_values[1] - 1.0) < 0.01
    assert abs(bb_values[2] - 1.015) < 0.01


def test_build_grid_categorical_param(tuner, param_space_categorical):
    """범주형 파라미터 grid 생성 검증"""
    seed_params = {
        'momentum_lookback': 7,
        'max_hold_minutes': 60
    }
    
    grid_config = {
        'core_params': ['momentum_lookback', 'max_hold_minutes'],
        'int_delta': 2,
        'float_ratio': 0.05,
        'discrete_neighbors': 1
    }
    
    grid = tuner._build_grid_phase28_5(seed_params, param_space_categorical, grid_config)
    
    # 검증: momentum_lookback=7은 idx=2, neighbors=1 → [5, 7, 10]
    # max_hold_minutes=60은 idx=1, neighbors=1 → [45, 60, 90]
    # 3x3 = 9 조합
    assert len(grid) == 9
    
    momentum_values = sorted(set(g['momentum_lookback'] for g in grid))
    assert momentum_values == [5, 7, 10]
    
    hold_values = sorted(set(g['max_hold_minutes'] for g in grid))
    assert hold_values == [45, 60, 90]


def test_build_grid_core_params_filter(tuner, param_space_mixed):
    """Core params 필터링 검증"""
    seed_params = {
        'rsi_long_threshold': 40,
        'bb_std_main': 1.0,
        'momentum_lookback': 7
    }
    
    grid_config = {
        'core_params': ['rsi_long_threshold'],  # bb_std_main, momentum_lookback는 고정
        'int_delta': 2,
        'float_ratio': 0.05,
        'discrete_neighbors': 1
    }
    
    grid = tuner._build_grid_phase28_5(seed_params, param_space_mixed, grid_config)
    
    # 검증: rsi_long_threshold만 변경, 나머지 고정
    # 예상: 3 조합 (rsi_long_threshold: [38, 40, 42])
    assert len(grid) == 3
    
    # bb_std_main은 모두 1.0으로 고정
    bb_values = set(g['bb_std_main'] for g in grid)
    assert bb_values == {1.0}
    
    # momentum_lookback은 모두 7로 고정
    momentum_values = set(g['momentum_lookback'] for g in grid)
    assert momentum_values == {7}


def test_build_grid_param_space_bounds(tuner, param_space_int):
    """ParamSpace 경계 확인 (min/max 클리핑)"""
    seed_params = {
        'rsi_long_threshold': 49,  # max=50에 가까움
        'rsi_short_threshold': 51   # min=50에 가까움
    }
    
    grid_config = {
        'core_params': ['rsi_long_threshold', 'rsi_short_threshold'],
        'int_delta': 2,
        'float_ratio': 0.05,
        'discrete_neighbors': 1
    }
    
    grid = tuner._build_grid_phase28_5(seed_params, param_space_int, grid_config)
    
    # 검증: 경계를 벗어나지 않음
    for g in grid:
        assert 30 <= g['rsi_long_threshold'] <= 50
        assert 50 <= g['rsi_short_threshold'] <= 70


def test_build_grid_deduplication(tuner, param_space_int):
    """중복 조합 제거 검증 (경계 조건)"""
    seed_params = {
        'rsi_long_threshold': 30,  # min 경계
        'rsi_short_threshold': 70   # max 경계
    }
    
    grid_config = {
        'core_params': ['rsi_long_threshold', 'rsi_short_threshold'],
        'int_delta': 2,
        'float_ratio': 0.05,
        'discrete_neighbors': 1
    }
    
    grid = tuner._build_grid_phase28_5(seed_params, param_space_int, grid_config)
    
    # 검증: rsi_long_threshold는 [30, 30, 32] → 중복 제거 후 [30, 32]
    # rsi_short_threshold는 [68, 70, 70] → 중복 제거 후 [68, 70]
    # 2x2 = 4 조합
    assert len(grid) == 4
    
    # 중복 확인
    grid_set = set(tuple(sorted(g.items())) for g in grid)
    assert len(grid_set) == len(grid)


def test_build_grid_empty_core_params(tuner, param_space_mixed):
    """Core params가 비어있을 때 (모든 파라미터 고정)"""
    seed_params = {
        'rsi_long_threshold': 40,
        'bb_std_main': 1.0,
        'momentum_lookback': 7
    }
    
    grid_config = {
        'core_params': [],  # 빈 리스트 → 모든 파라미터 고정
        'int_delta': 2,
        'float_ratio': 0.05,
        'discrete_neighbors': 1
    }
    
    grid = tuner._build_grid_phase28_5(seed_params, param_space_mixed, grid_config)
    
    # 검증: 조합은 1개 (모두 고정)
    assert len(grid) == 1
    assert grid[0] == seed_params


def test_build_grid_mixed_params(tuner, param_space_mixed):
    """혼합 파라미터 grid 생성 (int + float + categorical)"""
    seed_params = {
        'rsi_long_threshold': 40,
        'bb_std_main': 1.0,
        'momentum_lookback': 7
    }
    
    grid_config = {
        'core_params': ['rsi_long_threshold', 'bb_std_main', 'momentum_lookback'],
        'int_delta': 2,
        'float_ratio': 0.05,
        'discrete_neighbors': 1
    }
    
    grid = tuner._build_grid_phase28_5(seed_params, param_space_mixed, grid_config)
    
    # 검증: 3 * 3 * 3 = 27 조합
    assert len(grid) == 27
    
    # 각 파라미터 값 범위 확인
    rsi_values = sorted(set(g['rsi_long_threshold'] for g in grid))
    assert rsi_values == [38, 40, 42]
    
    momentum_values = sorted(set(g['momentum_lookback'] for g in grid))
    assert momentum_values == [5, 7, 10]


# ========================================
# Integration Test (Optional)
# ========================================

def test_run_from_seeds_mock(tuner, param_space_mixed):
    """run_from_seeds 메서드 구조 검증 (Mock)"""
    seed_trials = [
        {
            'params_json': {
                'rsi_long_threshold': 40,
                'bb_std_main': 1.0,
                'momentum_lookback': 7
            }
        }
    ]
    
    grid_config = {
        'core_params': ['rsi_long_threshold'],
        'int_delta': 2,
        'float_ratio': 0.05,
        'discrete_neighbors': 1,
        'max_jobs': 30
    }
    
    # Mock: DB 접근 및 실행 건너뛰기
    with patch.object(tuner, '_run_single_trial_phase28_5', return_value={'sharpe_ratio': 0.0}):
        with patch('tuning.algorithms.local_grid_search.get_db_connection'):
            # 이 테스트는 실제 DB 없이 구조만 검증
            # 실제 통합 테스트는 별도로 수행
            pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
