#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE29-2C-R: Config 파라미터 전달 검증 테스트
================================================
btc5m_baseline_v3 전략의 Config → 파라미터 전달이 정상 작동하는지 검증

목적:
- YAML Config의 strategies.btc5m_baseline_v3 섹션이
- load_strategies()를 통해 전략 인스턴스의 params로 정확히 전달되는지 확인
- Scenario A+ 핵심 파라미터 검증

테스트 항목:
1. load_strategies() 실행 시 btc5m_baseline_v3 params 추출
2. 핵심 파라미터 값 검증 (range_rsi_long_threshold, range_min_conditions 등)
3. params dict가 빈 딕셔너리가 아닌지 확인
"""
import pytest
import yaml
from pathlib import Path

# 프로젝트 루트 추가
import sys
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from strategies import load_strategies


def test_load_strategies_btc5m_baseline_v3_params_extraction():
    """
    PHASE29-2C-R: btc5m_baseline_v3 Config 파라미터 추출 검증
    
    검증:
    - Config의 strategies.btc5m_baseline_v3 섹션이 params로 추출됨
    - params가 빈 딕셔너리가 아님
    - 핵심 파라미터 포함 확인
    """
    # Scenario A+ Config 로드
    config_path = project_root / "configs/backtest/phase29_2c_btc5m_baseline_v3_month_scenario_a_plus.yml"
    
    if not config_path.exists():
        pytest.skip(f"Config 파일 없음: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Config 검증
    assert 'strategies' in config, "Config에 strategies 섹션 없음"
    assert 'btc5m_baseline_v3' in config['strategies'], "btc5m_baseline_v3 설정 없음"
    
    # load_strategies 실행
    config['strategy'] = {'selector': 'btc5m_baseline_v3', 'use_ensemble': False}
    strategies = load_strategies(config)
    
    # btc5m_baseline_v3 전략 로딩 확인
    assert 'btc5m_baseline_v3' in strategies, "btc5m_baseline_v3 전략 로드 실패"
    
    strategy_info = strategies['btc5m_baseline_v3']
    assert 'params' in strategy_info, "params 키 없음"
    
    params = strategy_info['params']
    
    # params가 빈 딕셔너리가 아닌지 확인 (PHASE29-2C 버그)
    assert params, "params가 빈 딕셔너리 (버그 재발)"
    assert len(params) > 0, "params에 아무 키도 없음"
    
    print(f"✅ params 추출 성공: {len(params)} 개 파라미터")


def test_btc5m_baseline_v3_scenario_a_plus_params_values():
    """
    PHASE29-2C-R: Scenario A+ 핵심 파라미터 값 검증
    
    검증:
    - range_rsi_long_threshold = 40
    - range_rsi_short_threshold = 60
    - range_min_conditions = 1
    - min_atr_pct = 0.0015
    - min_volume_ratio = 0.5
    - min_reward_risk_ratio = 1.5 (position_sizing 또는 전략 레벨)
    """
    config_path = project_root / "configs/backtest/phase29_2c_btc5m_baseline_v3_month_scenario_a_plus.yml"
    
    if not config_path.exists():
        pytest.skip(f"Config 파일 없음: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # load_strategies 실행
    config['strategy'] = {'selector': 'btc5m_baseline_v3', 'use_ensemble': False}
    strategies = load_strategies(config)
    
    params = strategies['btc5m_baseline_v3']['params']
    
    # Scenario A+ 핵심 파라미터 검증
    assert params.get('range_rsi_long_threshold') == 40, f"range_rsi_long_threshold: {params.get('range_rsi_long_threshold')} != 40"
    assert params.get('range_rsi_short_threshold') == 60, f"range_rsi_short_threshold: {params.get('range_rsi_short_threshold')} != 60"
    assert params.get('range_min_conditions') == 1, f"range_min_conditions: {params.get('range_min_conditions')} != 1"
    
    # V3 필터 파라미터 검증 (v3_filters 하위 또는 직접)
    v3_filters = params.get('v3_filters', {})
    
    # min_atr_pct는 v3_filters 또는 직접 파라미터
    min_atr_pct = v3_filters.get('min_atr_pct') or params.get('min_atr_pct')
    assert min_atr_pct == 0.0015, f"min_atr_pct: {min_atr_pct} != 0.0015"
    
    # min_volume_ratio는 v3_filters 또는 직접 파라미터
    min_volume_ratio = v3_filters.get('min_volume_ratio') or params.get('min_volume_ratio')
    assert min_volume_ratio == 0.5, f"min_volume_ratio: {min_volume_ratio} != 0.5"
    
    print(f"✅ Scenario A+ 핵심 파라미터 검증 완료")
    print(f"   - range_rsi_long_threshold: {params['range_rsi_long_threshold']}")
    print(f"   - range_rsi_short_threshold: {params['range_rsi_short_threshold']}")
    print(f"   - range_min_conditions: {params['range_min_conditions']}")
    print(f"   - min_atr_pct: {min_atr_pct}")
    print(f"   - min_volume_ratio: {min_volume_ratio}")


def test_btc5m_baseline_v3_instance_creation():
    """
    PHASE29-2C-R: btc5m_baseline_v3 인스턴스 생성 및 파라미터 병합 검증
    
    검증:
    - BaseStrategy 인스턴스가 정상 생성됨
    - 인스턴스의 config에 전략 파라미터가 병합되어 있음
    """
    config_path = project_root / "configs/backtest/phase29_2c_btc5m_baseline_v3_month_scenario_a_plus.yml"
    
    if not config_path.exists():
        pytest.skip(f"Config 파일 없음: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # load_strategies 실행
    config['strategy'] = {'selector': 'btc5m_baseline_v3', 'use_ensemble': False}
    strategies = load_strategies(config)
    
    instance = strategies['btc5m_baseline_v3']['instance']
    
    # 인스턴스 타입 검증
    assert instance is not None, "instance가 None"
    
    # BaseStrategy 인스턴스인지 확인
    from common.registry.base_strategy import BaseStrategy
    assert isinstance(instance, BaseStrategy), f"instance 타입: {type(instance)}, BaseStrategy 아님"
    
    # 인스턴스의 config에 파라미터가 병합되었는지 확인
    instance_config = instance.config
    
    assert instance_config.get('range_rsi_long_threshold') == 40, "인스턴스 config에 range_rsi_long_threshold 누락"
    assert instance_config.get('range_min_conditions') == 1, "인스턴스 config에 range_min_conditions 누락"
    
    print(f"✅ btc5m_baseline_v3 인스턴스 생성 및 파라미터 병합 검증 완료")
    print(f"   - 인스턴스 타입: {type(instance).__name__}")
    print(f"   - range_rsi_long_threshold in config: {instance_config.get('range_rsi_long_threshold')}")
    print(f"   - range_min_conditions in config: {instance_config.get('range_min_conditions')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
