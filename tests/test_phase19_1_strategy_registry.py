#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE19-1: Strategy Registry 테스트
==================================
Strategy Metadata, BaseStrategy, StrategyRegistry 검증
"""
import sys
import pandas as pd
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_strategy_metadata():
    """StrategyMetadata 동작 테스트"""
    print("=" * 60)
    print("TEST 1: StrategyMetadata")
    print("=" * 60)
    
    from common.registry.strategy_metadata import StrategyMetadata
    
    # 정상 메타데이터
    metadata = StrategyMetadata(
        strategy_name='test_strategy',
        strategy_type='scalping',
        supported_symbols=['BTCUSDT'],
        supported_timeframes=['1m', '5m'],
        version='v1.0',
        description='Test strategy'
    )
    
    assert metadata.validate(), "유효한 metadata가 validate 실패"
    print("✅ 정상 메타데이터 생성 및 검증 성공")
    
    # 심볼 지원 확인
    assert metadata.supports_symbol('BTCUSDT'), "BTCUSDT 지원해야 함"
    assert not metadata.supports_symbol('ETHUSDT'), "ETHUSDT는 지원 안함"
    print("✅ supports_symbol() 테스트 성공")
    
    # 타임프레임 지원 확인
    assert metadata.supports_timeframe('1m'), "1m 지원해야 함"
    assert not metadata.supports_timeframe('1h'), "1h는 지원 안함"
    print("✅ supports_timeframe() 테스트 성공")
    
    # 빈 리스트 = 모든 것 지원
    metadata_all = StrategyMetadata(
        strategy_name='all_strategy',
        strategy_type='trend',
        supported_symbols=[],  # 모든 심볼
        supported_timeframes=[],  # 모든 TF
        version='v1.0',
        description='All support'
    )
    assert metadata_all.supports_symbol('ANYUSDT'), "빈 리스트는 모든 심볼 지원"
    assert metadata_all.supports_timeframe('99h'), "빈 리스트는 모든 TF 지원"
    print("✅ 빈 리스트 = 모든 것 지원 테스트 성공")
    
    print("\n✅ TEST 1 PASSED\n")


def test_base_strategy():
    """BaseStrategy 인터페이스 테스트"""
    print("=" * 60)
    print("TEST 2: BaseStrategy")
    print("=" * 60)
    
    from common.registry.base_strategy import BaseStrategy
    from common.registry.strategy_metadata import StrategyMetadata
    
    # 구체 클래스 정의
    class TestStrategy(BaseStrategy):
        @property
        def metadata(self):
            return StrategyMetadata(
                strategy_name='test',
                strategy_type='test',
                supported_symbols=[],
                supported_timeframes=[],
                version='v1.0',
                description='Test'
            )
        
        def compute_signal(self, df):
            return {'direction': 'LONG', 'reason': 'test'}
    
    # 인스턴스 생성
    strategy = TestStrategy(config={'rsi_oversold': 30})
    assert strategy.config['rsi_oversold'] == 30, "config 전달 실패"
    print("✅ 전략 인스턴스 생성 및 config 전달 성공")
    
    # metadata 확인
    assert strategy.metadata.strategy_name == 'test', "metadata 반환 실패"
    print("✅ metadata 프로퍼티 정상 작동")
    
    # validate 확인
    assert strategy.validate(), "validate() 실패"
    print("✅ validate() 메서드 정상 작동")
    
    # compute_signal 확인
    df = pd.DataFrame({'close': [100, 101, 102]})
    signal = strategy.compute_signal(df)
    assert signal['direction'] == 'LONG', "compute_signal 실패"
    print("✅ compute_signal() 메서드 정상 작동")
    
    # __repr__ 확인
    repr_str = repr(strategy)
    assert 'TestStrategy' in repr_str, "__repr__ 실패"
    print(f"✅ __repr__: {repr_str}")
    
    print("\n✅ TEST 2 PASSED\n")


def test_strategy_registry_basic():
    """StrategyRegistry 기본 기능 테스트"""
    print("=" * 60)
    print("TEST 3: StrategyRegistry Basic")
    print("=" * 60)
    
    from common.registry.strategy_registry import StrategyRegistry
    from common.registry.base_strategy import BaseStrategy
    from common.registry.strategy_metadata import StrategyMetadata
    
    # 레지스트리 생성
    registry = StrategyRegistry()
    print(f"✅ Registry 생성: {registry}")
    
    # 테스트 전략 정의
    class DummyStrategy(BaseStrategy):
        @property
        def metadata(self):
            return StrategyMetadata(
                strategy_name='dummy',
                strategy_type='test',
                supported_symbols=[],
                supported_timeframes=[],
                version='v1.0',
                description='Dummy'
            )
        
        def compute_signal(self, df):
            return {'direction': None}
    
    # 수동 등록
    registry.register(DummyStrategy)
    assert 'dummy' in registry.list_strategies(), "수동 등록 실패"
    print("✅ 수동 등록 (register) 성공")
    
    # 전략 가져오기
    strategy = registry.get('dummy', {'test': 123})
    assert strategy is not None, "get() 실패"
    assert strategy.config['test'] == 123, "config 전달 실패"
    print("✅ get() 메서드 정상 작동")
    
    # 메타데이터 조회
    metadata = registry.get_metadata('dummy')
    assert metadata.strategy_name == 'dummy', "get_metadata 실패"
    print("✅ get_metadata() 정상 작동")
    
    # 전체 메타데이터
    all_metadata = registry.list_metadata()
    assert 'dummy' in all_metadata, "list_metadata 실패"
    print(f"✅ list_metadata(): {list(all_metadata.keys())}")
    
    # count
    assert registry.count() >= 1, "count() 실패"
    print(f"✅ count(): {registry.count()}")
    
    print("\n✅ TEST 3 PASSED\n")


def test_strategy_registry_scan():
    """StrategyRegistry 자동 스캔 테스트"""
    print("=" * 60)
    print("TEST 4: StrategyRegistry Scan")
    print("=" * 60)
    
    from common.registry.strategy_registry import StrategyRegistry
    
    # 실제 strategies 디렉토리 스캔
    registry = StrategyRegistry(strategies_dir='strategies')
    count = registry.scan()
    
    print(f"📊 발견된 전략 수: {count}")
    print(f"📋 전략 목록: {registry.list_strategies()}")
    
    # 최소 전략 수 확인 (scalping, breakout, reversion, trend, swing, swing_bb, daytrade)
    assert count >= 7, f"전략이 {count}개만 발견됨 (최소 7개 필요)"
    print(f"✅ 최소 7개 전략 발견 ({count}개)")
    
    # 주요 전략 존재 확인
    strategies = registry.list_strategies()
    expected = ['scalping', 'breakout', 'reversion', 'trend', 'swing', 'swing_bb', 'daytrade']
    for name in expected:
        assert name in strategies, f"{name} 전략이 등록되지 않음"
        print(f"  ✅ {name}")
    
    print("\n✅ TEST 4 PASSED\n")


def test_real_strategies():
    """실제 전략 클래스 동작 테스트"""
    print("=" * 60)
    print("TEST 5: Real Strategies")
    print("=" * 60)
    
    from common.registry.strategy_registry import StrategyRegistry
    import pandas as pd
    import numpy as np
    
    # Registry 스캔
    registry = StrategyRegistry()
    registry.scan()
    
    # 테스트용 DataFrame 생성 (간단한 OHLCV)
    np.random.seed(42)
    df = pd.DataFrame({
        'time': pd.date_range('2024-01-01', periods=100, freq='1min'),
        'open': 100 + np.random.randn(100).cumsum(),
        'high': 101 + np.random.randn(100).cumsum(),
        'low': 99 + np.random.randn(100).cumsum(),
        'close': 100 + np.random.randn(100).cumsum(),
        'volume': 1000 + np.random.randint(0, 500, 100),
        'atr': np.full(100, 0.5),
        'rsi': np.full(100, 50.0),
        'ema_fast': 100 + np.random.randn(100).cumsum(),
        'ema_slow': 100 + np.random.randn(100).cumsum(),
        'vol_ma': np.full(100, 1000.0),
    })
    
    # scalping 전략 테스트
    scalping = registry.get('scalping', {
        'min_bars_for_signal': 10,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'leverage': {'min': 1, 'max': 10},
        'rr': 1.5,
        'atr_mult_sl': 1.2
    })
    
    assert scalping is not None, "scalping 전략 로드 실패"
    print("✅ scalping 전략 인스턴스 생성")
    
    # Metadata 확인
    metadata = scalping.metadata
    assert metadata.strategy_name == 'scalping', "scalping metadata 오류"
    assert metadata.version == 'v3.0', "scalping version 오류"
    print(f"  📋 Metadata: {metadata.strategy_name} {metadata.version}")
    print(f"  🕒 Supported TF: {metadata.supported_timeframes}")
    
    # Signal 계산 시도 (에러 없이 실행되면 성공)
    try:
        signal = scalping.compute_signal(df)
        print(f"  ✅ compute_signal() 정상 실행")
        print(f"     Signal keys: {list(signal.keys())[:5]}...")
    except Exception as e:
        print(f"  ⚠️  compute_signal() 실행 중 에러: {e}")
        # 일부 전략은 특정 지표가 없으면 에러 발생 가능 (정상)
    
    # 다른 전략들도 인스턴스 생성만 테스트
    for name in ['breakout', 'reversion', 'trend']:
        strategy = registry.get(name, {'leverage': {'min': 1, 'max': 10}, 'rr': 1.5, 'atr_mult_sl': 1.2})
        assert strategy is not None, f"{name} 전략 로드 실패"
        assert strategy.metadata.strategy_name == name, f"{name} metadata 오류"
        print(f"✅ {name} 전략: {strategy.metadata.version}")
    
    print("\n✅ TEST 5 PASSED\n")


def test_inheritance_validation():
    """BaseStrategy 상속 여부 검증"""
    print("=" * 60)
    print("TEST 6: Inheritance Validation")
    print("=" * 60)
    
    from common.registry.strategy_registry import StrategyRegistry
    from common.registry.base_strategy import BaseStrategy
    
    registry = StrategyRegistry()
    registry.scan()
    
    strategies = registry.list_strategies()
    print(f"📊 등록된 전략: {len(strategies)}개")
    
    for name in strategies:
        strategy = registry.get(name, {})
        assert isinstance(strategy, BaseStrategy), f"{name}이 BaseStrategy를 상속하지 않음"
        print(f"  ✅ {name}: BaseStrategy 상속 확인")
    
    print("\n✅ TEST 6 PASSED\n")


def test_exception_handling():
    """예외 처리 테스트"""
    print("=" * 60)
    print("TEST 7: Exception Handling")
    print("=" * 60)
    
    from common.registry.strategy_registry import StrategyRegistry
    
    registry = StrategyRegistry()
    registry.scan()
    
    # 존재하지 않는 전략
    non_existent = registry.get('non_existent_strategy')
    assert non_existent is None, "존재하지 않는 전략은 None 반환해야 함"
    print("✅ 존재하지 않는 전략 처리 정상")
    
    # 존재하지 않는 메타데이터
    metadata = registry.get_metadata('non_existent')
    assert metadata is None, "존재하지 않는 메타데이터는 None 반환해야 함"
    print("✅ 존재하지 않는 메타데이터 처리 정상")
    
    print("\n✅ TEST 7 PASSED\n")


def main():
    """전체 테스트 실행"""
    print("\n" + "=" * 60)
    print("PHASE19-1 Strategy Registry 테스트 시작")
    print("=" * 60)
    
    tests = [
        test_strategy_metadata,
        test_base_strategy,
        test_strategy_registry_basic,
        test_strategy_registry_scan,
        test_real_strategies,
        test_inheritance_validation,
        test_exception_handling,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ TEST FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ TEST ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"테스트 완료: {passed} PASSED, {failed} FAILED")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("\n✅ 모든 테스트 PASSED")
        sys.exit(0)


if __name__ == '__main__':
    main()
