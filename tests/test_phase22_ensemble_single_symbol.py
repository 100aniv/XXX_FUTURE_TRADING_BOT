#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE22-1: Single-Symbol Ensemble v1 Integration - Unit Tests
=============================================================
목표: Config, 전략 로딩, Ensemble 구조 검증

Test Cases:
1. Config 파싱 가능
2. 4개 전략 정의 확인
3. Ensemble 설정 유효성
4. 개별 전략 모듈 import 가능
"""
import pytest
import yaml
from pathlib import Path
import sys

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestPHASE22_1_Config:
    """Config 파일 검증"""
    
    @pytest.fixture
    def config_path(self):
        return project_root / "configs/paper/phase22_ensemble_single_symbol.yml"
    
    @pytest.fixture
    def config(self, config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def test_config_file_exists(self, config_path):
        """Config 파일 존재 확인"""
        assert config_path.exists(), f"Config 파일이 없습니다: {config_path}"
    
    def test_config_parse(self, config):
        """Config 파싱 가능"""
        assert config is not None
        assert isinstance(config, dict)
    
    def test_mode_is_paper(self, config):
        """모드가 paper인지 확인"""
        assert config.get('mode') == 'paper'
    
    def test_symbol_is_btcusdt(self, config):
        """심볼이 BTCUSDT인지 확인"""
        assert config.get('symbol') == 'BTCUSDT'
    
    def test_ensemble_enabled(self, config):
        """Ensemble 모드 활성화 확인"""
        ensemble = config.get('ensemble', {})
        assert ensemble.get('enabled') is True, "Ensemble 모드가 비활성화되어 있습니다"
    
    def test_ensemble_strategies_count(self, config):
        """Ensemble 전략 수 확인 (4개)"""
        ensemble = config.get('ensemble', {})
        strategies = ensemble.get('strategies', [])
        assert len(strategies) == 4, f"전략 수가 4개가 아닙니다: {len(strategies)}"
    
    def test_ensemble_strategies_list(self, config):
        """Ensemble 전략 목록 확인"""
        ensemble = config.get('ensemble', {})
        strategies = ensemble.get('strategies', [])
        expected = ['scalping', 'breakout', 'reversion', 'trend']
        
        assert set(strategies) == set(expected), f"전략 목록 불일치: {strategies} != {expected}"
    
    def test_duration_is_30min(self, config):
        """실행 시간이 30분(0.5h)인지 확인"""
        paper = config.get('paper', {})
        duration_hours = paper.get('duration_hours')
        assert duration_hours == 0.5, f"실행 시간이 0.5h가 아닙니다: {duration_hours}"
    
    def test_duration_mode_is_wall_clock(self, config):
        """Duration 모드가 wall_clock인지 확인"""
        paper = config.get('paper', {})
        duration_mode = paper.get('duration_mode')
        assert duration_mode == 'wall_clock', f"Duration 모드가 wall_clock이 아닙니다: {duration_mode}"
    
    def test_feed_timeframes(self, config):
        """Feed timeframes 확인 (3m, 5m, 15m, 1h)"""
        feed = config.get('feed', {})
        timeframes = feed.get('timeframes', [])
        expected = ['3m', '5m', '15m', '1h']
        
        assert set(timeframes) == set(expected), f"Timeframes 불일치: {timeframes} != {expected}"


class TestPHASE22_1_StrategyLoading:
    """전략 모듈 로딩 검증"""
    
    def test_import_scalping(self):
        """Scalping 전략 import 가능"""
        try:
            from strategies import scalping
            assert scalping is not None
        except ImportError as e:
            pytest.fail(f"Scalping 전략 import 실패: {e}")
    
    def test_import_reversion(self):
        """Reversion 전략 import 가능"""
        try:
            from strategies import reversion
            assert reversion is not None
        except ImportError as e:
            pytest.fail(f"Reversion 전략 import 실패: {e}")
    
    def test_import_breakout(self):
        """Breakout 전략 import 가능"""
        try:
            from strategies import breakout
            assert breakout is not None
        except ImportError as e:
            pytest.fail(f"Breakout 전략 import 실패: {e}")
    
    def test_import_trend(self):
        """Trend 전략 import 가능"""
        try:
            from strategies import trend
            assert trend is not None
        except ImportError as e:
            pytest.fail(f"Trend 전략 import 실패: {e}")
    
    def test_all_strategies_have_class(self):
        """모든 전략이 Strategy 클래스를 가지고 있는지 확인"""
        from strategies import scalping, reversion, breakout, trend
        
        strategies = [
            ('scalping', scalping),
            ('reversion', reversion),
            ('breakout', breakout),
            ('trend', trend)
        ]
        
        for name, module in strategies:
            # 전략 클래스 이름은 대문자로 시작 (예: ScalpingStrategy)
            class_name = name.capitalize() + 'Strategy'
            assert hasattr(module, class_name) or hasattr(module, name.capitalize()), \
                f"{name} 전략에 {class_name} 클래스가 없습니다"


class TestPHASE22_1_EnsembleStructure:
    """Ensemble 구조 검증"""
    
    def test_ensemble_module_exists(self):
        """Ensemble 모듈 존재 확인"""
        ensemble_path = project_root / "common/ensemble"
        assert ensemble_path.exists(), f"Ensemble 모듈 디렉토리가 없습니다: {ensemble_path}"
    
    @pytest.mark.skip(reason="StrategyRegistry는 현재 구조에 없음 (aggregator 사용)")
    def test_ensemble_strategy_registry(self):
        """StrategyRegistry import 가능"""
        try:
            from common.ensemble.registry import StrategyRegistry
            assert StrategyRegistry is not None
        except ImportError as e:
            pytest.fail(f"StrategyRegistry import 실패: {e}")
    
    def test_ensemble_aggregator(self):
        """EnsembleAggregator import 가능"""
        try:
            from common.ensemble.aggregator import EnsembleAggregator
            assert EnsembleAggregator is not None
        except ImportError as e:
            pytest.fail(f"EnsembleAggregator import 실패: {e}")


class TestPHASE22_1_RunScript:
    """실행 스크립트 검증"""
    
    def test_run_script_exists(self):
        """실행 스크립트 파일 존재 확인"""
        script_path = project_root / "scripts/run_phase22_ensemble_single_symbol.py"
        assert script_path.exists(), f"실행 스크립트가 없습니다: {script_path}"
    
    def test_run_script_executable(self):
        """실행 스크립트 실행 가능 (문법 오류 없음)"""
        script_path = project_root / "scripts/run_phase22_ensemble_single_symbol.py"
        
        # 문법 체크
        import py_compile
        try:
            py_compile.compile(str(script_path), doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"실행 스크립트 문법 오류: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
