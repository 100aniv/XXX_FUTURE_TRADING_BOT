#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE27-5A: Strategy Loading Tests
===================================
전략 로딩 로직 버그 수정 검증

목적:
- btc5m_baseline_v1이 정상적으로 로드되는지 검증
- base.yml essential_strategies와 custom config의 우선순위 검증
- daytrade fallback이 발생하지 않는지 검증
"""
import pytest
import yaml
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture
def base_config():
    """base.yml 로드"""
    base_path = PROJECT_ROOT / "configs" / "base.yml"
    with open(base_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture
def phase27_5_config():
    """phase27_5 config 로드"""
    config_path = PROJECT_ROOT / "configs" / "backtest" / "phase27_5_baseline_replay_30d.yml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def test_btc5m_baseline_v1_in_registry():
    """btc5m_baseline_v1이 전략 레지스트리에 등록되어 있는지 확인"""
    from strategies import get_all_strategies
    
    all_strategies = get_all_strategies()
    
    assert 'btc5m_baseline_v1' in all_strategies, \
        "btc5m_baseline_v1이 get_all_strategies()에 등록되어 있지 않음"


def test_btc5m_baseline_v1_module_import():
    """btc5m_baseline_v1 모듈을 import할 수 있는지 확인"""
    try:
        from strategies import btc5m_baseline_v1
        assert hasattr(btc5m_baseline_v1, 'BTC5mBaselineV1'), \
            "btc5m_baseline_v1 모듈에 BTC5mBaselineV1 클래스가 없음"
        assert hasattr(btc5m_baseline_v1, 'signal_logic'), \
            "btc5m_baseline_v1 모듈에 signal_logic 함수가 없음"
    except ImportError as e:
        pytest.fail(f"btc5m_baseline_v1 모듈을 import할 수 없음: {e}")


def test_load_strategies_single_mode_baseline(phase27_5_config):
    """단일 전략 모드에서 btc5m_baseline_v1이 로드되는지 검증"""
    from strategies import load_strategies
    
    # phase27_5 config 구조 확인
    assert 'strategy' in phase27_5_config, "phase27_5 config에 strategy 섹션이 없음"
    assert phase27_5_config['strategy']['selector'] == 'btc5m_baseline_v1', \
        "phase27_5 config의 selector가 btc5m_baseline_v1이 아님"
    assert phase27_5_config['strategy']['use_ensemble'] is False, \
        "phase27_5 config의 use_ensemble이 False가 아님"
    
    # load_strategies 호출
    strategies = load_strategies(config=phase27_5_config)
    
    # 검증
    assert len(strategies) == 1, \
        f"단일 전략 모드인데 {len(strategies)}개 전략이 로드됨"
    assert 'btc5m_baseline_v1' in strategies, \
        f"btc5m_baseline_v1이 로드되지 않음. 로드된 전략: {list(strategies.keys())}"
    assert 'daytrade' not in strategies, \
        "daytrade fallback이 발생함 (btc5m_baseline_v1이 로드되어야 함)"
    
    # 전략 인스턴스 확인
    strategy_info = strategies['btc5m_baseline_v1']
    assert 'instance' in strategy_info, "전략 인스턴스가 없음"
    assert 'params' in strategy_info, "전략 파라미터가 없음"
    assert 'enabled' in strategy_info, "전략 enabled 플래그가 없음"
    assert strategy_info['enabled'] is True, "전략이 비활성화되어 있음"


def test_load_strategies_baseline_params(phase27_5_config):
    """btc5m_baseline_v1의 파라미터가 제대로 전달되는지 검증"""
    from strategies import load_strategies
    
    strategies = load_strategies(config=phase27_5_config)
    
    # 전략 파라미터 확인
    strategy_info = strategies['btc5m_baseline_v1']
    params = strategy_info['params']
    
    # Config에서 정의한 파라미터 확인
    assert 'rsi_long_threshold' in params or 'rsi_long_threshold' in phase27_5_config.get('strategies', {}).get('btc5m_baseline_v1', {}), \
        "rsi_long_threshold 파라미터가 없음"
    assert 'use_adx' in params or 'use_adx' in phase27_5_config.get('strategies', {}).get('btc5m_baseline_v1', {}), \
        "use_adx 파라미터가 없음"


def test_load_strategies_base_essential_not_override():
    """base.yml의 essential_strategies가 custom config를 덮어쓰지 않는지 검증"""
    from strategies import load_strategies
    
    # Custom config: btc5m_baseline_v1만 사용
    custom_config = {
        'strategy': {
            'selector': 'btc5m_baseline_v1',
            'use_ensemble': False
        },
        'strategies': {
            'btc5m_baseline_v1': {
                'enabled': True,
                'params': {}
            }
        },
        'timeframe': '5m',
        'lookback': 1000,
        'equity': 50000,
        'risk': {'max_risk_per_trade': 0.03}
    }
    
    strategies = load_strategies(config=custom_config)
    
    # 검증: daytrade가 로드되면 안 됨
    assert 'daytrade' not in strategies, \
        f"base.yml의 essential_strategies가 custom config를 덮어씀. 로드된 전략: {list(strategies.keys())}"
    assert 'btc5m_baseline_v1' in strategies, \
        f"btc5m_baseline_v1이 로드되지 않음. 로드된 전략: {list(strategies.keys())}"


def test_load_strategies_with_ensemble_disabled():
    """Ensemble 비활성화 시 단일 전략만 로드되는지 검증"""
    from strategies import load_strategies
    
    config = {
        'strategy': {
            'selector': 'btc5m_baseline_v1',
            'use_ensemble': False  # 명시적 비활성화
        },
        'strategies': {
            'btc5m_baseline_v1': {
                'enabled': True,
                'params': {}
            },
            'daytrade': {  # 다른 전략도 있지만
                'enabled': True,
                'params': {}
            }
        },
        'timeframe': '5m',
        'lookback': 1000,
        'equity': 50000,
        'risk': {'max_risk_per_trade': 0.03}
    }
    
    strategies = load_strategies(config=config)
    
    # Ensemble 비활성화 + selector 있으면 selector만 로드
    assert len(strategies) == 1, \
        f"단일 전략 모드인데 {len(strategies)}개 전략이 로드됨"
    assert 'btc5m_baseline_v1' in strategies, \
        "btc5m_baseline_v1이 로드되지 않음"


def test_baseline_strategy_class_instance():
    """btc5m_baseline_v1이 BaseStrategy 인스턴스를 생성하는지 확인"""
    from strategies import load_strategies
    from common.registry.base_strategy import BaseStrategy
    
    config = {
        'strategy': {
            'selector': 'btc5m_baseline_v1',
            'use_ensemble': False
        },
        'strategies': {
            'btc5m_baseline_v1': {
                'enabled': True,
                'params': {
                    'rsi_long_threshold': 42,
                    'rsi_short_threshold': 58
                }
            }
        },
        'timeframe': '5m',
        'lookback': 1000,
        'equity': 50000,
        'risk': {'max_risk_per_trade': 0.03}
    }
    
    strategies = load_strategies(config=config)
    strategy_instance = strategies['btc5m_baseline_v1']['instance']
    
    # BaseStrategy 인스턴스인지 확인
    assert isinstance(strategy_instance, BaseStrategy), \
        f"전략 인스턴스가 BaseStrategy가 아님: {type(strategy_instance)}"
    
    # compute_signal 메서드가 있는지 확인
    assert hasattr(strategy_instance, 'compute_signal'), \
        "전략 인스턴스에 compute_signal 메서드가 없음"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
