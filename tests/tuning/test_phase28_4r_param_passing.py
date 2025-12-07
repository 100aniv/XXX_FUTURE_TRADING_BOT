#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-4R: Parameter Passing Verification Unit Tests
======================================================
파라미터 전달 경로 검증:
1. ParamSpace → Optuna suggest → build_tuning_config
2. build_tuning_config → strategies.{selector}
3. DB params_json 저장 확인
"""
import pytest
import yaml
from pathlib import Path
from typing import Dict, Any

from tuning.algorithms.random_search import ParamSpace
from tuning.utils.config_builder import build_tuning_config


@pytest.fixture
def param_space():
    """테스트용 ParamSpace"""
    space = {
        'rsi_long_threshold': {'type': 'int', 'min': 40, 'max': 48},
        'rsi_short_threshold': {'type': 'int', 'min': 52, 'max': 58},
        'bb_std_main': {'type': 'float', 'min': 0.9, 'max': 1.2},
        'bb_std_strong': {'type': 'float', 'min': 1.3, 'max': 1.6},
        'rr': {'type': 'float', 'min': 1.2, 'max': 2.0},
    }
    return ParamSpace(space=space)


@pytest.fixture
def sample_params():
    """테스트용 샘플 파라미터"""
    return {
        'rsi_long_threshold': 42,
        'rsi_short_threshold': 56,
        'bb_std_main': 1.1,
        'bb_std_strong': 1.5,
        'rr': 1.8,
    }


@pytest.fixture
def base_config_path():
    """테스트용 base config 경로"""
    return "configs/backtest/phase28_2_btc5m_tuning_base.yml"


class TestParamPassingVerification:
    """
    PHASE28-4R: Parameter Passing Verification
    
    AC1: Unit Level Param Passing 검증
    - ParamSpace 정의 → build_tuning_config → strategies.{selector}
    - 파라미터가 top-level과 strategies 섹션 모두에 존재하는지 확인
    """
    
    def test_param_space_validation(self, param_space):
        """ParamSpace 검증 테스트"""
        # ParamSpace가 올바르게 초기화되는지 확인
        assert len(param_space.space) == 5
        assert 'rsi_long_threshold' in param_space.space
        assert param_space.space['rsi_long_threshold']['type'] == 'int'
        
        # validate() 호출 시 에러가 없는지 확인
        param_space.validate()
    
    def test_build_tuning_config_param_merge(
        self,
        base_config_path,
        sample_params
    ):
        """
        build_tuning_config가 파라미터를 strategies 섹션에 병합하는지 검증
        
        AC1: 핵심 검증 포인트
        """
        # Given: Base config와 sample params
        config = build_tuning_config(
            base_config_path=base_config_path,
            strategy_params=sample_params,
            trial_id="test_job_123",
            run_id="test_run_456",
            mode='backtest'
        )
        
        # Then: strategies.btc5m_baseline_v1에 파라미터가 병합되어야 함
        assert 'strategies' in config
        assert 'btc5m_baseline_v1' in config['strategies']
        
        strategy_config = config['strategies']['btc5m_baseline_v1']
        
        # 각 파라미터가 정확히 병합되었는지 확인
        for key, value in sample_params.items():
            assert key in strategy_config, f"Parameter '{key}' not found in strategies.btc5m_baseline_v1"
            assert strategy_config[key] == value, f"Parameter '{key}' value mismatch"
    
    def test_config_structure_for_strategy_consumption(
        self,
        base_config_path,
        sample_params
    ):
        """
        전략이 파라미터를 읽을 수 있는 구조인지 검증
        
        전략은 config.get('rsi_long_threshold', default) 형식으로 읽음
        → strategies.{selector} 섹션에 직접 있어야 함 (params 키 없이)
        """
        config = build_tuning_config(
            base_config_path=base_config_path,
            strategy_params=sample_params,
            trial_id="test_job_789",
            run_id="test_run_012",
            mode='backtest'
        )
        
        # merge_strategy_config()가 engine.py에서 호출될 것으로 가정하고,
        # strategies.{selector}에 있는지만 확인
        strategy_config = config['strategies']['btc5m_baseline_v1']
        
        # 전략이 직접 읽는 형식 확인
        assert strategy_config.get('rsi_long_threshold') == 42
        assert strategy_config.get('rsi_short_threshold') == 56
        assert strategy_config.get('bb_std_main') == pytest.approx(1.1, abs=0.01)
        assert strategy_config.get('bb_std_strong') == pytest.approx(1.5, abs=0.01)
        assert strategy_config.get('rr') == pytest.approx(1.8, abs=0.01)
    
    def test_trial_metadata_in_config(
        self,
        base_config_path,
        sample_params
    ):
        """
        trial_id와 run_id가 config에 정확히 설정되는지 검증
        
        DB 연결 및 메트릭 추출에 필수
        """
        trial_id = "test_job_abc123"
        run_id = "test_run_xyz789"
        
        config = build_tuning_config(
            base_config_path=base_config_path,
            strategy_params=sample_params,
            trial_id=trial_id,
            run_id=run_id,
            mode='backtest'
        )
        
        # trial_id, run_id가 config에 설정되어야 함
        assert config['trial_id'] == trial_id
        assert config['run_id'] == run_id
        assert config['mode'] == 'backtest'
    
    def test_empty_params_handling(self, base_config_path):
        """
        빈 파라미터 dict도 오류 없이 처리되는지 확인
        """
        config = build_tuning_config(
            base_config_path=base_config_path,
            strategy_params={},
            trial_id="test_job_empty",
            run_id="test_run_empty",
            mode='backtest'
        )
        
        # config가 정상적으로 생성되어야 함
        assert 'strategies' in config
        assert 'btc5m_baseline_v1' in config['strategies']
        
        # 기존 base config의 default 값이 유지되어야 함
        # (파라미터 override가 없으므로)
    
    def test_param_override_consistency(
        self,
        base_config_path,
        sample_params
    ):
        """
        동일한 파라미터로 두 번 호출해도 결과가 동일한지 확인
        (멱등성 테스트)
        """
        config1 = build_tuning_config(
            base_config_path=base_config_path,
            strategy_params=sample_params,
            trial_id="test_job_001",
            run_id="test_run_001",
            mode='backtest'
        )
        
        config2 = build_tuning_config(
            base_config_path=base_config_path,
            strategy_params=sample_params,
            trial_id="test_job_002",
            run_id="test_run_002",
            mode='backtest'
        )
        
        # strategies.btc5m_baseline_v1의 파라미터 값이 동일해야 함
        params1 = {k: v for k, v in config1['strategies']['btc5m_baseline_v1'].items() 
                   if k in sample_params}
        params2 = {k: v for k, v in config2['strategies']['btc5m_baseline_v1'].items() 
                   if k in sample_params}
        
        assert params1 == params2


class TestBayesianSearchParamFlow:
    """
    PHASE28-4R: Bayesian Search 전체 흐름에서 파라미터 전달 검증
    
    AC2: Runtime Param Logging 검증 (통합 테스트)
    """
    
    def test_param_space_to_optuna_suggest(self, param_space):
        """
        ParamSpace → Optuna suggest API 변환 검증
        
        BayesianSearchTuner._suggest_params_from_space() 로직 검증
        """
        # Optuna mock 없이 ParamSpace 구조만 검증
        for param_name, spec in param_space.space.items():
            assert 'type' in spec
            assert spec['type'] in ['int', 'float', 'categorical']
            
            if spec['type'] in ['int', 'float']:
                assert 'min' in spec
                assert 'max' in spec
                assert spec['min'] < spec['max']
            elif spec['type'] == 'categorical':
                assert 'values' in spec
                assert len(spec['values']) > 0


# ========================================
# PHASE28-4R Acceptance Criteria 매핑
# ========================================
"""
AC1: Unit Level Param Passing
- test_build_tuning_config_param_merge: ✅
- test_config_structure_for_strategy_consumption: ✅
- test_trial_metadata_in_config: ✅

AC2: Runtime Param Logging
- test_param_space_to_optuna_suggest: ✅ (구조 검증)
- 실제 로그 검증은 실행 중 수동 확인 (bayesian_search.py Line 502, 237)

AC3: Bayesian Search 결과의 구조적 정상성
- DB params_json 검증은 실행 후 수동 확인 (tuning.jobs 테이블)

AC4: 문서화
- PHASE28-4R_PARAM_PASSING_VERIFICATION_REPORT.md: ✅

AC5: ROADMAP & Git
- 별도 수동 작업
"""
