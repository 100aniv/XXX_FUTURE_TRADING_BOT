#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-2 ITER8: Runner 날짜 SSOT 존중 테스트
================================================

검증 항목:
1. YAML에 start_date/end_date가 있으면 절대 덮어쓰지 않음
2. YAML에 없고 --range 1d 지정 시 1일 범위로 설정
3. YAML에 없고 --range 7d 지정 시 7일 범위로 설정
4. YAML에 없고 --range 미지정 시 디폴트 7d
"""
import sys
from pathlib import Path

# Project root 추가
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from scripts.phase35.run_iter5_isolated_v2 import apply_date_range


def test_yaml_dates_respected():
    """YAML에 날짜가 있으면 보존 + backtest 섹션 동기화"""
    config = {
        'start_date': '2024-11-01',
        'end_date': '2024-11-15'
    }
    
    # range_override가 있어도 YAML 우선
    apply_date_range(config, range_override='1d')
    
    assert config['start_date'] == '2024-11-01', "YAML start_date가 변경됨!"
    assert config['end_date'] == '2024-11-15', "YAML end_date가 변경됨!"
    
    # ITER9: backtest 섹션 동기화 검증
    assert 'backtest' in config, "backtest 섹션 미생성!"
    assert config['backtest']['start_date'] == '2024-11-01', "backtest.start_date 불일치!"
    assert config['backtest']['end_date'] == '2024-11-15', "backtest.end_date 불일치!"


def test_range_1d_override():
    """YAML 날짜 없고 --range 1d 지정 시"""
    config = {}
    
    apply_date_range(config, range_override='1d')
    
    assert 'start_date' in config
    assert 'end_date' in config
    assert config['start_date'] == '2024-12-01'
    assert config['end_date'] == '2024-12-02'


def test_range_7d_override():
    """YAML 날짜 없고 --range 7d 지정 시"""
    config = {}
    
    apply_date_range(config, range_override='7d')
    
    assert 'start_date' in config
    assert 'end_date' in config
    assert config['start_date'] == '2024-12-01'
    assert config['end_date'] == '2024-12-08'


def test_default_7d_when_no_override():
    """YAML 날짜 없고 --range 미지정 시 디폴트 7d"""
    config = {}
    
    apply_date_range(config, range_override=None)
    
    assert 'start_date' in config
    assert 'end_date' in config
    assert config['start_date'] == '2024-12-01'
    assert config['end_date'] == '2024-12-08'


def test_partial_yaml_dates_not_respected():
    """YAML에 start_date만 있고 end_date 없으면 override"""
    config = {
        'start_date': '2024-11-01'
    }
    
    apply_date_range(config, range_override='1d')
    
    # start_date만 있으면 "모두 있는 것"으로 간주하지 않음
    # 따라서 override됨
    assert config['start_date'] == '2024-12-01'
    assert config['end_date'] == '2024-12-02'


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
