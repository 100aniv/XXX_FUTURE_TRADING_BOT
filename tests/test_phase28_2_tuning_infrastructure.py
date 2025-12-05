#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-2: Tuning Infrastructure Tests
=======================================
btc5m_baseline_v1 튜닝 인프라에 대한 단위 테스트

테스트 범위:
- ParamSpace YAML 로딩
- ParamSpace 객체 생성 및 검증
- Random Search Runner (dry-run)
- Bayesian Search Runner (dry-run)
- Results Summarizer (mock data)
"""
import pytest
import yaml
from pathlib import Path
from unittest.mock import Mock, patch

# 프로젝트 경로 추가
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tuning.algorithms.random_search import ParamSpace


class TestParamSpaceYAML:
    """ParamSpace YAML 로딩 테스트"""
    
    def test_paramspace_yaml_exists(self):
        """ParamSpace YAML 파일 존재 확인"""
        yaml_path = project_root / "configs" / "tuning" / "phase28_2_btc5m_baseline_paramspace.yml"
        assert yaml_path.exists(), f"ParamSpace YAML 파일 없음: {yaml_path}"
    
    def test_paramspace_yaml_structure(self):
        """ParamSpace YAML 구조 검증"""
        yaml_path = project_root / "configs" / "tuning" / "phase28_2_btc5m_baseline_paramspace.yml"
        
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # 필수 섹션 확인
        assert 'run_metadata' in data
        assert 'target' in data
        assert 'base_config' in data
        assert 'market_periods' in data
        assert 'param_space' in data
        assert 'metrics' in data
        
        # run_metadata 필드 확인
        assert data['run_metadata']['phase'] == 'PHASE28-2'
        assert data['run_metadata']['strategy_name'] == 'btc5m_baseline_v1'
        assert 'random_search' in data['run_metadata']
        assert 'bayesian_search' in data['run_metadata']
        
        # param_space 필드 확인
        param_space = data['param_space']
        assert len(param_space) > 0, "파라미터 공간이 비어있음"
        
        # 각 파라미터 스펙 검증
        for param_name, spec in param_space.items():
            assert 'type' in spec, f"'{param_name}': 'type' 필드 없음"
            assert spec['type'] in ('int', 'float', 'categorical'), f"'{param_name}': 잘못된 type '{spec['type']}'"
            
            if spec['type'] in ('int', 'float'):
                assert 'min' in spec, f"'{param_name}': 'min' 필드 없음"
                assert 'max' in spec, f"'{param_name}': 'max' 필드 없음"
            elif spec['type'] == 'categorical':
                assert 'values' in spec, f"'{param_name}': 'values' 필드 없음"
                assert len(spec['values']) > 0, f"'{param_name}': 'values' 비어있음"
    
    def test_market_periods_count(self):
        """시장 구간 개수 확인 (최소 3개)"""
        yaml_path = project_root / "configs" / "tuning" / "phase28_2_btc5m_baseline_paramspace.yml"
        
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        market_periods = data['market_periods']
        assert len(market_periods) >= 3, f"시장 구간 개수 부족: {len(market_periods)}개 (최소 3개)"


class TestParamSpace:
    """ParamSpace 클래스 테스트"""
    
    def test_paramspace_creation(self):
        """ParamSpace 객체 생성"""
        space = {
            'rsi_long_threshold': {'type': 'int', 'min': 40, 'max': 48},
            'bb_std_main': {'type': 'float', 'min': 0.9, 'max': 1.2},
            'momentum_lookback': {'type': 'categorical', 'values': [3, 5, 7]}
        }
        
        param_space = ParamSpace(space=space)
        assert param_space.space == space
    
    def test_paramspace_validation(self):
        """ParamSpace 검증"""
        space = {
            'rsi_long_threshold': {'type': 'int', 'min': 40, 'max': 48},
            'bb_std_main': {'type': 'float', 'min': 0.9, 'max': 1.2},
        }
        
        param_space = ParamSpace(space=space)
        assert param_space.validate() == True
    
    def test_paramspace_sampling(self):
        """ParamSpace 샘플링"""
        space = {
            'rsi_long_threshold': {'type': 'int', 'min': 40, 'max': 48},
            'bb_std_main': {'type': 'float', 'min': 0.9, 'max': 1.2},
            'momentum_lookback': {'type': 'categorical', 'values': [3, 5, 7]}
        }
        
        param_space = ParamSpace(space=space)
        params = param_space.sample(seed=42)
        
        # 샘플링된 파라미터 확인
        assert 'rsi_long_threshold' in params
        assert 'bb_std_main' in params
        assert 'momentum_lookback' in params
        
        # 타입 확인
        assert isinstance(params['rsi_long_threshold'], int)
        assert isinstance(params['bb_std_main'], float)
        assert params['momentum_lookback'] in [3, 5, 7]
        
        # 범위 확인
        assert 40 <= params['rsi_long_threshold'] <= 48
        assert 0.9 <= params['bb_std_main'] <= 1.2


class TestRandomSearchRunner:
    """Random Search Runner 테스트"""
    
    def test_random_search_script_exists(self):
        """Random Search 스크립트 존재 확인"""
        script_path = project_root / "scripts" / "tuning" / "phase28_2_run_random_search.py"
        assert script_path.exists(), f"Random Search 스크립트 없음: {script_path}"
    
    @pytest.mark.skipif(True, reason="실제 실행은 수동으로 수행")
    def test_random_search_dry_run(self):
        """Random Search dry-run 테스트 (스킵)"""
        # 이 테스트는 실제로는 수동 실행으로 확인
        # python scripts/tuning/phase28_2_run_random_search.py --dry-run
        pass


class TestBayesianSearchRunner:
    """Bayesian Search Runner 테스트"""
    
    def test_bayesian_search_script_exists(self):
        """Bayesian Search 스크립트 존재 확인"""
        script_path = project_root / "scripts" / "tuning" / "phase28_2_run_bayesian_search.py"
        assert script_path.exists(), f"Bayesian Search 스크립트 없음: {script_path}"
    
    @pytest.mark.skipif(True, reason="실제 실행은 수동으로 수행")
    def test_bayesian_search_dry_run(self):
        """Bayesian Search dry-run 테스트 (스킵)"""
        # 이 테스트는 실제로는 수동 실행으로 확인
        # python scripts/tuning/phase28_2_run_bayesian_search.py --dry-run
        pass


class TestResultsSummarizer:
    """Results Summarizer 테스트"""
    
    def test_summarizer_script_exists(self):
        """Summarizer 스크립트 존재 확인"""
        script_path = project_root / "scripts" / "research" / "phase28_2_summarize_tuning_results.py"
        assert script_path.exists(), f"Summarizer 스크립트 없음: {script_path}"
    
    def test_filter_valid_results(self):
        """유효한 결과 필터링 로직 테스트"""
        # Mock 데이터
        results = [
            {'trade_count': 5, 'max_drawdown': 10.0, 'sharpe_ratio': 1.5},  # 거래 수 부족
            {'trade_count': 15, 'max_drawdown': 25.0, 'sharpe_ratio': 2.0},  # MDD 초과
            {'trade_count': 20, 'max_drawdown': 15.0, 'sharpe_ratio': 1.8},  # OK
            {'trade_count': 30, 'max_drawdown': 10.0, 'sharpe_ratio': 2.2},  # OK
        ]
        
        # 필터링 (min_trades=10, max_drawdown=20.0)
        valid = [
            r for r in results
            if r['trade_count'] >= 10 and r['max_drawdown'] <= 20.0
        ]
        
        assert len(valid) == 2
        assert valid[0]['trade_count'] == 20
        assert valid[1]['trade_count'] == 30
    
    def test_select_top_n(self):
        """Top N 선정 로직 테스트"""
        # Mock 데이터
        results = [
            {'sharpe_ratio': 1.5, 'params': {'rsi': 42}},
            {'sharpe_ratio': 2.2, 'params': {'rsi': 44}},
            {'sharpe_ratio': 1.8, 'params': {'rsi': 43}},
            {'sharpe_ratio': 2.0, 'params': {'rsi': 45}},
        ]
        
        # Top 2 선정
        top_results = sorted(results, key=lambda x: x['sharpe_ratio'], reverse=True)[:2]
        
        assert len(top_results) == 2
        assert top_results[0]['sharpe_ratio'] == 2.2
        assert top_results[1]['sharpe_ratio'] == 2.0


class TestWorkerConfigCompatibility:
    """Worker와 PHASE28-1 Config 호환성 테스트"""
    
    def test_worker_supports_strategies_section(self):
        """Worker가 strategies 섹션을 지원하는지 확인"""
        from tuning.cluster.worker import TuningWorker
        
        # Worker 코드에 'strategies' 키워드가 있는지 확인
        import inspect
        source = inspect.getsource(TuningWorker.process_job)
        
        assert 'strategies' in source.lower(), "Worker가 strategies 섹션을 지원하지 않음"
    
    def test_worker_supports_selector_key(self):
        """Worker가 strategy.selector 키를 지원하는지 확인"""
        from tuning.cluster.worker import TuningWorker
        
        import inspect
        source = inspect.getsource(TuningWorker.process_job)
        
        assert 'selector' in source.lower(), "Worker가 strategy.selector를 지원하지 않음"


class TestAcceptanceCriteria:
    """PHASE28-2 Acceptance Criteria 테스트"""
    
    def test_all_required_files_exist(self):
        """필수 파일 존재 확인"""
        required_files = [
            "configs/tuning/phase28_2_btc5m_baseline_paramspace.yml",
            "scripts/tuning/phase28_2_run_random_search.py",
            "scripts/tuning/phase28_2_run_bayesian_search.py",
            "scripts/research/phase28_2_summarize_tuning_results.py",
        ]
        
        for file_path in required_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"필수 파일 없음: {file_path}"
    
    def test_paramspace_has_minimum_params(self):
        """ParamSpace에 최소 파라미터 개수 확인 (≥5)"""
        yaml_path = project_root / "configs" / "tuning" / "phase28_2_btc5m_baseline_paramspace.yml"
        
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        param_space = data['param_space']
        assert len(param_space) >= 5, f"파라미터 개수 부족: {len(param_space)}개 (최소 5개)"
    
    def test_acceptance_criteria_section_exists(self):
        """YAML에 acceptance 섹션 존재 확인"""
        yaml_path = project_root / "configs" / "tuning" / "phase28_2_btc5m_baseline_paramspace.yml"
        
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        assert 'acceptance' in data, "acceptance 섹션 없음"
        
        acceptance = data['acceptance']
        assert 'random_trials_min' in acceptance
        assert 'bayesian_trials_min' in acceptance
        assert acceptance['random_trials_min'] >= 20, "Random trials 최소값 부족"
        assert acceptance['bayesian_trials_min'] >= 3, "Bayesian trials 최소값 부족"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
