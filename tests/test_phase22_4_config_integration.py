"""
PHASE22-4/23-1: Strategy Config Integration Tests
전략별 config params가 제대로 로드되고 전달되는지 검증

PHASE23-1 추가: run_v2() 경로 검증
"""
import pytest
from strategies import load_strategies


def test_load_strategies_returns_dict_with_params():
    """load_strategies가 params를 포함한 dict를 반환하는지 테스트"""
    config = {
        "strategies": {
            "scalping": {
                "enabled": True,
                "params": {
                    "rsi_oversold": 40,
                    "rsi_overbought": 60,
                    "momentum_enabled": False,
                },
            },
            "trend": {
                "enabled": False,
                "params": {
                    "sma_fast": 50,
                    "sma_slow": 200,
                },
            },
        },
    }
    
    strategies = load_strategies(config)
    
    # scalping은 enabled=True이므로 로드되어야 함
    assert "scalping" in strategies
    assert isinstance(strategies["scalping"], dict)
    assert "module" in strategies["scalping"]
    assert "params" in strategies["scalping"]
    assert "enabled" in strategies["scalping"]
    
    # params 검증
    scalping_params = strategies["scalping"]["params"]
    assert scalping_params["rsi_oversold"] == 40
    assert scalping_params["rsi_overbought"] == 60
    assert scalping_params["momentum_enabled"] is False
    
    # trend는 enabled=False이므로 로드되지 않아야 함
    assert "trend" not in strategies


def test_load_strategies_with_empty_params():
    """params가 비어있어도 정상 작동하는지 테스트"""
    config = {
        "strategies": {
            "scalping": {
                "enabled": True,
                "params": {},
            },
        },
    }
    
    strategies = load_strategies(config)
    
    assert "scalping" in strategies
    assert strategies["scalping"]["params"] == {}


def test_load_strategies_without_params_key():
    """params 키가 없어도 정상 작동하는지 테스트 (기본값 {})"""
    config = {
        "strategies": {
            "scalping": {
                "enabled": True,
            },
        },
    }
    
    strategies = load_strategies(config)
    
    assert "scalping" in strategies
    assert "params" in strategies["scalping"]
    assert strategies["scalping"]["params"] == {}


def test_load_strategies_single_strategy_mode():
    """단일 전략 모드에서도 params가 전달되는지 테스트"""
    config = {
        "strategy": {
            "use_ensemble": False,
            "selector": "scalping",
        },
        "strategies": {
            "scalping": {
                "enabled": True,
                "params": {
                    "rsi_oversold": 45,
                    "rsi_overbought": 55,
                },
            },
        },
    }
    
    strategies = load_strategies(config)
    
    # 단일 전략 모드에서는 selector만 로드
    assert "scalping" in strategies
    assert len(strategies) == 1
    
    # params 검증
    scalping_params = strategies["scalping"]["params"]
    assert scalping_params["rsi_oversold"] == 45
    assert scalping_params["rsi_overbought"] == 55


def test_load_strategies_multiple_enabled():
    """여러 전략이 enabled=True일 때 모두 로드되는지 테스트"""
    config = {
        "strategies": {
            "scalping": {
                "enabled": True,
                "params": {"rsi_oversold": 40},
            },
            "trend": {
                "enabled": True,
                "params": {"sma_fast": 50},
            },
            "breakout": {
                "enabled": False,
                "params": {"lookback_period": 20},
            },
        },
    }
    
    strategies = load_strategies(config)
    
    # scalping과 trend는 로드, breakout은 로드 안 됨
    assert "scalping" in strategies
    assert "trend" in strategies
    assert "breakout" not in strategies
    
    # 각 전략의 params 검증
    assert strategies["scalping"]["params"]["rsi_oversold"] == 40
    assert strategies["trend"]["params"]["sma_fast"] == 50


def test_load_strategies_fallback_to_daytrade():
    """모든 전략이 disabled일 때 daytrade로 fallback하는지 테스트"""
    config = {
        "strategies": {
            "scalping": {"enabled": False},
            "swing_bb": {"enabled": False},
            "daytrade": {"enabled": False},
            "swing": {"enabled": False},
            "trend": {"enabled": False},
            "reversion": {"enabled": False},
            "breakout": {"enabled": False},
        },
    }
    
    strategies = load_strategies(config)
    
    # daytrade가 fallback으로 로드되어야 함
    assert "daytrade" in strategies
    assert len(strategies) == 1
    assert strategies["daytrade"]["enabled"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
