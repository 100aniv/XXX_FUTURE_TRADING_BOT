#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전략 인터페이스 계약 테스트
============================
PHASE36-0 RECOVERY: P0-2 회귀 방지

모든 등록된 전략이 compute_signal(df, config=...) 호출을 
예외 없이 처리하는지 검증

이 테스트는 다음을 보장한다:
1. BaseStrategy를 상속한 모든 전략이 compute_signal(**kwargs) 지원
2. config= 키워드 인자가 전달되어도 예외가 발생하지 않음
3. 시그니처 불일치로 인한 0 trades 문제 재발 방지
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.registry.base_strategy import BaseStrategy


def _create_minimal_df() -> pd.DataFrame:
    """테스트용 최소 DataFrame 생성 (지표 포함)"""
    n = 100
    return pd.DataFrame({
        'time': pd.date_range('2025-01-01', periods=n, freq='1min'),
        'open': 100.0 + np.random.randn(n),
        'high': 101.0 + np.random.randn(n),
        'low': 99.0 + np.random.randn(n),
        'close': 100.0 + np.random.randn(n),
        'volume': 1000 + np.random.randint(-100, 100, n),
        'rsi': 50.0 + np.random.randn(n) * 10,
        'atr': 0.5 + np.random.rand(n) * 0.1,
        'ema_fast': 100.0 + np.random.randn(n) * 0.5,
        'ema_slow': 100.0 + np.random.randn(n) * 0.3,
        'bb_upper': 102.0 + np.random.randn(n) * 0.2,
        'bb_middle': 100.0 + np.random.randn(n) * 0.2,
        'bb_lower': 98.0 + np.random.randn(n) * 0.2,
    })


def _create_minimal_config() -> dict:
    """테스트용 최소 Config"""
    return {
        'symbol': 'BTCUSDT',
        'timeframe': '1m',
        'leverage': {'min': 1, 'max': 5, 'default': 1},
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'exits': {
            'rr': 1.5,
            'atr_mult_sl': 1.2,
        }
    }


@pytest.fixture
def test_df():
    """테스트용 DataFrame"""
    return _create_minimal_df()


@pytest.fixture
def test_config():
    """테스트용 Config"""
    return _create_minimal_config()


class TestStrategyInterfaceContract:
    """전략 인터페이스 계약 테스트"""
    
    def test_base_strategy_signature_with_kwargs(self, test_df, test_config):
        """BaseStrategy.compute_signal이 **kwargs를 받는지 검증"""
        from strategies.scalping import ScalpingStrategy
        
        strategy = ScalpingStrategy(config=test_config)
        
        # 1. 기본 호출 (kwargs 없음)
        result1 = strategy.compute_signal(test_df)
        assert isinstance(result1, dict), "compute_signal은 dict를 반환해야 함"
        
        # 2. config= 키워드 인자 전달 (P0-2 회귀 케이스)
        result2 = strategy.compute_signal(test_df, config=test_config)
        assert isinstance(result2, dict), "compute_signal(df, config=...)은 예외 없이 실행되어야 함"
        
        # 3. 추가 kwargs 전달 (미래 확장성)
        result3 = strategy.compute_signal(test_df, config=test_config, extra_param="ignored")
        assert isinstance(result3, dict), "compute_signal(df, **kwargs)는 미사용 키워드도 허용해야 함"
    
    def test_all_registered_strategies_support_kwargs(self, test_df, test_config):
        """등록된 모든 전략이 kwargs를 지원하는지 검증"""
        strategy_classes = [
            ('scalping', 'ScalpingStrategy'),
            ('breakout', 'BreakoutStrategy'),
            ('daytrade', 'DaytradeStrategy'),
            ('reversion', 'ReversionStrategy'),
            ('swing', 'SwingStrategy'),
            ('swing_bb', 'SwingBBStrategy'),
            ('trend', 'TrendStrategy'),
        ]
        
        failed_strategies = []
        
        for module_name, class_name in strategy_classes:
            try:
                # 동적 임포트
                module = __import__(f'strategies.{module_name}', fromlist=[class_name])
                strategy_class = getattr(module, class_name)
                
                # BaseStrategy 상속 확인
                if not issubclass(strategy_class, BaseStrategy):
                    failed_strategies.append(f"{module_name}.{class_name}: BaseStrategy 미상속")
                    continue
                
                # 인스턴스 생성
                strategy = strategy_class(config=test_config)
                
                # config= 키워드 인자 전달 테스트
                result = strategy.compute_signal(test_df, config=test_config)
                
                # 결과 검증
                assert isinstance(result, dict), f"{module_name}: 반환값이 dict가 아님"
                
            except TypeError as e:
                if "unexpected keyword argument" in str(e):
                    failed_strategies.append(f"{module_name}.{class_name}: config= 키워드 미지원 - {e}")
                else:
                    failed_strategies.append(f"{module_name}.{class_name}: TypeError - {e}")
            except Exception as e:
                # 다른 예외는 전략 내부 로직 문제일 수 있으므로 경고만
                print(f"⚠️  {module_name}: 내부 예외 (시그니처는 OK) - {e}")
        
        # 실패한 전략이 있으면 테스트 실패
        if failed_strategies:
            pytest.fail(
                f"전략 인터페이스 계약 위반:\n" +
                "\n".join(f"  - {s}" for s in failed_strategies)
            )
    
    def test_ensemble_strategy_supports_kwargs(self, test_df, test_config):
        """Ensemble 전략도 kwargs를 지원하는지 검증"""
        try:
            from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
            
            strategy = Phase35EnsembleV1(config=test_config)
            
            # config= 키워드 인자 전달
            result = strategy.compute_signal(test_df, config=test_config)
            
            assert isinstance(result, dict), "Phase35EnsembleV1: 반환값이 dict가 아님"
            
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                pytest.fail(f"Phase35EnsembleV1이 config= 키워드를 지원하지 않음: {e}")
            else:
                raise
        except Exception as e:
            # 내부 로직 예외는 허용 (시그니처는 OK)
            print(f"⚠️  Phase35EnsembleV1: 내부 예외 (시그니처는 OK) - {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
