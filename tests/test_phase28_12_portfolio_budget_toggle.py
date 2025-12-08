#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-12: Portfolio Manager 전략 예산 Guard 토글 기능 테스트
=============================================================
enable_strategy_budget_cap 플래그가 정상 작동하는지 검증
"""
import pytest
from execution.portfolio_manager import PortfolioManager


@pytest.fixture
def base_config():
    """기본 Config"""
    return {
        'capital': {'initial': 50000},
        'risk': {
            'max_positions': 5,
            'max_exposure_per_symbol': 0.5
        },
        'portfolio': {
            'max_total_exposure': 0.9,
            'max_strategy_positions': 3,
            'symbol_cooldown_seconds': 0,
            'use_dynamic_budget': False,
            'enable_strategy_budget_cap': True,  # 기본값
            'budget': {
                'strategy_allocation': {},
                'default_allocation': 0.2  # 20%
            }
        }
    }


def test_strategy_budget_enabled(base_config):
    """
    케이스 1: enable_strategy_budget_cap=True
    전략 예산 초과 시 can_open_position()이 False 리턴
    """
    pm = PortfolioManager(base_config, load_existing=False)
    
    # 검증: 플래그가 True로 설정되었는지
    assert pm.enable_strategy_budget_cap is True
    
    # 전략 예산: 50,000 * 20% = 10,000
    # 포지션 가치: 15,000 (예산 초과)
    allowed, reason = pm.can_open_position(
        symbol='BTCUSDT',
        strategy='test_strategy',
        position_value=15000,
        side='LONG'
    )
    
    assert allowed is False
    assert '전략 예산 초과' in reason


def test_strategy_budget_disabled(base_config):
    """
    케이스 2: enable_strategy_budget_cap=False
    전략 예산 초과 상황에서도 can_open_position()이 True 리턴 (예산 체크 스킵)
    """
    # 플래그를 False로 변경
    base_config['portfolio']['enable_strategy_budget_cap'] = False
    pm = PortfolioManager(base_config, load_existing=False)
    
    # 검증: 플래그가 False로 설정되었는지
    assert pm.enable_strategy_budget_cap is False
    
    # 전략 예산: 50,000 * 20% = 10,000
    # 포지션 가치: 15,000 (예산 초과하지만 Guard 비활성화)
    allowed, reason = pm.can_open_position(
        symbol='BTCUSDT',
        strategy='test_strategy',
        position_value=15000,
        side='LONG'
    )
    
    # 예산 Guard가 비활성화되어 다른 Guard들만 체크
    # (다른 Guard들이 PASS하면 allowed=True)
    assert allowed is True
    assert reason == "OK"


def test_strategy_budget_within_limit(base_config):
    """
    케이스 3: enable_strategy_budget_cap=True, 예산 내
    정상적으로 PASS
    """
    pm = PortfolioManager(base_config, load_existing=False)
    
    # 전략 예산: 50,000 * 20% = 10,000
    # 포지션 가치: 5,000 (예산 내)
    allowed, reason = pm.can_open_position(
        symbol='BTCUSDT',
        strategy='test_strategy',
        position_value=5000,
        side='LONG'
    )
    
    assert allowed is True
    assert reason == "OK"


def test_strategy_budget_boundary(base_config):
    """
    케이스 4: 예산 경계값 테스트
    포지션 1개 추가 후, 다시 시도하면 예산 초과로 차단되는지 확인
    """
    pm = PortfolioManager(base_config, load_existing=False)
    
    # 첫 번째 포지션: 6,000 (예산 10,000의 60%)
    allowed, reason = pm.can_open_position(
        symbol='BTCUSDT',
        strategy='test_strategy',
        position_value=6000,
        side='LONG'
    )
    assert allowed is True
    
    # 포지션 추가
    pm.add_position(
        symbol='BTCUSDT',
        strategy='test_strategy',
        position_value=6000,
        side='LONG',
        position_id='pos_1'
    )
    
    # 두 번째 포지션 시도: 5,000 (누적 11,000 > 예산 10,000)
    allowed, reason = pm.can_open_position(
        symbol='BTCUSDT',
        strategy='test_strategy',
        position_value=5000,
        side='LONG'
    )
    assert allowed is False
    assert '전략 예산 초과' in reason


def test_default_flag_value(base_config):
    """
    케이스 5: Config에 enable_strategy_budget_cap 없을 때
    기본값 True로 설정되는지 확인
    """
    # 플래그 삭제
    del base_config['portfolio']['enable_strategy_budget_cap']
    pm = PortfolioManager(base_config, load_existing=False)
    
    # 기본값은 True
    assert pm.enable_strategy_budget_cap is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
